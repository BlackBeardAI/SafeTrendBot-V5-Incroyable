"""
Circuit Breaker par symbole — protège chaque actif individuellement.
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict


class SymbolCBStatus(Enum):
    OK = "ok"
    WARNING = "warning"
    HALTED = "halted"


@dataclass
class SymbolCircuitState:
    symbol: str
    status: SymbolCBStatus
    today_trades: int = 0
    today_pnl: float = 0.0
    consecutive_losses: int = 0
    max_drawdown_today: float = 0.0
    last_trade_time: Optional[datetime] = None
    reasons: List[str] = field(default_factory=list)


class SymbolCircuitBreaker:
    """
    Circuit breaker indépendant pour chaque symbole.
    Si EURUSD crashe, on continue sur GBPUSD.
    """

    def __init__(self,
                 max_daily_loss_pct: float = 5.0,
                 max_consecutive_losses: int = 3,
                 max_trades_per_hour: int = 3,
                 cooldown_minutes_after_loss: int = 30):
        self.max_daily_loss = max_daily_loss_pct
        self.max_consec_losses = max_consecutive_losses
        self.max_trades_hour = max_trades_per_hour
        self.cooldown = cooldown_minutes_after_loss
        self._states: Dict[str, SymbolCircuitState] = {}
        self._trade_history: Dict[str, List[datetime]] = defaultdict(list)

    def _get_state(self, symbol: str) -> SymbolCircuitState:
        if symbol not in self._states:
            self._states[symbol] = SymbolCircuitState(symbol=symbol, status=SymbolCBStatus.OK)
        return self._states[symbol]

    def record_trade(self, symbol: str, profit: float):
        state = self._get_state(symbol)
        state.today_trades += 1
        state.today_pnl += profit
        state.last_trade_time = datetime.now()
        self._trade_history[symbol].append(datetime.now())

        if profit < 0:
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0

        # Nettoyer vieux trades (dernière heure)
        cutoff = datetime.now() - timedelta(hours=1)
        self._trade_history[symbol] = [t for t in self._trade_history[symbol] if t > cutoff]

    def check(self, symbol: str) -> SymbolCircuitState:
        state = self._get_state(symbol)
        state.status = SymbolCBStatus.OK
        state.reasons = []

        # 1. Daily loss
        if state.today_pnl < -self.max_daily_loss:
            state.status = SymbolCBStatus.HALTED
            state.reasons.append(f"Perte journalière {state.today_pnl:.1f}% > max {self.max_daily_loss}%")

        # 2. Consecutive losses
        if state.consecutive_losses >= self.max_consec_losses:
            state.status = SymbolCBStatus.HALTED
            state.reasons.append(f"{state.consecutive_losses} pertes consécutives")

        # 3. Trades par heure
        if len(self._trade_history[symbol]) >= self.max_trades_hour:
            state.status = SymbolCBStatus.WARNING
            state.reasons.append(f"{len(self._trade_history[symbol])} trades/heure (max {self.max_trades_hour})")

        # 4. Cooldown après perte
        if state.consecutive_losses > 0 and state.last_trade_time:
            elapsed = (datetime.now() - state.last_trade_time).total_seconds() / 60
            if elapsed < self.cooldown:
                state.status = SymbolCBStatus.WARNING
                state.reasons.append(f"Cooldown : {self.cooldown - int(elapsed)} min restantes")

        return state

    def reset_symbol(self, symbol: str):
        if symbol in self._states:
            del self._states[symbol]
        if symbol in self._trade_history:
            del self._trade_history[symbol]

    def reset_all(self):
        self._states.clear()
        self._trade_history.clear()
