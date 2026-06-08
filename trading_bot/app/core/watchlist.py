"""
Module Watchlist : surveillance de symboles avec alertes de prix.
Permet de définir des seuils (au-dessus / en-dessous) et d'être notifié quand atteints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from datetime import datetime


class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"


class AlertStatus(Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


@dataclass
class PriceAlert:
    """Alerte de prix individuelle"""
    symbol: str
    alert_type: AlertType
    threshold: float
    note: str = ""
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None
    trigger_price: Optional[float] = None
    notify_telegram: bool = True
    notify_desktop: bool = True

    def check(self, current_price: float) -> bool:
        """Vérifie si l'alerte doit se déclencher au prix actuel"""
        if self.status != AlertStatus.ACTIVE:
            return False

        triggered = False
        if self.alert_type == AlertType.PRICE_ABOVE:
            triggered = current_price >= self.threshold
        elif self.alert_type == AlertType.PRICE_BELOW:
            triggered = current_price <= self.threshold

        if triggered:
            self.status = AlertStatus.TRIGGERED
            self.triggered_at = datetime.now()
            self.trigger_price = current_price
        return triggered


@dataclass
class WatchlistEntry:
    """Symbole surveillé (sans forcément trader)"""
    symbol: str
    note: str = ""
    added_at: datetime = field(default_factory=datetime.now)
    alerts: List[PriceAlert] = field(default_factory=list)


class WatchlistManager:
    """Gestionnaire de la watchlist"""

    def __init__(self):
        self.entries: List[WatchlistEntry] = []

    def add_symbol(self, symbol: str, note: str = "") -> WatchlistEntry:
        """Ajoute un symbole à la watchlist (ignore si déjà présent)"""
        for e in self.entries:
            if e.symbol == symbol:
                return e
        entry = WatchlistEntry(symbol=symbol, note=note)
        self.entries.append(entry)
        return entry

    def remove_symbol(self, symbol: str) -> bool:
        """Retire un symbole et ses alertes"""
        for i, e in enumerate(self.entries):
            if e.symbol == symbol:
                del self.entries[i]
                return True
        return False

    def add_alert(self, symbol: str, alert: PriceAlert) -> bool:
        """Ajoute une alerte sur un symbole (l'ajoute à la watchlist si absent)"""
        entry = self.add_symbol(symbol)
        entry.alerts.append(alert)
        return True

    def check_alerts(self, symbol: str, price: float) -> List[PriceAlert]:
        """Vérifie toutes les alertes pour un prix donné. Retourne celles déclenchées."""
        triggered = []
        for entry in self.entries:
            if entry.symbol != symbol:
                continue
            for alert in entry.alerts:
                if alert.check(price):
                    triggered.append(alert)
        return triggered

    def get_active_symbols(self) -> List[str]:
        """Liste des symboles à surveiller (avec au moins 1 alerte active ou juste watchés)"""
        return [e.symbol for e in self.entries]

    def to_dict(self) -> dict:
        """Sérialisation pour sauvegarde"""
        return {
            'entries': [
                {
                    'symbol': e.symbol,
                    'note': e.note,
                    'added_at': e.added_at.isoformat(),
                    'alerts': [
                        {
                            'symbol': a.symbol,
                            'alert_type': a.alert_type.value,
                            'threshold': a.threshold,
                            'note': a.note,
                            'status': a.status.value,
                            'created_at': a.created_at.isoformat(),
                            'triggered_at': a.triggered_at.isoformat() if a.triggered_at else None,
                            'trigger_price': a.trigger_price,
                            'notify_telegram': a.notify_telegram,
                            'notify_desktop': a.notify_desktop,
                        }
                        for a in e.alerts
                    ]
                }
                for e in self.entries
            ]
        }

    def from_dict(self, data: dict):
        """Chargement depuis sérialisation"""
        self.entries = []
        for ed in data.get('entries', []):
            try:
                entry = WatchlistEntry(
                    symbol=ed['symbol'],
                    note=ed.get('note', ''),
                    added_at=datetime.fromisoformat(ed['added_at']),
                )
                for ad in ed.get('alerts', []):
                    alert = PriceAlert(
                        symbol=ad['symbol'],
                        alert_type=AlertType(ad['alert_type']),
                        threshold=ad['threshold'],
                        note=ad.get('note', ''),
                        status=AlertStatus(ad['status']),
                        created_at=datetime.fromisoformat(ad['created_at']),
                        triggered_at=(datetime.fromisoformat(ad['triggered_at'])
                                      if ad.get('triggered_at') else None),
                        trigger_price=ad.get('trigger_price'),
                        notify_telegram=ad.get('notify_telegram', True),
                        notify_desktop=ad.get('notify_desktop', True),
                    )
                    entry.alerts.append(alert)
                self.entries.append(entry)
            except Exception as e:
                print(f"Erreur chargement entrée watchlist: {e}")


# Instance singleton
_watchlist_instance: Optional[WatchlistManager] = None


def get_watchlist() -> WatchlistManager:
    """Récupère l'instance singleton de la watchlist"""
    global _watchlist_instance
    if _watchlist_instance is None:
        _watchlist_instance = WatchlistManager()
    return _watchlist_instance
