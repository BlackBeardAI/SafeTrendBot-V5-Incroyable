"""
Backtest parallélisé avec ProcessPoolExecutor.
Grid search des paramètres en parallèle.
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from datetime import datetime

from app.core.strategies import (
    TrendFollowingStrategy, MeanReversionStrategy, BreakoutStrategy, MACDStrategy,
    StrategyVoter, MarketData, Signal
)


@dataclass
class BacktestResult:
    params: Dict[str, Any]
    net_profit_pct: float
    win_rate: float
    max_drawdown_pct: float
    sharpe: float
    profit_factor: float
    trades_count: int
    avg_trade: float
    expectancy: float
    total_return: float
    duration_hours: float


def _run_single_backtest(args) -> BacktestResult:
    """Fonction worker pour multiprocessing"""
    params, data_dict = args

    # Reconstruire MarketData
    data = MarketData(
        symbol=data_dict['symbol'],
        closes=np.array(data_dict['closes']),
        highs=np.array(data_dict['highs']),
        lows=np.array(data_dict['lows']),
        opens=np.array(data_dict['opens']),
        volumes=np.array(data_dict['volumes']),
        timeframe=data_dict['timeframe'],
    )

    strategies = [
        TrendFollowingStrategy(fast_ema=params.get('fast_ema', 50),
                               slow_ema=params.get('slow_ema', 200),
                               rsi_period=params.get('rsi_period', 14)),
        MeanReversionStrategy(bb_period=params.get('bb_period', 20)),
        BreakoutStrategy(period=params.get('breakout_period', 20)),
        MACDStrategy(),
    ]
    voter = StrategyVoter(strategies, min_agreement=params.get('min_agreement', 2),
                          min_confidence=params.get('min_confidence', 0.5))

    closes = data.closes
    highs = data.highs
    lows = data.lows
    trades = []
    position = None
    entry_price = 0.0
    atr_val = None

    for i in range(60, len(closes)):
        md = MarketData(symbol=data.symbol, closes=closes[:i+1], highs=highs[:i+1],
                        lows=lows[:i+1], opens=data.opens[:i+1], volumes=data.volumes[:i+1],
                        timeframe=data.timeframe)
        result = voter.vote(md)

        if result.final_signal != Signal.NONE and position is None:
            position = 1 if result.final_signal == Signal.BUY else -1
            entry_price = closes[i]
            atr_val = np.mean([max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1]))
                               for j in range(max(1, i-14), i+1)])
        elif position is not None:
            sl_dist = atr_val * params.get('atr_multiplier_sl', 1.5) if atr_val else closes[i] * 0.01
            rr = params.get('risk_reward', 2.0)
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

    if len(trades) < 5:
        return BacktestResult(params=params, net_profit_pct=-999, win_rate=0,
                              max_drawdown_pct=0, sharpe=0, profit_factor=0,
                              trades_count=0, avg_trade=0, expectancy=0, total_return=0,
                              duration_hours=0)

    trades_arr = np.array(trades)
    net_profit = trades_arr.sum()
    wins = trades_arr[trades_arr > 0]
    losses = trades_arr[trades_arr <= 0]
    win_rate = len(wins) / len(trades_arr) * 100
    max_dd = _calc_max_dd(trades_arr)
    sharpe = np.mean(trades_arr) / (np.std(trades_arr) + 1e-10) * np.sqrt(len(trades_arr))
    pf = abs(wins.sum() / losses.sum()) if len(losses) > 0 and losses.sum() != 0 else 999
    avg_trade = np.mean(trades_arr)
    expectancy = (win_rate/100 * np.mean(wins) if len(wins) > 0 else 0) -                  ((100-win_rate)/100 * abs(np.mean(losses)) if len(losses) > 0 else 0)

    return BacktestResult(
        params=params, net_profit_pct=round(net_profit, 2), win_rate=round(win_rate, 1),
        max_drawdown_pct=round(max_dd, 2), sharpe=round(sharpe, 2),
        profit_factor=round(pf, 2), trades_count=len(trades),
        avg_trade=round(avg_trade, 2), expectancy=round(expectancy, 2),
        total_return=round(net_profit, 2),
        duration_hours=round(len(closes) * 0.1, 1),
    )


def _calc_max_dd(returns):
    equity = np.cumsum(returns)
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / (peak + 1e-10) * 100
    return dd.max() if len(dd) > 0 else 0.0


class ParallelBacktest:
    """
    Lance des backtests en parallèle sur plusieurs combinaisons de paramètres.
    """

    def __init__(self, n_jobs: Optional[int] = None):
        self.n_jobs = n_jobs or max(1, multiprocessing.cpu_count() - 1)

    def grid_search(self, data: MarketData, param_grid: List[Dict[str, Any]]) -> List[BacktestResult]:
        """
        Teste toutes les combinaisons en parallèle.
        Retourne les résultats triés par Sharpe.
        """
        print(f"[BACKTEST] {len(param_grid)} combinaisons sur {self.n_jobs} cœurs")

        # Sérialiser MarketData
        data_dict = {
            'symbol': data.symbol, 'closes': data.closes.tolist(),
            'highs': data.highs.tolist(), 'lows': data.lows.tolist(),
            'opens': data.opens.tolist(), 'volumes': data.volumes.tolist(),
            'timeframe': data.timeframe,
        }
        args = [(p, data_dict) for p in param_grid]

        results = []
        with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
            futures = {executor.submit(_run_single_backtest, a): i for i, a in enumerate(args)}
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    print(f"[BACKTEST] Erreur worker: {e}")

        # Trier par Sharpe
        results = sorted(results, key=lambda r: r.sharpe, reverse=True)
        print(f"[BACKTEST] Meilleur Sharpe: {results[0].sharpe if results else 'N/A'}")
        return results

    def optimize(self, data: MarketData, n_combinations: int = 20) -> Optional[BacktestResult]:
        """Optimise rapidement sur un sous-échantillon"""
        import itertools
        keys = [
            ('fast_ema', [10, 20, 50]), ('slow_ema', [50, 100, 200]),
            ('rsi_period', [10, 14, 21]), ('atr_multiplier_sl', [1.0, 1.5, 2.0]),
            ('risk_reward', [1.5, 2.0, 2.5, 3.0]),
        ]
        all_combos = list(itertools.product(*[k[1] for k in keys]))
        if len(all_combos) > n_combinations:
            import random
            all_combos = random.sample(all_combos, n_combinations)
        param_grid = [{keys[i][0]: v for i, v in enumerate(combo)} for combo in all_combos]
        results = self.grid_search(data, param_grid)
        return results[0] if results else None
