"""
Stratégies adaptatives selon le régime de marché.
Les pondérations et paramètres s'ajustent dynamiquement.
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

from app.core.strategies import (
    BaseStrategy, StrategySignal, Signal, MarketData,
    TrendFollowingStrategy, MeanReversionStrategy, BreakoutStrategy, MACDStrategy,
    StrategyVoter, VoteResult,
)
from app.core.regime_detector import RegimeDetector, MarketRegime, RegimeResult


@dataclass
class AdaptiveVoteResult(VoteResult):
    """Résultat enrichi avec le régime et les pondérations adaptatives"""
    regime: MarketRegime = MarketRegime.UNKNOWN
    regime_confidence: float = 0.0
    strategy_weights: Dict[str, float] = None
    adjusted_risk_percent: float = 0.0


class AdaptiveStrategyVoter(StrategyVoter):
    """
    Voter amélioré qui adapte les pondérations selon le régime de marché.
    """

    def __init__(self, strategies: List[BaseStrategy], config, min_agreement: int = 2,
                 min_confidence: float = 0.5):
        super().__init__(strategies, min_agreement, min_confidence)
        self.regime_detector = RegimeDetector()
        self.config = config
        self._last_regime: Optional[RegimeResult] = None
        self._performance_history: Dict[str, List[float]] = {
            "trend": [], "mean_rev": [], "breakout": [], "macd": []
        }

    def vote(self, data: MarketData) -> AdaptiveVoteResult:
        # Détecter le régime
        regime_result = self.regime_detector.detect(
            data.closes, data.highs, data.lows, data.volumes
        )
        self._last_regime = regime_result

        # Pondérations adaptatives
        weights = self.regime_detector.get_recommended_strategies(regime_result.regime)

        # Ajuster selon la performance historique des stratégies
        weights = self._apply_performance_boost(weights)

        # Collecter les signaux individuels
        signals = []
        for strategy in self.strategies:
            sig = strategy.analyze(data)
            # Ajuster la confiance selon le poids
            key = self._strategy_key(strategy)
            weight = weights.get(key, 0.25)
            # Stratégies avec poids < 0.1 sont mises à neutre (pas bannies, juste moins confiantes)
            if weight < 0.1:
                sig = StrategySignal(Signal.NONE, 0.0, strategy.name, f"Désactivée (régime {regime_result.regime.value})")
            else:
                sig.confidence *= weight  # Pondérer la confiance
            signals.append(sig)

        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        sell_signals = [s for s in signals if s.signal == Signal.SELL]

        buy_count = len(buy_signals)
        sell_count = len(sell_signals)

        # Calculer la confiance pondérée (somme des confidences des stratégies qui votent)
        def weighted_conf(signals_list):
            if not signals_list:
                return 0.0
            return sum(s.confidence for s in signals_list) / len([s for s in signals if s.confidence > 0])

        # Ajuster le risque selon le régime
        base_risk = getattr(self.config.strategy, 'risk_percent', 1.0)
        adjusted_risk = self.regime_detector.get_recommended_risk(regime_result.regime, base_risk)

        if buy_count >= self.min_agreement and buy_count > sell_count:
            avg_conf = np.mean([s.confidence for s in buy_signals])
            if avg_conf >= self.min_confidence:
                return AdaptiveVoteResult(
                    final_signal=Signal.BUY, confidence=float(avg_conf),
                    buy_votes=buy_count, sell_votes=sell_count,
                    total_strategies=len(self.strategies),
                    individual_signals=signals,
                    decision_reason=f"ACHAT | {regime_result.regime.value} | {buy_count}/{len(self.strategies)} strat | conf={avg_conf:.2f}",
                    regime=regime_result.regime,
                    regime_confidence=regime_result.confidence,
                    strategy_weights=weights,
                    adjusted_risk_percent=adjusted_risk,
                )

        if sell_count >= self.min_agreement and sell_count > buy_count:
            avg_conf = np.mean([s.confidence for s in sell_signals])
            if avg_conf >= self.min_confidence:
                return AdaptiveVoteResult(
                    final_signal=Signal.SELL, confidence=float(avg_conf),
                    buy_votes=buy_count, sell_votes=sell_count,
                    total_strategies=len(self.strategies),
                    individual_signals=signals,
                    decision_reason=f"VENTE | {regime_result.regime.value} | {sell_count}/{len(self.strategies)} strat | conf={avg_conf:.2f}",
                    regime=regime_result.regime,
                    regime_confidence=regime_result.confidence,
                    strategy_weights=weights,
                    adjusted_risk_percent=adjusted_risk,
                )

        return AdaptiveVoteResult(
            final_signal=Signal.NONE, confidence=0.0,
            buy_votes=buy_count, sell_votes=sell_count,
            total_strategies=len(self.strategies),
            individual_signals=signals,
            decision_reason=f"NEUTRE | {regime_result.regime.value} | {buy_count}↑ {sell_count}↓",
            regime=regime_result.regime,
            regime_confidence=regime_result.confidence,
            strategy_weights=weights,
            adjusted_risk_percent=adjusted_risk,
        )

    def _strategy_key(self, strategy: BaseStrategy) -> str:
        name = strategy.name.lower()
        if "trend" in name:
            return "trend"
        if "mean" in name or "reversion" in name:
            return "mean_rev"
        if "breakout" in name or "donchian" in name:
            return "breakout"
        if "macd" in name:
            return "macd"
        return "macd"

    def _apply_performance_boost(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Booste les stratégies qui performent bien récemment"""
        for key, history in self._performance_history.items():
            if len(history) >= 5:
                recent_win_rate = sum(1 for p in history[-10:] if p > 0) / len(history[-10:])
                if recent_win_rate > 0.6:
                    weights[key] = min(0.6, weights.get(key, 0.25) * 1.3)
                elif recent_win_rate < 0.3:
                    weights[key] = max(0.0, weights.get(key, 0.25) * 0.5)
        # Normaliser
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        return weights

    def record_trade_result(self, strategy_key: str, profit: float):
        """Enregistre le résultat d'un trade pour ajuster les poids"""
        self._performance_history.setdefault(strategy_key, []).append(profit)
        for hist in self._performance_history.values():
            if len(hist) > 100:
                hist.pop(0)

    def get_last_regime(self) -> Optional[RegimeResult]:
        return self._last_regime


def create_adaptive_voter(config) -> AdaptiveStrategyVoter:
    """Factory pour créer un voter adaptatif"""
    strategies = [
        TrendFollowingStrategy(
            fast_ema=config.strategy.fast_ema,
            slow_ema=config.strategy.slow_ema,
            rsi_period=config.strategy.rsi_period,
            rsi_overbought=config.strategy.rsi_overbought,
            rsi_oversold=config.strategy.rsi_oversold,
        ),
        MeanReversionStrategy(),
        BreakoutStrategy(),
        MACDStrategy(),
    ]
    return AdaptiveStrategyVoter(
        strategies,
        config=config,
        min_agreement=config.strategy.min_strategies_agreement,
        min_confidence=config.strategy.min_confidence,
    )
