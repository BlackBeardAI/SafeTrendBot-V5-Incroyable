"""
Prop Firm Challenge Mode — respecte automatiquement les règles FTMO/TFF/MFF.
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime, timedelta


@dataclass
class PropFirmRules:
    """Règles standard des prop firms"""
    name: str
    max_daily_loss_pct: float = 5.0
    max_total_loss_pct: float = 10.0
    profit_target_pct: float = 10.0
    min_trading_days: int = 4
    max_trading_days: int = 30
    max_position_size: float = 999  # lots max
    forbidden_symbols: list = None
    weekend_hold: bool = False  # Autoriser positions weekend


class PropFirmManager:
    """
    Gère le compte en mode Prop Firm Challenge.
    Bloque automatiquement si les règles sont violées.
    """

    PRESETS = {
        'ftmo': PropFirmRules('FTMO', max_daily_loss_pct=5.0, max_total_loss_pct=10.0,
                               profit_target_pct=10.0, min_trading_days=4, max_trading_days=30,
                               weekend_hold=False),
        'the5ers': PropFirmRules('The5ers', max_daily_loss_pct=5.0, max_total_loss_pct=10.0,
                                 profit_target_pct=10.0, min_trading_days=3, max_trading_days=60,
                                 weekend_hold=True),
        'funded_trader': PropFirmRules('Funded Trader', max_daily_loss_pct=5.0, max_total_loss_pct=10.0,
                                       profit_target_pct=10.0, min_trading_days=3, max_trading_days=35,
                                       weekend_hold=False),
        'custom': PropFirmRules('Custom'),
    }

    def __init__(self, preset: str = 'ftmo', initial_balance: float = 10000.0):
        self.rules = self.PRESETS.get(preset, self.PRESETS['ftmo'])
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.today_start = initial_balance
        self.trading_days: set = set()
        self.today = datetime.now().date()
        self._target_reached = False
        self._failed = False
        self._fail_reason = ""

    def update(self, balance: float, equity: float, open_positions: int) -> tuple:
        """
        Vérifie les règles à chaque tick.
        Retourne (can_trade, status_dict).
        """
        if self._failed:
            return False, {'status': 'FAILED', 'reason': self._fail_reason}
        if self._target_reached:
            return False, {'status': 'PASSED', 'reason': 'Profit target atteint!'}

        now = datetime.now()
        today = now.date()

        # Reset quotidien
        if today != self.today:
            self.today_start = balance
            self.today = today

        # Update peak
        if equity > self.peak_balance:
            self.peak_balance = equity

        # Règle 1 : Daily loss limit
        daily_loss = (self.today_start - equity) / self.initial_balance * 100
        if daily_loss >= self.rules.max_daily_loss_pct:
            self._failed = True
            self._fail_reason = f"Daily loss {daily_loss:.1f}% ≥ {self.rules.max_daily_loss_pct}%"
            return False, {'status': 'FAILED', 'reason': self._fail_reason}

        # Règle 2 : Total loss limit
        total_loss = (self.initial_balance - equity) / self.initial_balance * 100
        if total_loss >= self.rules.max_total_loss_pct:
            self._failed = True
            self._fail_reason = f"Total loss {total_loss:.1f}% ≥ {self.rules.max_total_loss_pct}%"
            return False, {'status': 'FAILED', 'reason': self._fail_reason}

        # Règle 3 : Profit target
        profit_pct = (equity - self.initial_balance) / self.initial_balance * 100
        if profit_pct >= self.rules.profit_target_pct:
            self._target_reached = True
            return False, {'status': 'PASSED', 'reason': f'Profit {profit_pct:.1f}% target atteint!'}

        # Règle 4 : Trading days
        if open_positions > 0:
            self.trading_days.add(today)

        # Règle 5 : Weekend hold
        if now.weekday() >= 5 and open_positions > 0 and not self.rules.weekend_hold:
            return False, {'status': 'BLOCKED', 'reason': 'Fermeture weekend requise'}

        return True, {
            'status': 'ACTIVE',
            'daily_loss_pct': round(daily_loss, 2),
            'total_loss_pct': round(total_loss, 2),
            'profit_pct': round(profit_pct, 2),
            'trading_days': len(self.trading_days),
            'days_remaining': self.rules.max_trading_days - (today - min(self.trading_days or [today])).days if self.trading_days else self.rules.max_trading_days,
        }

    def get_progress(self) -> str:
        """Affiche la progression du challenge"""
        status, info = self.update(self.today_start, self.today_start, 0)
        if info['status'] == 'ACTIVE':
            return (f"🏆 Prop Firm {self.rules.name} | "
                    f"Jours: {info['trading_days']}/{self.rules.min_trading_days} | "
                    f"P&L: {info['profit_pct']:.1f}%/{self.rules.profit_target_pct}% | "
                    f"DD: {info['total_loss_pct']:.1f}%/{self.rules.max_total_loss_pct}%")
        return f"🏆 {info['status']}: {info['reason']}"
