"""
Smart Order Routing — minimise le slippage via Limit Orders intelligentes.
"""
import time
from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum
from datetime import datetime, timedelta


class ExecutionType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"
    TWAP = "twap"  # Time-Weighted Average Price


@dataclass
class ExecutionResult:
    success: bool
    filled_price: float
    requested_price: float
    slippage: float
    execution_type: ExecutionType
    latency_ms: float
    error_message: str = ""


class SmartOrderRouter:
    """
    Route les ordres de manière intelligente :
    - Limit Order si spread faible
    - Market Order si timeout ou volatilité extrême
    - TWAP pour les gros volumes
    - Track slippage par symbole pour ajuster
    """

    def __init__(self, broker, max_limit_wait_sec: float = 2.0,
                 spread_threshold_multiplier: float = 2.0,
                 slippage_log_max: int = 200):
        self.broker = broker
        self.max_limit_wait = max_limit_wait_sec
        self.spread_threshold_mult = spread_threshold_multiplier
        self._slippage_log: Dict[str, list] = {}  # symbol -> [(slippage, timestamp)]
        self._spread_history: Dict[str, list] = {}  # symbol -> [spread points]

    def _get_spread_median(self, symbol: str) -> float:
        hist = self._spread_history.get(symbol, [])
        if len(hist) < 5:
            return 20.0  # Défaut si pas d'historique
        return sorted(hist)[len(hist)//2]

    def execute(self, symbol: str, direction: int, volume: float,
                sl: float, tp: float, magic: int,
                preferred_price: Optional[float] = None) -> ExecutionResult:
        """
        Exécute un ordre avec la meilleure méthode selon les conditions.
        """
        tick = self.broker.get_tick(symbol)
        sym_info = self.broker.get_symbol_info(symbol)
        if not tick or not sym_info:
            return ExecutionResult(False, 0, 0, 0, ExecutionType.MARKET, 0, "Tick ou sym info indisponible")

        spread_points = (tick.ask - tick.bid) / sym_info.point if sym_info.point > 0 else 0
        median_spread = self._get_spread_median(symbol)

        # Mettre à jour l'historique
        self._spread_history.setdefault(symbol, []).append(spread_points)
        if len(self._spread_history[symbol]) > 50:
            self._spread_history[symbol].pop(0)

        # Décision d'exécution
        use_limit = spread_points <= median_spread * self.spread_threshold_mult

        if use_limit:
            # Essayer Limit Order
            result = self._try_limit_order(symbol, direction, volume, sl, tp, magic, tick)
            if result.success:
                self._log_slippage(symbol, result.slippage)
                return result
            # Fallback Market
            print(f"[SOR] Limit échouée sur {symbol}, fallback Market")

        # Market Order
        return self._execute_market(symbol, direction, volume, sl, tp, magic)

    def _try_limit_order(self, symbol, direction, volume, sl, tp, magic, tick) -> ExecutionResult:
        price = tick.bid if direction == -1 else tick.ask
        start = time.time()

        # Essayer d'envoyer Limit Order
        # Note: l'API du broker doit supporter les limit orders
        # Si pas supporté, on simule avec market
        if not self.broker.capabilities.supports_limit_orders:
            return ExecutionResult(False, 0, price, 0, ExecutionType.LIMIT, 0, "Limit non supporté")

        from app.brokers import OrderType
        order_type = OrderType.LIMIT_BUY if direction == 1 else OrderType.LIMIT_SELL

        result = self.broker.open_position(
            symbol=symbol, order_type=order_type,
            volume=volume, stop_loss=sl, take_profit=tp,
            price=price, magic=magic,
        )
        latency = (time.time() - start) * 1000

        if result.success:
            slippage = ((result.filled_price - price) / price * 100) if price > 0 else 0
            if direction == -1:
                slippage = -slippage  # Pour les sells, un fill plus haut = slippage négatif
            return ExecutionResult(
                True, result.filled_price or price, price, slippage,
                ExecutionType.LIMIT, latency,
            )
        return ExecutionResult(False, 0, price, 0, ExecutionType.LIMIT, latency, result.error_message)

    def _execute_market(self, symbol, direction, volume, sl, tp, magic) -> ExecutionResult:
        from app.brokers import OrderType
        order_type = OrderType.MARKET_BUY if direction == 1 else OrderType.MARKET_SELL
        start = time.time()

        result = self.broker.open_position(
            symbol=symbol, order_type=order_type,
            volume=volume, stop_loss=sl, take_profit=tp,
            magic=magic,
        )
        latency = (time.time() - start) * 1000

        if result.success:
            tick = self.broker.get_tick(symbol)
            expected = tick.ask if direction == 1 else tick.bid
            slippage = ((result.filled_price - expected) / expected * 100) if expected > 0 else 0
            return ExecutionResult(
                True, result.filled_price or expected, expected, slippage,
                ExecutionType.MARKET, latency,
            )
        return ExecutionResult(False, 0, 0, 0, ExecutionType.MARKET, latency, result.error_message)

    def _log_slippage(self, symbol: str, slippage: float):
        self._slippage_log.setdefault(symbol, []).append({
            'slippage': slippage, 'time': datetime.now().isoformat(),
        })
        if len(self._slippage_log[symbol]) > self.slippage_log_max:
            self._slippage_log[symbol].pop(0)

    def get_slippage_stats(self, symbol: str) -> Dict:
        logs = self._slippage_log.get(symbol, [])
        if not logs:
            return {'avg': 0, 'max': 0, 'count': 0}
        values = [l['slippage'] for l in logs]
        return {
            'avg': round(sum(values)/len(values), 3),
            'max': round(max(values), 3),
            'count': len(values),
        }

    def recommend_execution_type(self, symbol: str) -> ExecutionType:
        tick = self.broker.get_tick(symbol)
        sym_info = self.broker.get_symbol_info(symbol)
        if not tick or not sym_info:
            return ExecutionType.MARKET
        spread = (tick.ask - tick.bid) / sym_info.point if sym_info.point > 0 else 0
        median = self._get_spread_median(symbol)
        if spread <= median * 1.5:
            return ExecutionType.LIMIT
        return ExecutionType.MARKET
