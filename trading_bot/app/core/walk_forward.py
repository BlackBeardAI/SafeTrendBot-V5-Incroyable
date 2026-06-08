"""
Walk-Forward Analysis (WFA) automatique.
Réoptimise les paramètres des stratégies chaque semaine sur 3 mois
et valide sur 1 mois. Ne garde que si amélioration significative.
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
from concurrent.futures import ProcessPoolExecutor
import itertools

from app.core.strategies import (
    TrendFollowingStrategy, MeanReversionStrategy, BreakoutStrategy, MACDStrategy,
    StrategyVoter, MarketData, Signal
)
from app.core.regime_detector import MarketRegime


@dataclass
class WFAParams:
    """Grille de paramètres à tester"""
    fast_ema_range: List[int] = field(default_factory=lambda: [10, 20, 50])
    slow_ema_range: List[int] = field(default_factory=lambda: [50, 100, 200])
    rsi_period_range: List[int] = field(default_factory=lambda: [10, 14, 21])
    bb_period_range: List[int] = field(default_factory=lambda: [15, 20, 25])
    breakout_period_range: List[int] = field(default_factory=lambda: [15, 20, 25, 30])
    atr_multiplier_sl_range: List[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 2.5])
    risk_reward_range: List[float] = field(default_factory=lambda: [1.5, 2.0, 2.5, 3.0])


@dataclass
class WFAResult:
    params: Dict[str, Any]
    net_profit: float
    win_rate: float
    max_drawdown: float
    sharpe: float
    profit_factor: float
    trades_count: int
    is_better: bool = False


class WalkForwardAnalysis:
    """
    WFA : optimiser sur in-sample (3 mois), valider sur out-of-sample (1 mois).
    """

    def __init__(self, wfa_params: Optional[WFAParams] = None,
                 in_sample_months: int = 3, out_sample_months: int = 1,
                 min_trades: int = 20, min_improvement_pct: float = 5.0):
        self.wfa_params = wfa_params or WFAParams()
        self.in_sample_months = in_sample_months
        self.out_sample_months = out_sample_months
        self.min_trades = min_trades
        self.min_improvement_pct = min_improvement_pct
        self._best_params_file = Path(__file__).parent / 'wfa_best_params.json'
        self._last_run_file = Path(__file__).parent / 'wfa_last_run.json'

    def _generate_param_combinations(self, max_combinations: int = 50) -> List[Dict]:
        """Génère une grille réduite de combinaisons"""
        keys = [
            ('fast_ema', self.wfa_params.fast_ema_range),
            ('slow_ema', self.wfa_params.slow_ema_range),
            ('rsi_period', self.wfa_params.rsi_period_range),
            ('bb_period', self.wfa_params.bb_period_range),
            ('breakout_period', self.wfa_params.breakout_period_range),
            ('atr_multiplier_sl', self.wfa_params.atr_multiplier_sl_range),
            ('risk_reward', self.wfa_params.risk_reward_range),
        ]
        # Prendre un sous-échantillon aléatoire pour ne pas exploser
        all_combos = list(itertools.product(*[k[1] for k in keys]))
        if len(all_combos) > max_combinations:
            indices = np.random.choice(len(all_combos), max_combinations, replace=False)
            all_combos = [all_combos[i] for i in indices]

        return [{keys[i][0]: v for i, v in enumerate(combo)} for combo in all_combos]

    def _run_backtest_single(self, params: Dict, data: MarketData,
                              higher_tf_data: Optional[MarketData] = None) -> WFAResult:
        """Backtest rapide d'une combinaison de paramètres"""
        # Créer les stratégies avec les params
        strategies = [
            TrendFollowingStrategy(fast_ema=params['fast_ema'], slow_ema=params['slow_ema'],
                                   rsi_period=params['rsi_period']),
            MeanReversionStrategy(bb_period=params['bb_period']),
            BreakoutStrategy(period=params['breakout_period']),
            MACDStrategy(),
        ]
        voter = StrategyVoter(strategies, min_agreement=2, min_confidence=0.5)

        # Simuler trade par trade sur les closes
        closes = data.closes
        highs = data.highs
        lows = data.lows
        opens = data.opens
        volumes = data.volumes

        trades = []
        position = None
        entry_price = 0.0
        entry_signal = None
        atr_val = None

        for i in range(60, len(closes)):
            # Créer les données jusqu'à i
            md = MarketData(
                symbol=data.symbol, closes=closes[:i+1], highs=highs[:i+1],
                lows=lows[:i+1], opens=opens[:i+1], volumes=volumes[:i+1],
                timeframe=data.timeframe,
            )
            result = voter.vote(md)

            if result.final_signal != Signal.NONE and position is None:
                position = 1 if result.final_signal == Signal.BUY else -1
                entry_price = closes[i]
                entry_signal = result
                # ATR approximatif
                atr_val = np.mean([max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
                                   for j in range(max(1,i-14), i+1)])
            elif position is not None:
                sl_dist = atr_val * params['atr_multiplier_sl'] if atr_val else closes[i] * 0.01
                rr = params['risk_reward']
                if position == 1:
                    tp = entry_price + sl_dist * rr
                    sl = entry_price - sl_dist
                    if highs[i] >= tp:
                        trades.append((closes[i] - entry_price) / entry_price * 100)
                        position = None
                    elif lows[i] <= sl:
                        trades.append((sl - entry_price) / entry_price * 100)
                        position = None
                else:
                    tp = entry_price - sl_dist * rr
                    sl = entry_price + sl_dist
                    if lows[i] <= tp:
                        trades.append((entry_price - closes[i]) / entry_price * 100)
                        position = None
                    elif highs[i] >= sl:
                        trades.append((entry_price - sl) / entry_price * 100)
                        position = None

        if len(trades) < self.min_trades:
            return WFAResult(params=params, net_profit=-999, win_rate=0,
                             max_drawdown=0, sharpe=0, profit_factor=0, trades_count=len(trades))

        trades_arr = np.array(trades)
        net_profit = trades_arr.sum()
        wins = trades_arr[trades_arr > 0]
        losses = trades_arr[trades_arr <= 0]
        win_rate = len(wins) / len(trades_arr) * 100
        max_dd = self._calculate_max_drawdown(trades_arr)
        sharpe = np.mean(trades_arr) / (np.std(trades_arr) + 1e-10) * np.sqrt(len(trades_arr))
        pf = abs(wins.sum() / losses.sum()) if len(losses) > 0 and losses.sum() != 0 else 999

        return WFAResult(
            params=params, net_profit=round(net_profit, 2), win_rate=round(win_rate, 1),
            max_drawdown=round(max_dd, 2), sharpe=round(sharpe, 2),
            profit_factor=round(pf, 2), trades_count=len(trades),
        )

    @staticmethod
    def _calculate_max_drawdown(returns: np.ndarray) -> float:
        equity = np.cumsum(returns)
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / (peak + 1e-10) * 100
        return dd.max() if len(dd) > 0 else 0.0

    def run_wfa(self, data: MarketData, higher_tf_data: Optional[MarketData] = None,
                n_jobs: int = 4) -> Optional[WFAResult]:
        """
        Lance le WFA complet :
        1. Génère les combinaisons
        2. Backtest in-sample (dernier 3 mois)
        3. Garde les 5 meilleurs
        4. Backtest out-of-sample (mois suivant) pour validation
        5. Retourne le meilleur validé
        """
        combos = self._generate_param_combinations(max_combinations=40)
        print(f"[WFA] {len(combos)} combinaisons à tester")

        # In-sample : dernières N bougies
        n_total = len(data.closes)
        n_is = int(n_total * 0.75)  # 75% in-sample
        data_is = MarketData(
            symbol=data.symbol, closes=data.closes[:n_is], highs=data.highs[:n_is],
            lows=data.lows[:n_is], opens=data.opens[:n_is], volumes=data.volumes[:n_is],
            timeframe=data.timeframe,
        )
        data_os = MarketData(
            symbol=data.symbol, closes=data.closes[n_is:], highs=data.highs[n_is:],
            lows=data.lows[n_is:], opens=data.opens[n_is:], volumes=data.volumes[n_is:],
            timeframe=data.timeframe,
        )

        results = []
        for combo in combos:
            r = self._run_backtest_single(combo, data_is)
            if r.trades_count >= self.min_trades:
                results.append(r)

        if not results:
            return None

        # Top 5 in-sample par net profit
        top_is = sorted(results, key=lambda x: x.net_profit, reverse=True)[:5]
        print(f"[WFA] Top IS: {top_is[0].net_profit:.1f}% WR {top_is[0].win_rate:.0f}% DD {top_is[0].max_drawdown:.1f}%")

        # Validation out-of-sample
        best_os = None
        for candidate in top_is:
            os_result = self._run_backtest_single(candidate.params, data_os)
            if os_result.trades_count >= 5 and os_result.net_profit > 0:
                if best_os is None or os_result.sharpe > best_os.sharpe:
                    best_os = os_result

        if best_os is None:
            print("[WFA] Échec validation OOS — paramètres actuels conservés")
            return None

        # Comparer avec les params actuels (simulés)
        current_result = self._run_backtest_single({
            'fast_ema': 50, 'slow_ema': 200, 'rsi_period': 14,
            'bb_period': 20, 'breakout_period': 20,
            'atr_multiplier_sl': 1.5, 'risk_reward': 2.0,
        }, data_os)

        improvement = (best_os.net_profit - max(current_result.net_profit, -999)) /                       (abs(current_result.net_profit) + 1e-10) * 100
        best_os.is_better = improvement >= self.min_improvement_pct

        print(f"[WFA] Best OOS: {best_os.net_profit:.1f}% WR {best_os.win_rate:.0f}% | "
              f"Amélioration: {improvement:.1f}% {'✅ APPLIQUÉ' if best_os.is_better else '❌ Ignoré'}")

        self._save_result(best_os)
        return best_os

    def _save_result(self, result: WFAResult):
        data = {
            'params': result.params,
            'metrics': {
                'net_profit': result.net_profit, 'win_rate': result.win_rate,
                'max_drawdown': result.max_drawdown, 'sharpe': result.sharpe,
                'profit_factor': result.profit_factor, 'trades': result.trades_count,
            },
            'is_better': result.is_better,
            'timestamp': datetime.now().isoformat(),
        }
        self._best_params_file.write_text(json.dumps(data, indent=2))
        self._last_run_file.write_text(json.dumps({'last_run': datetime.now().isoformat()}))

    def load_best_params(self) -> Optional[Dict]:
        if self._best_params_file.exists():
            return json.loads(self._best_params_file.read_text())
        return None

    def should_run(self) -> bool:
        """Vrai si la dernière exécution date de + d'une semaine"""
        if not self._last_run_file.exists():
            return True
        last = json.loads(self._last_run_file.read_text()).get('last_run')
        if last:
            last_dt = datetime.fromisoformat(last)
            return (datetime.now() - last_dt).days >= 7
        return True
