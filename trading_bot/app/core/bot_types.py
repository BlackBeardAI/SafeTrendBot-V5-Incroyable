"""
SafeTrendBot V5 — Types partagés et utilitaires communs
========================================================
Module central regroupant tous les types partagés (enums, dataclasses)
et le RegimeDetector afin d'unifier les imports à travers tout le projet.

Historique : auparavant éclaté entre trading_engine.py (v1) et
trading_engine_v3.py, ces types sont désormais centralisés ici.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class MarketRegime(Enum):
    """Régime de marché détecté en temps réel."""
    TRENDING_UP = auto()      # Tendance haussière
    TRENDING_DOWN = auto()    # Tendance baissière
    RANGING = auto()          # Range / consolidation
    VOLATILE = auto()          # Haute volatilité
    LOW_LIQUIDITY = auto()     # Marché calme/peu liquide
    UNKNOWN = auto()          # Régime indéterminé


class TradeDirection(Enum):
    """Direction d'un trade ou d'un signal."""
    LONG = auto()
    SHORT = auto()
    CLOSE_LONG = auto()
    CLOSE_SHORT = auto()
    CLOSE_ALL = auto()


class BrokerType(Enum):
    """Type de broker supporté (valeurs string pour sérialisation)."""
    MT5 = "mt5"
    CTRADER = "ctrader"
    XTB = "xtb"
    BINANCE = "binance"
    IC_MARKETS = "icmarkets"
    UNKNOWN = "unknown"


class BotState(Enum):
    """État d'exécution du bot."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    HALTED = "halted"
    ERROR = "error"


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Signal:
    """Signal de trading généré par le système."""
    symbol: str
    direction: TradeDirection
    confidence: float  # 0-100
    regime: MarketRegime
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    strategy: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Position ouverte."""
    ticket: int
    symbol: str
    direction: TradeDirection
    volume: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float
    opened_at: datetime


@dataclass
class TradeResult:
    """Résultat d'un trade exécuté."""
    success: bool
    ticket: Optional[int]
    symbol: str
    direction: TradeDirection
    entry_price: float
    volume: float
    stop_loss: float
    take_profit: float
    error: Optional[str] = None
    execution_time_ms: float = 0


@dataclass
class BotStatus:
    """Snapshot de l'état du bot (émis via status_changed)."""
    state: BotState
    mode: str
    broker: str
    connected: bool
    last_tick_time: Optional[datetime]
    last_signal_time: Optional[datetime]
    active_symbols: list
    open_positions: int
    managed_positions: dict
    today_trades: int
    today_pnl: float
    consecutive_losses: int
    circuit_breaker_level: str
    # Champs optionnels (V4+)
    current_regime: str = "unknown"
    regime_confidence: float = 0.0
    portfolio_risk_multiplier: float = 1.0
    kelly_fraction: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    message: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# REGIME DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class RegimeDetector:
    """
    Détecte le régime de marché en temps réel.
    Utilise ADX + Bollinger Bands + ATR pour classification.
    """

    def __init__(self, adx_threshold: float = 25, bb_period: int = 20):
        self.adx_threshold = adx_threshold
        self.bb_period = bb_period
        self.cache: Dict[str, dict] = {}

    def detect(self, candles: List[dict]) -> Tuple[MarketRegime, dict]:
        """
        Analyse les chandeliers et retourne le régime.
        candles = [{'open', 'high', 'low', 'close', 'volume', 'time'}]
        """
        if len(candles) < self.bb_period + 5:
            return MarketRegime.RANGING, {}

        closes = [c['close'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        volumes = [c.get('volume', 0) for c in candles]

        # BBands
        bb_upper, bb_middle, bb_lower = self._bollinger_bands(closes)
        price = closes[-1]

        # ADX
        adx, plus_di, minus_di = self._adx(highs, lows, closes)

        # ATR pour volatilité
        atr = self._atr(highs, lows, closes)
        atr_percent = (atr / price) * 100 if price else 0

        # Volume profile
        avg_volume = sum(volumes[-20:]) / min(20, len(volumes))
        current_volume = volumes[-1] if volumes else 0
        volume_ratio = current_volume / avg_volume if avg_volume else 1

        # Classification
        regime_info = {
            "adx": adx,
            "atr_percent": atr_percent,
            "volume_ratio": volume_ratio,
            "bb_position": (price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5,
        }

        # Déterminer régime
        if adx < self.adx_threshold:
            return MarketRegime.RANGING, regime_info

        if atr_percent > 2.5:
            return MarketRegime.VOLATILE, regime_info

        if volume_ratio < 0.3:
            return MarketRegime.LOW_LIQUIDITY, regime_info

        if plus_di > minus_di and adx > self.adx_threshold:
            return MarketRegime.TRENDING_UP, regime_info

        if minus_di > plus_di and adx > self.adx_threshold:
            return MarketRegime.TRENDING_DOWN, regime_info

        return MarketRegime.RANGING, regime_info

    def _bollinger_bands(self, prices: List[float], period: Optional[int] = None):
        period = period or self.bb_period
        if len(prices) < period:
            return prices[-1], prices[-1], prices[-1]

        recent = prices[-period:]
        middle = sum(recent) / period
        variance = sum((p - middle) ** 2 for p in recent) / period
        std = variance ** 0.5

        upper = middle + (2 * std)
        lower = middle - (2 * std)
        return upper, middle, lower

    def _adx(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14):
        if len(closes) < period + 1:
            return 25.0, 25.0, 25.0  # Default

        # Simplified ADX calculation
        trs = []
        plus_dms = []
        minus_dms = []

        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            prev_high = highs[i-1]
            prev_low = lows[i-1]
            prev_close = closes[i-1]

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)

            up_move = high - prev_high
            down_move = prev_low - low

            plus_dm = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0
            plus_dms.append(plus_dm)
            minus_dms.append(minus_dm)

        if len(trs) < period:
            return 25.0, 25.0, 25.0

        # Smooth
        atr = sum(trs[-period:]) / period
        plus_di = (sum(plus_dms[-period:]) / period / atr) * 100 if atr else 0
        minus_di = (sum(minus_dms[-period:]) / period / atr) * 100 if atr else 0

        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) else 0
        adx = dx  # Simplified

        return adx, plus_di, minus_di

    def _atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14):
        if len(closes) < period + 1:
            return 0

        trs = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)

        return sum(trs[-period:]) / period if len(trs) >= period else sum(trs) / len(trs)


__all__ = [
    'MarketRegime', 'TradeDirection', 'BrokerType', 'BotState',
    'Signal', 'Position', 'TradeResult', 'BotStatus',
    'RegimeDetector',
]