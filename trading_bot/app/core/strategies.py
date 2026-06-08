"""
Framework de stratégies de trading.
Chaque stratégie implémente une interface commune et peut être combinée
avec d'autres via un système de vote.
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class Signal(Enum):
    BUY = 1
    SELL = -1
    NONE = 0


@dataclass
class StrategySignal:
    """Signal émis par une stratégie"""
    signal: Signal
    confidence: float       # 0.0 à 1.0
    strategy_name: str
    reason: str = ""


@dataclass
class MarketData:
    """Données de marché fournies aux stratégies"""
    symbol: str
    closes: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    opens: np.ndarray
    volumes: np.ndarray
    timeframe: str
    # Multi-timeframe (optionnel)
    higher_tf_closes: Optional[np.ndarray] = None
    higher_tf_timeframe: Optional[str] = None


# ============================================================================
# INDICATEURS TECHNIQUES (réutilisables)
# ============================================================================

def ema(data: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(data, dtype=float)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def sma(data: np.ndarray, period: int) -> np.ndarray:
    result = np.zeros_like(data, dtype=float)
    for i in range(len(data)):
        if i < period - 1:
            result[i] = data[i]
        else:
            result[i] = np.mean(data[i - period + 1:i + 1])
    return result


def rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
    deltas = np.diff(data)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    result = np.zeros_like(data, dtype=float)
    result[0:period] = 50.0

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(data)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            result[i] = 100
        else:
            rs = avg_gain / avg_loss
            result[i] = 100 - (100 / (1 + rs))
    return result


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range"""
    tr = np.zeros(len(closes))
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close = abs(lows[i] - closes[i - 1])
        tr[i] = max(high_low, high_close, low_close)

    result = np.zeros_like(tr)
    result[:period] = np.mean(tr[:period]) if len(tr) >= period else tr.mean()
    for i in range(period, len(tr)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def bollinger_bands(data: np.ndarray, period: int = 20, std_dev: float = 2.0):
    """Retourne (upper, middle, lower)"""
    middle = sma(data, period)
    std = np.zeros_like(data, dtype=float)
    for i in range(len(data)):
        start = max(0, i - period + 1)
        std[i] = np.std(data[start:i + 1])
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def macd(data: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9):
    """Retourne (macd_line, signal_line, histogram)"""
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ============================================================================
# CLASSE DE BASE DES STRATÉGIES
# ============================================================================

class BaseStrategy(ABC):
    """Interface commune pour toutes les stratégies"""

    name: str = "BaseStrategy"
    min_bars_required: int = 50  # Réduit de 210 à 50 - suffisant pour MACD, RSI, Bollinger

    @abstractmethod
    def analyze(self, data: MarketData) -> StrategySignal:
        """Analyse les données et retourne un signal"""
        pass

    def validate_data(self, data: MarketData) -> bool:
        if len(data.closes) < self.min_bars_required:
            return False
        return True




# ============================================================================
# STRATÉGIE 1 : TREND FOLLOWING basée sur l'ÉTAT (pas le croisement)
# ============================================================================

class TrendFollowingStrategy(BaseStrategy):
    """
    Signal BUY si prix > EMA50 > EMA200 (tendance haussière EN COURS).
    Signal SELL si prix < EMA50 < EMA200 (tendance baissière EN COURS).
    Plus souple : utilise EMA20/EMA50 si moins de 200 bougies disponibles.
    """
    name = "Trend Following (EMA+RSI)"

    def __init__(self, fast_ema: int = 50, slow_ema: int = 200,
                 rsi_period: int = 14, rsi_overbought: float = 70,
                 rsi_oversold: float = 30):
        self.fast_ema_period = fast_ema
        self.slow_ema_period = slow_ema
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.min_bars_required = 52  # Seulement EMA50 requis au minimum

    def analyze(self, data: MarketData) -> StrategySignal:
        if not self.validate_data(data):
            return StrategySignal(Signal.NONE, 0.0, self.name, "Données insuffisantes")

        closes = data.closes
        n = len(closes)

        # Adapter les périodes selon les données disponibles
        if n >= self.slow_ema_period + 10:
            fast = ema(closes, self.fast_ema_period)
            slow_arr = ema(closes, self.slow_ema_period)
            label = f"EMA{self.fast_ema_period}/EMA{self.slow_ema_period}"
        elif n >= 52:
            fast = ema(closes, 20)
            slow_arr = ema(closes, 50)
            label = "EMA20/EMA50"
        else:
            fast = ema(closes, 10)
            slow_arr = ema(closes, 20)
            label = "EMA10/EMA20"

        rsi_val = rsi(closes, self.rsi_period)
        current = closes[-1]
        rsi_now = rsi_val[-1]
        fast_now = fast[-1]
        slow_now = slow_arr[-1]

        # Signal BUY : tendance haussière (état, pas croisement)
        if fast_now > slow_now and current > fast_now and rsi_now < self.rsi_overbought:
            gap_pct = (fast_now - slow_now) / slow_now * 100
            conf = min(0.85, 0.42 + gap_pct * 3 + max(0, (rsi_now - 50)) * 0.003)
            return StrategySignal(
                Signal.BUY, max(0.42, conf), self.name,
                f"Hausse ({label}), RSI={rsi_now:.0f}"
            )

        # Signal SELL : tendance baissière
        if fast_now < slow_now and current < fast_now and rsi_now > self.rsi_oversold:
            gap_pct = (slow_now - fast_now) / slow_now * 100
            conf = min(0.85, 0.42 + gap_pct * 3 + max(0, (50 - rsi_now)) * 0.003)
            return StrategySignal(
                Signal.SELL, max(0.42, conf), self.name,
                f"Baisse ({label}), RSI={rsi_now:.0f}"
            )

        return StrategySignal(Signal.NONE, 0.0, self.name,
                              f"Pas de tendance (RSI={rsi_now:.0f})")


# ============================================================================
# STRATÉGIE 2 : MEAN REVERSION (Bollinger Bands)
# ============================================================================

class MeanReversionStrategy(BaseStrategy):
    """
    Signal quand le prix sort des bandes de Bollinger (condition active).
    Seuils RSI assouplis pour générer plus de signaux.
    """
    name = "Mean Reversion (Bollinger)"

    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, rsi_period: int = 14):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.min_bars_required = max(bb_period + 10, 35)

    def analyze(self, data: MarketData) -> StrategySignal:
        if not self.validate_data(data):
            return StrategySignal(Signal.NONE, 0.0, self.name, "Données insuffisantes")

        upper, middle, lower = bollinger_bands(data.closes, self.bb_period, self.bb_std)
        rsi_val = rsi(data.closes, self.rsi_period)
        current = data.closes[-1]
        rsi_now = rsi_val[-1]
        band_width = upper[-1] - lower[-1] + 1e-10

        # BUY : sous la bande inférieure + RSI < 40
        if current < lower[-1] and rsi_now < 40:
            dist = (lower[-1] - current) / band_width
            conf = min(0.85, 0.42 + dist * 2.0)
            return StrategySignal(Signal.BUY, conf, self.name,
                                  f"Sous BB, RSI={rsi_now:.0f}")

        # SELL : au-dessus de la bande supérieure + RSI > 60
        if current > upper[-1] and rsi_now > 60:
            dist = (current - upper[-1]) / band_width
            conf = min(0.85, 0.42 + dist * 2.0)
            return StrategySignal(Signal.SELL, conf, self.name,
                                  f"Au-dessus BB, RSI={rsi_now:.0f}")

        return StrategySignal(Signal.NONE, 0.0, self.name,
                              f"Prix dans les bandes (RSI={rsi_now:.0f})")


# ============================================================================
# STRATÉGIE 3 : BREAKOUT (Donchian Channels)
# ============================================================================

class BreakoutStrategy(BaseStrategy):
    """
    Cassure de plus haut/bas sur N bougies.
    Signal dès que le prix casse un niveau — pas de confirmation requise.
    """
    name = "Breakout (Donchian)"

    def __init__(self, period: int = 20, confirmation_bars: int = 2):
        self.period = period
        self.confirmation_bars = confirmation_bars
        self.min_bars_required = period + 5

    def analyze(self, data: MarketData) -> StrategySignal:
        if not self.validate_data(data):
            return StrategySignal(Signal.NONE, 0.0, self.name, "Données insuffisantes")

        lookback_high = data.highs[-self.period - 1:-1]
        lookback_low  = data.lows[-self.period - 1:-1]
        highest = np.max(lookback_high)
        lowest  = np.min(lookback_low)
        current = data.closes[-1]

        atr_val = atr(data.highs, data.lows, data.closes, 14)
        atr_now = max(atr_val[-1], 1e-10)

        # Cassure haussière
        if current > highest:
            strength = (current - highest) / atr_now
            conf = min(0.85, 0.42 + strength * 0.12)
            return StrategySignal(Signal.BUY, conf, self.name,
                                  f"Cassure haute {current:.5f}>{highest:.5f}")

        # Cassure baissière
        if current < lowest:
            strength = (lowest - current) / atr_now
            conf = min(0.85, 0.42 + strength * 0.12)
            return StrategySignal(Signal.SELL, conf, self.name,
                                  f"Cassure basse {current:.5f}<{lowest:.5f}")

        return StrategySignal(Signal.NONE, 0.0, self.name, "Pas de cassure")


# ============================================================================
# STRATÉGIE 4 : MACD MOMENTUM (état, pas croisement)
# ============================================================================

class MACDStrategy(BaseStrategy):
    """
    Signal BUY tant que MACD > signal_line ET histogramme > 0.
    Signal SELL tant que MACD < signal_line ET histogramme < 0.
    Beaucoup plus fréquent que d'attendre un croisement.
    """
    name = "MACD Momentum"

    def __init__(self, fast: int = 12, slow: int = 26, signal_period: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period
        self.min_bars_required = slow + signal_period + 5

    def analyze(self, data: MarketData) -> StrategySignal:
        if not self.validate_data(data):
            return StrategySignal(Signal.NONE, 0.0, self.name, "Données insuffisantes")

        macd_line, signal_line, histogram = macd(
            data.closes, self.fast, self.slow, self.signal_period
        )
        hist_now = histogram[-1]
        macd_now = macd_line[-1]
        sig_now  = signal_line[-1]

        hist_window = histogram[-20:] if len(histogram) >= 20 else histogram
        hist_std = np.std(hist_window) + 1e-10
        strength = abs(hist_now) / hist_std

        # BUY : MACD positif (au-dessus de sa ligne signal)
        if macd_now > sig_now and hist_now > 0:
            conf = min(0.85, 0.40 + min(strength, 3.0) * 0.12)
            return StrategySignal(Signal.BUY, conf, self.name,
                                  f"MACD>Signal, hist={hist_now:.6f}")

        # SELL : MACD négatif
        if macd_now < sig_now and hist_now < 0:
            conf = min(0.85, 0.40 + min(strength, 3.0) * 0.12)
            return StrategySignal(Signal.SELL, conf, self.name,
                                  f"MACD<Signal, hist={hist_now:.6f}")

        return StrategySignal(Signal.NONE, 0.0, self.name,
                              f"MACD neutre (hist={hist_now:.6f})")

# ============================================================================
# SYSTÈME DE VOTE MULTI-STRATÉGIES
# ============================================================================

@dataclass
class VoteResult:
    final_signal: Signal
    confidence: float
    buy_votes: int
    sell_votes: int
    total_strategies: int
    individual_signals: List[StrategySignal]
    decision_reason: str


class StrategyVoter:
    """
    Combine plusieurs stratégies et prend une décision par vote pondéré.
    Un trade n'est pris que si X/N stratégies sont d'accord.
    """

    def __init__(self, strategies: List[BaseStrategy], min_agreement: int = 2,
                 min_confidence: float = 0.5):
        """
        Args:
            strategies: Liste des stratégies à combiner
            min_agreement: Nombre minimum de stratégies qui doivent être d'accord
            min_confidence: Confidence moyenne minimale requise
        """
        self.strategies = strategies
        self.min_agreement = min_agreement
        self.min_confidence = min_confidence

    def vote(self, data: MarketData) -> VoteResult:
        """Collecte les signaux et vote"""
        signals = [s.analyze(data) for s in self.strategies]

        buy_signals = [s for s in signals if s.signal == Signal.BUY]
        sell_signals = [s for s in signals if s.signal == Signal.SELL]

        buy_count = len(buy_signals)
        sell_count = len(sell_signals)

        # Décision
        if buy_count >= self.min_agreement and buy_count > sell_count:
            avg_conf = np.mean([s.confidence for s in buy_signals])
            if avg_conf >= self.min_confidence:
                return VoteResult(
                    final_signal=Signal.BUY,
                    confidence=float(avg_conf),
                    buy_votes=buy_count,
                    sell_votes=sell_count,
                    total_strategies=len(self.strategies),
                    individual_signals=signals,
                    decision_reason=f"{buy_count}/{len(self.strategies)} stratégies en ACHAT "
                                    f"(confidence moy: {avg_conf:.2f})"
                )

        if sell_count >= self.min_agreement and sell_count > buy_count:
            avg_conf = np.mean([s.confidence for s in sell_signals])
            if avg_conf >= self.min_confidence:
                return VoteResult(
                    final_signal=Signal.SELL,
                    confidence=float(avg_conf),
                    buy_votes=buy_count,
                    sell_votes=sell_count,
                    total_strategies=len(self.strategies),
                    individual_signals=signals,
                    decision_reason=f"{sell_count}/{len(self.strategies)} stratégies en VENTE "
                                    f"(confidence moy: {avg_conf:.2f})"
                )

        return VoteResult(
            final_signal=Signal.NONE,
            confidence=0.0,
            buy_votes=buy_count,
            sell_votes=sell_count,
            total_strategies=len(self.strategies),
            individual_signals=signals,
            decision_reason=f"Pas de consensus ({buy_count} achat / {sell_count} vente)"
        )


# ============================================================================
# FACTORY
# ============================================================================

def create_default_voter(config) -> StrategyVoter:
    """Crée un voter avec les stratégies par défaut, paramètres depuis la config."""
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
    return StrategyVoter(
        strategies,
        min_agreement=config.strategy.min_strategies_agreement,
        min_confidence=config.strategy.min_confidence,
    )
