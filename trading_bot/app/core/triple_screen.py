"""
Système Triple Screen — Alexander Elder.
Trade uniquement si D1, H4, et H1 sont alignés.
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from app.core.strategies import ema, rsi, MarketData, Signal


class TimeframeAlignment(Enum):
    FULLY_ALIGNED = "fully_aligned"      # Les 3 TF sont cohérents
    PARTIALLY_ALIGNED = "partially"      # 2/3 seulement
    CONFLICTED = "conflicted"            # Divergence
    NEUTRAL = "neutral"                  # Pas de tendance claire


@dataclass
class TripleScreenResult:
    alignment: TimeframeAlignment
    d1_signal: Signal
    h4_signal: Signal
    h1_signal: Signal
    final_direction: int  # 1 buy, -1 sell, 0 neutral
    confidence: float
    reason: str


class TripleScreen:
    """
    Triple Screen Analysis :
    1. D1 donne la tendance principale (direction)
    2. H4 confirme la tendance (momentum)
    3. H1 donne le timing d'entrée
    """

    def __init__(self, d1_ema_fast=50, d1_ema_slow=200,
                 h4_rsi_period=14, h4_rsi_bull=50, h4_rsi_bear=50,
                 h1_ema_fast=20, h1_ema_slow=50):
        self.d1_fast = d1_ema_fast
        self.d1_slow = d1_ema_slow
        self.h4_rsi_period = h4_rsi_period
        self.h4_rsi_bull = h4_rsi_bull
        self.h4_rsi_bear = h4_rsi_bear
        self.h1_fast = h1_ema_fast
        self.h1_slow = h1_ema_slow

    def analyze(self, d1_data: MarketData, h4_data: MarketData,
                h1_data: MarketData) -> TripleScreenResult:
        """
        Retourne l'analyse Triple Screen.
        Trade seulement si FULLY_ALIGNED.
        """
        # Écran 1 : D1 — tendance via EMA
        d1_dir = self._screen1_trend(d1_data)
        d1_signal = Signal.BUY if d1_dir > 0 else (Signal.SELL if d1_dir < 0 else Signal.NONE)

        # Écran 2 : H4 — momentum via RSI
        h4_dir = self._screen2_momentum(h4_data)
        h4_signal = Signal.BUY if h4_dir > 0 else (Signal.SELL if h4_dir < 0 else Signal.NONE)

        # Écran 3 : H1 — timing d'entrée via EMA
        h1_dir = self._screen3_timing(h1_data)
        h1_signal = Signal.BUY if h1_dir > 0 else (Signal.SELL if h1_dir < 0 else Signal.NONE)

        # Alignement
        directions = [d1_dir, h4_dir, h1_dir]
        buys = sum(1 for d in directions if d > 0)
        sells = sum(1 for d in directions if d < 0)
        neutrals = sum(1 for d in directions if d == 0)

        if buys == 3:
            alignment = TimeframeAlignment.FULLY_ALIGNED
            final = 1
            conf = 0.85
            reason = "Triple Screen HAUSSIER (D1↑ H4↑ H1↑)"
        elif sells == 3:
            alignment = TimeframeAlignment.FULLY_ALIGNED
            final = -1
            conf = 0.85
            reason = "Triple Screen BAISSIER (D1↓ H4↓ H1↓)"
        elif buys == 2 and neutrals == 1:
            alignment = TimeframeAlignment.PARTIALLY_ALIGNED
            final = 1
            conf = 0.60
            reason = "Double Screen haussier (1 neutre)"
        elif sells == 2 and neutrals == 1:
            alignment = TimeframeAlignment.PARTIALLY_ALIGNED
            final = -1
            conf = 0.60
            reason = "Double Screen baissier (1 neutre)"
        elif buys > 0 and sells > 0:
            alignment = TimeframeAlignment.CONFLICTED
            final = 0
            conf = 0.0
            reason = f"Conflit : D1={d1_dir} H4={h4_dir} H1={h1_dir}"
        else:
            alignment = TimeframeAlignment.NEUTRAL
            final = 0
            conf = 0.0
            reason = "Aucune direction claire sur les 3 timeframes"

        return TripleScreenResult(
            alignment=alignment, d1_signal=d1_signal, h4_signal=h4_signal,
            h1_signal=h1_signal, final_direction=final, confidence=conf, reason=reason,
        )

    def _screen1_trend(self, data: MarketData) -> int:
        """D1 : EMA fast > slow = tendance haussière"""
        if len(data.closes) < self.d1_slow + 10:
            return 0
        fast = ema(data.closes, self.d1_fast)
        slow = ema(data.closes, self.d1_slow)
        if fast[-1] > slow[-1] and data.closes[-1] > fast[-1]:
            return 1
        if fast[-1] < slow[-1] and data.closes[-1] < fast[-1]:
            return -1
        return 0

    def _screen2_momentum(self, data: MarketData) -> int:
        """H4 : RSI confirme la tendance"""
        if len(data.closes) < self.h4_rsi_period + 5:
            return 0
        rsi_val = rsi(data.closes, self.h4_rsi_period)
        current = rsi_val[-1]
        if current > self.h4_rsi_bull:
            return 1
        if current < self.h4_rsi_bear:
            return -1
        return 0

    def _screen3_timing(self, data: MarketData) -> int:
        """H1 : timing via croisement EMA court"""
        if len(data.closes) < self.h1_slow + 5:
            return 0
        fast = ema(data.closes, self.h1_fast)
        slow = ema(data.closes, self.h1_slow)
        if fast[-1] > slow[-1] and fast[-2] <= slow[-2]:
            return 1  # Croisement haussier frais
        if fast[-1] < slow[-1] and fast[-2] >= slow[-2]:
            return -1  # Croisement baissier frais
        if fast[-1] > slow[-1]:
            return 1
        if fast[-1] < slow[-1]:
            return -1
        return 0
