"""
SafeTrendBot Trading Engine — Moteur de trading unifié
======================================================
- Gestion multi-brokers (MT5, cTrader, XTB, Binance, etc.)
- Détection automatique du régime de marché
- Kelly Criterion pour sizing adaptatif
- Gestion du risque multicouche
- Mode headless/GUI
- Intégration license_manager
"""

import sys
import os
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum, auto
from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor

# ─── Configuration ───────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".safetrendbot"
CONFIG_FILE = CONFIG_DIR / "config.json"

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(CONFIG_DIR / "bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SafeTrendBot")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class MarketRegime(Enum):
    TRENDING_UP = auto()      # Tendance haussière
    TRENDING_DOWN = auto()    # Tendance baissière
    RANGING = auto()          # Range / consolidation
    VOLATILE = auto()          # Haute volatilité
    LOW_LIQUIDITY = auto()     # Marché calme/peu liquide

class TradeDirection(Enum):
    LONG = auto()
    SHORT = auto()
    CLOSE_LONG = auto()
    CLOSE_SHORT = auto()
    CLOSE_ALL = auto()

class BrokerType(Enum):
    MT5 = "mt5"
    CTRADER = "ctrader"
    XTB = "xtb"
    BINANCE = "binance"
    IC_MARKETS = "icmarkets"
    UNKNOWN = "unknown"


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
    
    def _bollinger_bands(self, prices: List[float], period: int = None):
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


# ═══════════════════════════════════════════════════════════════════════════════
# KELLY CRITERION SIZER
# ═══════════════════════════════════════════════════════════════════════════════

class KellySizer:
    """
    Calcule la taille de position selon Kelly Criterion.
    Adapté pour le trading (version fractionnaire).
    """
    
    def __init__(self, fraction: float = 0.25, max_risk_percent: float = 2.0):
        # Kelly fraction (0.25 = quarter Kelly = plus prudent)
        self.fraction = fraction
        self.max_risk_percent = max_risk_percent
        self.win_rate = 0.5
        self.avg_win = 0
        self.avg_loss = 0
    
    def update_stats(self, wins: int, losses: int, total_win: float, total_loss: float):
        """Met à jour les statistiques de trade."""
        total = wins + losses
        if total == 0:
            return
        
        self.win_rate = wins / total
        self.avg_win = total_win / wins if wins else 0
        self.avg_loss = abs(total_loss / losses) if losses else 0
    
    def calculate_size(self, account_balance: float, entry_price: float, 
                      stop_loss: float, regime: MarketRegime) -> float:
        """
        Calcule la taille de position optimale.
        Returns volume en lots (MT5) ou en unités (crypto).
        """
        if self.avg_loss == 0 or self.win_rate == 0:
            # Pas de stats — risque fixe
            return self._fixed_size(account_balance, entry_price, stop_loss)
        
        # Kelly fractionnel
        if self.avg_loss > 0:
            win_loss_ratio = self.avg_win / self.avg_loss
        else:
            win_loss_ratio = 1.0
        
        kelly = self.fraction * (
            (self.win_rate * win_loss_ratio) - (1 - self.win_rate)
        )
        
        # Contraire: si win_rate < 0.5, kelly est négatif
        kelly = max(0.01, min(kelly, 0.20))  # Borné 1-20%
        
        # Ajuster selon régime
        if regime == MarketRegime.VOLATILE:
            kelly *= 0.5  # Réduire en volatile
        elif regime == MarketRegime.TRENDING_UP:
            kelly *= 1.2  # Augmenter en trend
        
        # Risque max
        risk_amount = account_balance * (self.max_risk_percent / 100)
        max_lot = risk_amount / (abs(entry_price - stop_loss) * 100000) if abs(entry_price - stop_loss) > 0 else 0.01
        
        # Prendre le min entre Kelly et max_risk
        risk_from_kelly = account_balance * kelly
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk > 0:
            kelly_lot = risk_from_kelly / (price_risk * 100000)
        else:
            kelly_lot = 0.01
        
        return round(max(0.01, min(kelly_lot, max_lot)), 2)
    
    def _fixed_size(self, balance: float, entry: float, sl: float) -> float:
        """Fallback: taille fixe basée sur risque max."""
        risk_pct = 1.0 / 100
        risk_amount = balance * risk_pct
        pip_risk = abs(entry - sl)
        
        if pip_risk > 0:
            return round(risk_amount / (pip_risk * 100000), 2)
        return 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# BROKER ABSTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

class BrokerAdapter(ABC):
    """Interface abstraite pour les adapters de broker."""
    
    @abstractmethod
    def connect(self) -> bool:
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    @abstractmethod
    def get_account_info(self) -> dict:
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        pass
    
    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, count: int) -> List[dict]:
        pass
    
    @abstractmethod
    def send_order(self, symbol: str, direction: TradeDirection, volume: float,
                   stop_loss: float, take_profit: float) -> TradeResult:
        pass
    
    @abstractmethod
    def close_position(self, ticket: int) -> bool:
        pass


class MT5Adapter(BrokerAdapter):
    """Adapter pour MetaTrader 5."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.connected = False
        self._mt5 = None
    
    def connect(self) -> bool:
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
            if mt5.initialize():
                self.connected = True
                logger.info("MT5 connecté")
                return True
        except ImportError:
            logger.warning("MetaTrader5 non installé")
        except Exception as e:
            logger.error(f"Erreur connexion MT5: {e}")
        return False
    
    def disconnect(self):
        if self._mt5 and self.connected:
            self._mt5.shutdown()
            self.connected = False
    
    def get_account_info(self) -> dict:
        if not self._mt5:
            return {}
        info = self._mt5.account_info()
        if info:
            return {
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "free_margin": info.margin_free,
                "currency": info.currency,
            }
        return {}
    
    def get_positions(self) -> List[Position]:
        if not self._mt5:
            return []
        positions = self._mt5.positions_get()
        result = []
        for p in positions:
            result.append(Position(
                ticket=p.ticket,
                symbol=p.symbol,
                direction=TradeDirection.LONG if p.type == 0 else TradeDirection.SHORT,
                volume=p.volume,
                entry_price=p.price_open,
                current_price=p.price_current,
                stop_loss=p.sl,
                take_profit=p.tp,
                unrealized_pnl=p.profit,
                opened_at=datetime.fromtimestamp(p.time),
            ))
        return result
    
    def get_candles(self, symbol: str, timeframe: str = "H1", count: int = 100) -> List[dict]:
        if not self._mt5:
            return []
        
        tf_map = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}
        tf = tf_map.get(timeframe, 60)
        
        rates = self._mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return []
        
        return [
            {
                "time": datetime.fromtimestamp(r[0]),
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "volume": r[5],
            }
            for r in rates
        ]
    
    def send_order(self, symbol: str, direction: TradeDirection, volume: float,
                   stop_loss: float, take_profit: float) -> TradeResult:
        if not self._mt5:
            return TradeResult(False, None, symbol, direction, 0, 0, 0, 0, "Non connecté")
        
        start = time.time()
        order_type = 0 if direction == TradeDirection.LONG else 1
        
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": self._mt5.symbol_info_tick(symbol).bid,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 10,
            "magic": 2024,
            "comment": "SafeTrendBot",
            "type_filling": self._mt5.ORDER_FILLING_FOK,
        }
        
        result = self._mt5.order_send(request)
        elapsed = (time.time() - start) * 1000
        
        if result.retcode == self._mt5.TRADE_RETCODE_DONE:
            return TradeResult(
                True, result.order, symbol, direction,
                result.price, volume, stop_loss, take_profit,
                execution_time_ms=elapsed
            )
        else:
            return TradeResult(
                False, None, symbol, direction, 0, volume, stop_loss, take_profit,
                error=f"Code {result.retcode}: {result.comment}",
                execution_time_ms=elapsed
            )
    
    def close_position(self, ticket: int) -> bool:
        if not self._mt5:
            return False
        
        positions = self._mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        
        pos = positions[0]
        direction = self._mt5.POSITION_TYPE_BUY if pos.type == 0 else self._mt5.POSITION_TYPE_SELL
        
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": direction,
            "price": self._mt5.symbol_info_tick(pos.symbol).bid,
            "magic": 2024,
            "comment": "SafeTrendBot Close",
            "type_filling": self._mt5.ORDER_FILLING_FOK,
        }
        
        result = self._mt5.order_send(request)
        return result.retcode == self._mt5.TRADE_RETCODE_DONE


class BrokerFactory:
    """Factory pour créer l'adapter approprié."""
    
    _adapters = {
        BrokerType.MT5: MT5Adapter,
        # Ajouter d'autres adapters selon besoin
    }
    
    @classmethod
    def create(cls, broker_type: BrokerType, config: dict = None) -> BrokerAdapter:
        adapter_class = cls._adapters.get(broker_type, MT5Adapter)
        return adapter_class(config)
    
    @classmethod
    def auto_detect(cls) -> BrokerAdapter:
        """Détecte automatiquement le broker disponible."""
        # Essayer MT5 en premier
        try:
            import MetaTrader5
            return MT5Adapter()
        except ImportError:
            pass
        
        logger.error("Aucun broker détecté")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# TRADING ENGINE (MAIN CLASS)
# ═══════════════════════════════════════════════════════════════════════════════

class TradingEngine:
    """
    Moteur de trading principal.
    Orchestre régime detection, sizing, exécution.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or self._load_config()
        self.broker: Optional[BrokerAdapter] = None
        self.regime_detector = RegimeDetector()
        self.kelly_sizer = KellySizer()
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.signals: List[Signal] = []
        
        # Stats
        self.trades_won = 0
        self.trades_lost = 0
        self.total_win = 0.0
        self.total_loss = 0.0
    
    def _load_config(self) -> dict:
        """Charge la config utilisateur."""
        default = {
            "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
            "timeframe": "H1",
            "max_positions": 3,
            "risk_percent": 2.0,
            "kelly_fraction": 0.25,
            "adx_threshold": 25,
            "stop_loss_pips": 50,
            "take_profit_pips": 100,
            "trailing_stop": True,
            "trailing_offset": 20,
        }
        
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    user = json.load(f)
                    default.update(user)
            except:
                pass
        
        return default
    
    def start(self):
        """Démarre le moteur de trading."""
        if self.running:
            logger.warning("Moteur déjà démarré")
            return
        
        self.broker = BrokerFactory.auto_detect()
        if not self.broker or not self.broker.connect():
            logger.error("Impossible de se connecter au broker")
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Moteur de trading démarré")
    
    def stop(self):
        """Arrête le moteur."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self.broker:
            self.broker.disconnect()
        logger.info("Moteur arrêté")
    
    def _run_loop(self):
        """Boucle principale de trading."""
        while self.running:
            try:
                self._scan_markets()
                time.sleep(60)  # Scan chaque minute
            except Exception as e:
                logger.error(f"Erreur boucle: {e}")
                time.sleep(10)
    
    def _scan_markets(self):
        """Scanne tous les symbols et génère des signaux."""
        for symbol in self.config.get("symbols", []):
            try:
                candles = self.broker.get_candles(
                    symbol, 
                    self.config.get("timeframe", "H1"),
                    100
                )
                
                if not candles:
                    continue
                
                # Détecter régime
                regime, regime_info = self.regime_detector.detect(candles)
                logger.debug(f"{symbol}: {regime.name} (ADX={regime_info.get('adx', 0):.1f})")
                
                # Générer signal si régime favorable
                if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                    signal = self._generate_signal(symbol, candles, regime, regime_info)
                    if signal and signal.confidence > 60:
                        self._execute_signal(signal)
                
                # Check positions existantes
                self._manage_open_positions()
                
            except Exception as e:
                logger.error(f"Erreur scan {symbol}: {e}")
    
    def _generate_signal(self, symbol: str, candles: List[dict], 
                        regime: MarketRegime, regime_info: dict) -> Optional[Signal]:
        """Génère un signal de trading."""
        closes = [c['close'] for c in candles]
        current_price = closes[-1]
        
        # Calculer SL/TP en pips
        sl_pips = self.config.get("stop_loss_pips", 50)
        tp_pips = self.config.get("take_profit_pips", 100)
        pip_value = current_price * 0.0001
        
        stop_loss = current_price - (sl_pips * pip_value) if regime == MarketRegime.TRENDING_UP else current_price + (sl_pips * pip_value)
        take_profit = current_price + (tp_pips * pip_value) if regime == MarketRegime.TRENDING_UP else current_price - (tp_pips * pip_value)
        
        # Confidence basée sur ADX
        adx = regime_info.get('adx', 0)
        confidence = min(100, adx * 3)  # ADX 25 → 75%, ADX 40 → 100%
        
        direction = TradeDirection.LONG if regime == MarketRegime.TRENDING_UP else TradeDirection.SHORT
        
        return Signal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            regime=regime,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy="RegimeFollower",
            metadata=regime_info
        )
    
    def _execute_signal(self, signal: Signal):
        """Exécute un signal de trading."""
        # Vérifier nombre max de positions
        positions = self.broker.get_positions() if self.broker else []
        if len(positions) >= self.config.get("max_positions", 3):
            logger.debug("Max positions atteint")
            return
        
        # Calculer taille
        account = self.broker.get_account_info() if self.broker else {}
        balance = account.get("balance", 10000)
        
        volume = self.kelly_sizer.calculate_size(
            balance,
            signal.entry_price,
            signal.stop_loss,
            signal.regime
        )
        
        # Envoyer ordre
        result = self.broker.send_order(
            signal.symbol,
            signal.direction,
            volume,
            signal.stop_loss,
            signal.take_profit
        )
        
        if result.success:
            logger.info(f"✅ ORDER: {signal.direction.name} {signal.symbol} "
                       f"@{result.entry_price:.5f} SL:{result.stop_loss:.5f} TP:{result.take_profit:.5f}")
        else:
            logger.warning(f"❌ ORDER FAILED: {result.error}")
    
    def _manage_open_positions(self):
        """Gère les positions ouvertes (trailing stop, etc.)."""
        positions = self.broker.get_positions() if self.broker else []
        
        for pos in positions:
            if pos.unrealized_pnl > 0 and self.config.get("trailing_stop"):
                # Implémenter trailing stop
                pass  # À compléter


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Point d'entrée pour le bot."""
    from .license_manager import auto_activate, LicenseStatus, LicenseManager
    
    # 1. Vérifier licence
    lm = LicenseManager()
    status = lm.check_license(verbose=True)
    
    if status != LicenseStatus.VALID:
        logger.error(f"Licence invalide: {status.name}")
        sys.exit(1)
    
    logger.info("Licence validée — démarrage SafeTrendBot")
    
    # 2. Démarrer moteur
    engine = TradingEngine()
    engine.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Arrêt demandé")
        engine.stop()


if __name__ == "__main__":
    main()