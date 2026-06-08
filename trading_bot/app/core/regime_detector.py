"""
Détecteur de régime de marché avancé.
Identifie en temps réel : TRENDING, RANGING, VOLATILE, CRASH, RECOVERY.
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from collections import deque
from datetime import datetime

class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CRASH = "crash"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"

class RegimeConfidence(Enum):
    LOW = 0.5
    MEDIUM = 0.75
    HIGH = 0.9

@dataclass
class RegimeResult:
    regime: MarketRegime
    confidence: float
    strength: float
    reasons: List[str]
    adx: float
    atr_ratio: float
    bb_position: float
    momentum_20: float
    momentum_50: float

class RegimeDetector:
    """
    Détecte le régime de marché via un ensemble d'indicateurs :
    - ADX pour la force de tendance
    - ATR ratio pour la volatilité
    - Position dans les Bollinger Bands
    - Momentum court et long terme
    - Skewness des returns
    """

    def __init__(self, adx_period=14, lookback=100):
        self.adx_period = adx_period
        self.lookback = lookback
        self._history = deque(maxlen=20)  # Historique des régimes pour lissage

    def _adx(self, highs, lows, closes):
        n = len(closes)
        if n < self.adx_period * 2:
            return 0.0
        tr = np.zeros(n)
        tr[0] = highs[0] - lows[0]
        for i in range(1, n):
            tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        atr = np.zeros(n)
        atr[self.adx_period] = np.mean(tr[:self.adx_period])
        for i in range(self.adx_period+1, n):
            atr[i] = (atr[i-1]*(self.adx_period-1) + tr[i]) / self.adx_period

        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)
        for i in range(1, n):
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            if up > down and up > 0:
                plus_dm[i] = up
            if down > up and down > 0:
                minus_dm[i] = down

        smoothed_plus = np.zeros(n)
        smoothed_minus = np.zeros(n)
        smoothed_plus[self.adx_period] = np.mean(plus_dm[:self.adx_period])
        smoothed_minus[self.adx_period] = np.mean(minus_dm[:self.adx_period])
        for i in range(self.adx_period+1, n):
            smoothed_plus[i] = (smoothed_plus[i-1]*(self.adx_period-1) + plus_dm[i]) / self.adx_period
            smoothed_minus[i] = (smoothed_minus[i-1]*(self.adx_period-1) + minus_dm[i]) / self.adx_period

        dx = np.zeros(n)
        for i in range(self.adx_period, n):
            denom = smoothed_plus[i] + smoothed_minus[i]
            if denom > 0:
                dx[i] = 100 * abs(smoothed_plus[i] - smoothed_minus[i]) / denom

        adx = np.zeros(n)
        adx[self.adx_period*2] = np.mean(dx[self.adx_period:self.adx_period*2])
        for i in range(self.adx_period*2+1, n):
            adx[i] = (adx[i-1]*(self.adx_period-1) + dx[i]) / self.adx_period
        return adx[-1] if len(adx) > 0 else 0.0

    def _bollinger_position(self, closes, period=20):
        if len(closes) < period:
            return 0.5
        mid = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        if std == 0:
            return 0.5
        return (closes[-1] - mid) / (2 * std + 1e-10)

    def detect(self, closes, highs, lows, volumes=None) -> RegimeResult:
        n = len(closes)
        if n < 55:
            return RegimeResult(MarketRegime.UNKNOWN, 0.0, 0.0, ["Données insuffisantes"], 0, 1.0, 0.5, 0, 0)

        returns = np.diff(closes) / closes[:-1]
        adx_val = self._adx(highs, lows, closes)

        # ATR ratio
        tr = np.array([max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
                       for i in range(1, n)])
        atr_current = np.mean(tr[-14:])
        atr_median = np.median(tr[-100:]) if len(tr) >= 100 else np.median(tr)
        atr_ratio = atr_current / (atr_median + 1e-10)

        bb_pos = self._bollinger_position(closes)
        momentum_20 = (closes[-1] / closes[-20] - 1) * 100 if n >= 20 else 0
        momentum_50 = (closes[-1] / closes[-50] - 1) * 100 if n >= 50 else 0

        # Skewness (asymétrie des returns)
        skew = np.mean(returns**3) / (np.std(returns)**3 + 1e-10) if len(returns) > 0 else 0

        reasons = []
        regime = MarketRegime.UNKNOWN
        confidence = 0.0
        strength = 0.0

        # Détection CRASH : drawdown > 5% en 20 bougies + volatilité extrême
        if momentum_20 < -5 and atr_ratio > 2.5:
            regime = MarketRegime.CRASH
            confidence = min(0.95, 0.7 + abs(momentum_20)/20)
            strength = abs(momentum_20)
            reasons.append(f"Drawdown {momentum_20:.1f}% + volatilité {atr_ratio:.1f}x")

        # Détection RECOVERY : après crash, momentum fort positif
        elif momentum_20 > 3 and momentum_50 < -2 and atr_ratio > 1.5:
            regime = MarketRegime.RECOVERY
            confidence = min(0.9, 0.6 + momentum_20/10)
            strength = momentum_20
            reasons.append(f"Rebond {momentum_20:.1f}% après tendance baissière")

        # Détection VOLATILE : ATR élevé sans direction claire
        elif atr_ratio > 2.0 and adx_val < 25:
            regime = MarketRegime.VOLATILE
            confidence = min(0.9, 0.6 + (atr_ratio-2)*0.2)
            strength = atr_ratio
            reasons.append(f"Volatilité {atr_ratio:.1f}x sans tendance claire (ADX={adx_val:.0f})")

        # Détection TRENDING : ADX élevé
        elif adx_val >= 25:
            if momentum_20 > 1.5 and bb_pos > 0.3:
                regime = MarketRegime.TRENDING_UP
                confidence = min(0.95, 0.7 + adx_val/50 + momentum_20/10)
                strength = momentum_20
                reasons.append(f"Tendance haussière forte (ADX={adx_val:.0f}, mom={momentum_20:.1f}%)")
            elif momentum_20 < -1.5 and bb_pos < -0.3:
                regime = MarketRegime.TRENDING_DOWN
                confidence = min(0.95, 0.7 + adx_val/50 + abs(momentum_20)/10)
                strength = abs(momentum_20)
                reasons.append(f"Tendance baissière forte (ADX={adx_val:.0f}, mom={momentum_20:.1f}%)")
            else:
                regime = MarketRegime.VOLATILE
                confidence = 0.6
                strength = adx_val / 10
                reasons.append(f"Tendance ambiguë malgré ADX={adx_val:.0f}")

        # Détection RANGING : ADX faible, prix dans les bandes
        elif adx_val < 20 and abs(bb_pos) < 0.5 and atr_ratio < 1.5:
            regime = MarketRegime.RANGING
            confidence = min(0.9, 0.7 + (20-adx_val)/40)
            strength = 1.0 - abs(bb_pos)
            reasons.append(f"Marché sans tendance (ADX={adx_val:.0f}, BB pos={bb_pos:.2f})")

        # Fallback : momentum faible → ranging
        else:
            if abs(momentum_20) < 1:
                regime = MarketRegime.RANGING
                confidence = 0.5
                strength = 0.5
                reasons.append(f"Momentum quasi nul ({momentum_20:.2f}%)")
            elif momentum_20 > 0:
                regime = MarketRegime.TRENDING_UP
                confidence = 0.5
                strength = momentum_20
                reasons.append(f"Momentum positif faible")
            else:
                regime = MarketRegime.TRENDING_DOWN
                confidence = 0.5
                strength = abs(momentum_20)
                reasons.append(f"Momentum négatif faible")

        # Lissage avec l'historique
        self._history.append(regime)
        if len(self._history) >= 3:
            recent = list(self._history)[-5:]
            most_common = max(set(recent), key=recent.count)
            if most_common != regime:
                confidence *= 0.8  # Pénalité si changement brutal
                reasons.append("Transition détectée (lissage)")

        return RegimeResult(
            regime=regime, confidence=round(confidence, 2), strength=round(strength, 2),
            reasons=reasons, adx=round(adx_val, 1), atr_ratio=round(atr_ratio, 2),
            bb_position=round(bb_pos, 2), momentum_20=round(momentum_20, 2),
            momentum_50=round(momentum_50, 2),
        )

    def get_recommended_strategies(self, regime: MarketRegime) -> dict:
        """Retourne les pondérations recommandées des stratégies selon le régime"""
        weights = {
            MarketRegime.TRENDING_UP:   {"trend": 0.50, "mean_rev": 0.05, "breakout": 0.35, "macd": 0.10},
            MarketRegime.TRENDING_DOWN:  {"trend": 0.50, "mean_rev": 0.05, "breakout": 0.35, "macd": 0.10},
            MarketRegime.RANGING:        {"trend": 0.10, "mean_rev": 0.50, "breakout": 0.15, "macd": 0.25},
            MarketRegime.VOLATILE:       {"trend": 0.20, "mean_rev": 0.20, "breakout": 0.40, "macd": 0.20},
            MarketRegime.CRASH:          {"trend": 0.05, "mean_rev": 0.10, "breakout": 0.05, "macd": 0.00},
            MarketRegime.RECOVERY:       {"trend": 0.35, "mean_rev": 0.15, "breakout": 0.30, "macd": 0.20},
            MarketRegime.UNKNOWN:        {"trend": 0.25, "mean_rev": 0.25, "breakout": 0.25, "macd": 0.25},
        }
        return weights.get(regime, weights[MarketRegime.UNKNOWN])

    def get_recommended_risk(self, regime: MarketRegime, base_risk: float) -> float:
        """Ajuste le risque selon le régime"""
        multipliers = {
            MarketRegime.TRENDING_UP:   1.0,
            MarketRegime.TRENDING_DOWN:  1.0,
            MarketRegime.RANGING:        0.7,
            MarketRegime.VOLATILE:       0.5,
            MarketRegime.CRASH:        0.0,
            MarketRegime.RECOVERY:       0.8,
            MarketRegime.UNKNOWN:        0.6,
        }
        return base_risk * multipliers.get(regime, 0.6)
