"""
Auto-Hedge — ouvre des positions de couverture sur les paires corrélées.
"""
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class HedgeRecommendation:
    primary_symbol: str
    hedge_symbol: str
    correlation: float
    hedge_ratio: float
    direction: int  # 1 = même sens, -1 = opposé
    confidence: float


class AutoHedge:
    """
    Détecte et ouvre des hedges automatiques pour protéger le portefeuille.
    """

    def __init__(self, correlation_threshold: float = 0.8,
                 max_hedge_ratio: float = 0.5):
        self.corr_threshold = correlation_threshold
        self.max_hedge_ratio = max_hedge_ratio
        self._correlations: Dict[str, Dict[str, float]] = {}

    def update_correlations(self, symbols: List[str], broker):
        """Calcule la matrice de corrélation"""
        for i, s1 in enumerate(symbols):
            self._correlations[s1] = {}
            for s2 in symbols[i+1:]:
                try:
                    a = broker.get_candles_arrays(s1, 'H1', 100)
                    b = broker.get_candles_arrays(s2, 'H1', 100)
                    if a is None or b is None:
                        continue
                    n = min(len(a['close']), len(b['close']))
                    if n < 20:
                        continue
                    ra = np.diff(a['close'][-n:]) / a['close'][-n:-1]
                    rb = np.diff(b['close'][-n:]) / b['close'][-n:-1]
                    corr = float(np.corrcoef(ra, rb)[0, 1])
                    self._correlations[s1][s2] = corr
                except Exception:
                    continue

    def recommend_hedge(self, symbol: str, direction: int, volume: float) -> Optional[HedgeRecommendation]:
        """
        Recommande un hedge pour une position donnée.
        """
        best = None
        best_score = 0

        for other, corr in self._correlations.get(symbol, {}).items():
            if abs(corr) < self.corr_threshold:
                continue

            hedge_dir = 1 if corr > 0 else -1
            hedge_dir *= -1  # On veut l'opposé

            score = abs(corr)
            if score > best_score:
                best_score = score
                hedge_ratio = min(self.max_hedge_ratio, abs(corr))
                best = HedgeRecommendation(
                    primary_symbol=symbol,
                    hedge_symbol=other,
                    correlation=round(corr, 2),
                    hedge_ratio=round(hedge_ratio, 2),
                    direction=hedge_dir,
                    confidence=round(abs(corr), 2),
                )

        return best

    def should_hedge(self, portfolio_exposure: float, max_exposure: float) -> bool:
        """Hedge si l'exposition dépasse la limite"""
        return portfolio_exposure > max_exposure * 0.8
