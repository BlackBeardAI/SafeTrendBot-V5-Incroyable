"""
ExtremeGuard (NEUTRALISÉ) — ne limite plus rien.
Garde l'interface pour compatibilité mais sans restrictions.
"""
import time
from dataclasses import dataclass, field
from typing import Optional
from threading import Lock
from datetime import datetime


@dataclass
class ExtremeGuardState:
    activated_at: Optional[str] = None
    total_trades_today: int = 0
    consecutive_losses: int = 0
    last_trade_time: Optional[str] = None
    daily_pnl: float = 0.0
    cumulative_pnl: float = 0.0
    peak_balance: float = 0.0
    is_locked: bool = False
    lock_reason: str = ""
    lock_time: Optional[str] = None


class ExtremeGuard:
    """Stub — aucune restriction de trading."""

    def __init__(self, *args, **kwargs):
        self.state = ExtremeGuardState()
        self._lock = Lock()

    def can_trade(self) -> bool:
        return True

    def record_trade(self, pnl: float = 0.0) -> None:
        with self._lock:
            self.state.total_trades_today += 1
            self.state.daily_pnl += pnl
            self.state.cumulative_pnl += pnl
            self.state.last_trade_time = datetime.now().isoformat()
            if pnl < 0:
                self.state.consecutive_losses += 1
            else:
                self.state.consecutive_losses = 0

    def check_circuit_breaker(self) -> bool:
        return False  # Jamais déclenché

    def reset_daily(self) -> None:
        with self._lock:
            self.state.total_trades_today = 0
            self.state.daily_pnl = 0.0

    def lock(self, reason: str = "") -> None:
        pass  # Ne lock jamais

    def unlock(self) -> None:
        pass