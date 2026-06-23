"""
Risk-Off automatique — ferme les positions avant les événements économiques majeurs.
"""
import time
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import threading
import logging

logger = logging.getLogger("risk_off_manager")


@dataclass
class EconomicEvent:
    time: datetime
    name: str
    currency: str
    impact: str  # 'low', 'medium', 'high', 'red'
    forecast: Optional[str] = None
    previous: Optional[str] = None


class RiskOffManager:
    """
    Ferme les positions ou bloque les nouvelles entrées avant les events économiques.
    """

    HIGH_IMPACT_EVENTS = {
        'NFP', 'Non-Farm Payrolls', 'CPI', 'Inflation Rate', 'GDP',
        'Interest Rate', 'FOMC', 'Fed', 'ECB', 'BOE', 'BOJ',
        'Retail Sales', 'Unemployment Rate', 'PMI', 'ISM',
        'ADP', 'Initial Jobless Claims',
    }

    def __init__(self, broker, minutes_before: int = 15, minutes_after: int = 30,
                 close_positions: bool = True):
        self.broker = broker
        self.minutes_before = minutes_before
        self.minutes_after = minutes_after
        self.close_positions = close_positions
        self._upcoming_events: List[EconomicEvent] = []
        self._risk_off_active = False
        self._risk_off_until: Optional[datetime] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()

    def start_monitoring(self):
        """Lance le thread de surveillance des events"""
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        while not self._stop_flag.is_set():
            try:
                self._fetch_events()
                self._check_risk_off()
                self._stop_flag.wait(60)  # Vérifie toutes les minutes
            except Exception as e:
                logger.warning(f"[RiskOff] Erreur: {e}")
                time.sleep(60)

    def _fetch_events(self):
        """Récupère les events du calendrier éco"""
        try:
            from bot.economic_calendar import EconomicCalendar
            cal = EconomicCalendar()
            events = cal.get_events_for_today()
            self._upcoming_events = [
                EconomicEvent(
                    time=e.get('time', datetime.now()),
                    name=e.get('name', ''),
                    currency=e.get('currency', ''),
                    impact=e.get('impact', 'low'),
                ) for e in events if e.get('impact') in ('high', 'red')
            ]
        except Exception:
            pass

    def _check_risk_off(self):
        now = datetime.now()
        active = False
        until = None

        for event in self._upcoming_events:
            if event.time <= now <= event.time + timedelta(minutes=self.minutes_after):
                active = True
                until = event.time + timedelta(minutes=self.minutes_after)
                break
            elif now <= event.time <= now + timedelta(minutes=self.minutes_before):
                active = True
                until = event.time + timedelta(minutes=self.minutes_after)
                # Fermer les positions si configuré
                if self.close_positions and not self._risk_off_active:
                    self._close_all_positions(event.name)
                break

        self._risk_off_active = active
        self._risk_off_until = until

    def _close_all_positions(self, reason: str):
        if not self.broker:
            return
        try:
            positions = self.broker.get_positions()
            for pos in positions:
                self.broker.close_position(pos.ticket)
                print(f"[RiskOff] Position {pos.ticket} fermée avant: {reason}")
        except Exception as e:
            logger.warning(f"[RiskOff] Erreur fermeture: {e}")

    def is_risk_off(self) -> tuple:
        """Retourne (active, reason, until)"""
        if self._risk_off_active and self._risk_off_until:
            remaining = int((self._risk_off_until - datetime.now()).total_seconds() / 60)
            return True, f"Risk-Off actif ({remaining} min restantes)", self._risk_off_until
        return False, "", None

    def can_trade(self) -> bool:
        return not self._risk_off_active
