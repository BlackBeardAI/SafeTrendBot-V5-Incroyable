"""
ExtremeGuard — Système de sécurité pour le mode EXTREME.

Gère :
- Compteur de pertes consécutives (arrêt après N)
- Compteur de trades par jour (hard cap)
- Désactivation automatique après N heures
- Cooldown entre trades (minutes)
- PIN requis à l'activation
- Circuit breaker sur daily loss / drawdown

Ce module est conçu pour protéger l'utilisateur des risques extrêmes
inclus dans le mode EXTREME. Il est INDÉPENDANT du trading engine
et peut être utilisé en mode live comme paper.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from threading import Lock
from datetime import datetime, timedelta


@dataclass
class ExtremeGuardState:
    """État persistant du guardian"""
    activated_at: Optional[str] = None          # ISO datetime
    total_trades_today: int = 0
    consecutive_losses: int = 0
    last_trade_time: Optional[str] = None       # ISO datetime
    daily_pnl: float = 0.0
    cumulative_pnl: float = 0.0
    peak_balance: float = 0.0
    is_locked: bool = False                      # Lock après trop de pertes
    lock_reason: str = ""
    lock_time: Optional[str] = None


class ExtremeGuard:
    """
    Gardien de sécurité pour le mode EXTREME.
    Doit être instancié une fois par session trading.
    """

    def __init__(
        self,
        max_consecutive_losses: int = 3,
        max_trades_per_day: int = 15,
        time_limit_hours: int = 48,
        cooldown_minutes: int = 5,
        daily_loss_limit_pct: float = 8.0,
        max_drawdown_pct: float = 30.0,
        leverage_cap: float = 3.0,
        state_dir: Optional[Path] = None,
    ):
        self.max_consecutive_losses = max_consecutive_losses
        self.max_trades_per_day = max_trades_per_day
        self.time_limit_hours = time_limit_hours
        self.cooldown_minutes = cooldown_minutes
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.leverage_cap = leverage_cap

        self.state = ExtremeGuardState()
        self._lock = Lock()
        self._state_file = state_dir / "extreme_guard.json" if state_dir else None

        # Vérifications
        self._check_reason: Optional[str] = None
        self._last_check_time: float = 0.0

    # ─────────────────────────────────────────────────────────────────────────

    def activate(self, pin_code: str, expected_pin: str, current_balance: float) -> bool:
        """
        Active le mode EXTREME après vérification du PIN.
        Retourne True si activation réussie.
        """
        if not pin_code or pin_code != expected_pin:
            self._check_reason = "PIN incorrect"
            return False

        with self._lock:
            self.state = ExtremeGuardState()
            self.state.activated_at = datetime.utcnow().isoformat()
            self.state.peak_balance = current_balance
            self.state.is_locked = False
            self.state.lock_reason = ""
            self.state.lock_time = None
            self._save_state()

        self._check_reason = None
        return True

    def can_trade(
        self,
        current_balance: float,
        current_daily_pnl_pct: float,
    ) -> bool:
        """
        Vérifie si un trade est autorisé.
        Met à jour l'état interne et retourne True si OK.
        """
        with self._lock:
            now = datetime.utcnow()
            now_ts = time.time()

            # 1. Vérifier si locké
            if self.state.is_locked:
                self._check_reason = f"🔒 Mode verrouillé : {self.state.lock_reason}"
                return False

            # 2. Vérifier time limit
            if self.state.activated_at:
                activated = datetime.fromisoformat(self.state.activated_at)
                elapsed = (now - activated).total_seconds() / 3600
                if elapsed >= self.time_limit_hours:
                    self.state.is_locked = True
                    self.state.lock_reason = (
                        f"Temps limite atteint ({self.time_limit_hours}h). "
                        "Recharge manuelle requise."
                    )
                    self.state.lock_time = now.isoformat()
                    self._save_state()
                    self._check_reason = self.state.lock_reason
                    return False

            # 3. Vérifier max trades par jour
            if self.state.total_trades_today >= self.max_trades_per_day:
                self._check_reason = (
                    f"Cap journalier atteint ({self.max_trades_per_day} trades)."
                )
                return False

            # 4. Vérifier cooldown
            if self.state.last_trade_time:
                last = datetime.fromisoformat(self.state.last_trade_time)
                elapsed_min = (now - last).total_seconds() / 60
                if elapsed_min < self.cooldown_minutes:
                    remaining = self.cooldown_minutes - int(elapsed_min)
                    self._check_reason = f"Cooldown : attendre {remaining} min"
                    return False

            # 5. Vérifier daily loss limit
            if current_daily_pnl_pct <= -self.daily_loss_limit_pct:
                self.state.is_locked = True
                self.state.lock_reason = (
                    f"Circuit breaker déclenché : perte journalière "
                    f"{-current_daily_pnl_pct:.1f}% >= {self.daily_loss_limit_pct}%"
                )
                self.state.lock_time = now.isoformat()
                self._save_state()
                self._check_reason = self.state.lock_reason
                return False

            # 6. Vérifier drawdown max
            if self.state.peak_balance > 0:
                dd = (self.state.peak_balance - current_balance) / self.state.peak_balance * 100
                if dd >= self.max_drawdown_pct:
                    self.state.is_locked = True
                    self.state.lock_reason = (
                        f"Drawdown max atteint : {dd:.1f}% >= {self.max_drawdown_pct}%"
                    )
                    self.state.lock_time = now.isoformat()
                    self._save_state()
                    self._check_reason = self.state.lock_reason
                    return False

            self._check_reason = None
            self._last_check_time = now_ts
            return True

    def on_trade_opened(self, trade_pnl_estimate: float = 0.0):
        """
        À appeler dès qu'un trade est ouvert.
        """
        with self._lock:
            now = datetime.utcnow()
            self.state.total_trades_today += 1
            self.state.last_trade_time = now.isoformat()
            self._save_state()

    def on_trade_closed(self, realized_pnl: float, current_balance: float):
        """
        À appeler quand un trade se ferme.
        Met à jour les compteurs de pertes consécutives et PnL.
        """
        with self._lock:
            self.state.cumulative_pnl += realized_pnl
            self.state.daily_pnl += realized_pnl

            if realized_pnl < 0:
                self.state.consecutive_losses += 1
            else:
                self.state.consecutive_losses = 0

            # Update peak balance
            if current_balance > self.state.peak_balance:
                self.state.peak_balance = current_balance

            # Check consecutive losses lock
            if self.state.consecutive_losses >= self.max_consecutive_losses:
                self.state.is_locked = True
                self.state.lock_reason = (
                    f"{self.max_consecutive_losses} pertes consécutives atteintes. "
                    "Réflexion et recharge manuelle requises."
                )
                self.state.lock_time = datetime.utcnow().isoformat()

            self._save_state()

    def reset_daily_counters(self):
        """À appeler au début de chaque jour de trading."""
        with self._lock:
            self.state.total_trades_today = 0
            self.state.daily_pnl = 0.0
            self._save_state()

    def manual_unlock(self, pin_code: str, expected_pin: str) -> bool:
        """Déverrouille manuellement après vérification PIN."""
        if pin_code != expected_pin:
            return False
        with self._lock:
            self.state.is_locked = False
            self.state.lock_reason = ""
            self.state.lock_time = None
            self._save_state()
        return True

    @property
    def is_active(self) -> bool:
        """Retourne True si le guardian est actif et non locké."""
        return bool(self.state.activated_at) and not self.state.is_locked

    @property
    def last_reason(self) -> Optional[str]:
        """Dernière raison de blocage."""
        return self._check_reason

    @property
    def status_summary(self) -> Dict:
        """Résumé de l'état pour l'UI / logs."""
        with self._lock:
            return {
                "active": self.is_active,
                "locked": self.state.is_locked,
                "lock_reason": self.state.lock_reason,
                "trades_today": self.state.total_trades_today,
                "max_trades": self.max_trades_per_day,
                "consecutive_losses": self.state.consecutive_losses,
                "max_consecutive": self.max_consecutive_losses,
                "daily_pnl": round(self.state.daily_pnl, 2),
                "cumulative_pnl": round(self.state.cumulative_pnl, 2),
                "peak_balance": round(self.state.peak_balance, 2),
                "time_remaining_hours": self._time_remaining(),
            }

    def _time_remaining(self) -> Optional[float]:
        if not self.state.activated_at:
            return None
        activated = datetime.fromisoformat(self.state.activated_at)
        elapsed = (datetime.utcnow() - activated).total_seconds() / 3600
        remaining = self.time_limit_hours - elapsed
        return round(max(0.0, remaining), 1)

    def _save_state(self):
        if self._state_file:
            try:
                self._state_file.parent.mkdir(parents=True, exist_ok=True)
                self._state_file.write_text(
                    json.dumps(self.state.__dict__, indent=2, default=str),
                    encoding="utf-8",
                )
            except Exception:
                pass

    def _load_state(self):
        if self._state_file and self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                self.state = ExtremeGuardState(**data)
            except Exception:
                pass

    @classmethod
    def from_profile(cls, profile, state_dir: Optional[Path] = None):
        """Instancie un guard à partir d'un TradingProfile EXTREME."""
        return cls(
            max_consecutive_losses=profile.max_consecutive_losses,
            max_trades_per_day=profile.max_trades_per_day,
            time_limit_hours=profile.time_limit_hours or 48,
            cooldown_minutes=profile.cooldown_between_trades_min,
            daily_loss_limit_pct=profile.max_daily_loss_pct,
            max_drawdown_pct=profile.max_drawdown_pct,
            leverage_cap=profile.leverage_cap,
            state_dir=state_dir,
        )
