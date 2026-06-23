"""
SafeTrendBot — PIN Lock (NEUTRALISÉ)
=====================================
Stub de verrouillage par PIN. Toutes les vérifications sont désactivées.
Le bot fonctionne sans PIN, sans restriction d'accès.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PinConfig:
    """Configuration du PIN — stub neutralisé."""
    enabled: bool = False
    pin_hash: str = ""
    lock_on_startup: bool = False
    lock_on_idle_minutes: int = 0
    max_attempts: int = 5
    auto_lock_minutes: int = 30
    salt: str = ""
    require_pin_for_trading: bool = False
    require_pin_for_settings: bool = False

    def set_pin(self, pin: str) -> None:
        """Active le PIN (stub — ne fait rien de sécurisé)."""
        self.enabled = True
        self.pin_hash = f"stub_{hash(pin)}"

    def verify_pin(self, pin: str) -> bool:
        """Vérifie le PIN (stub — toujours True si PIN défini)."""
        return True

    def disable(self) -> None:
        """Désactive le PIN."""
        self.enabled = False
        self.pin_hash = ""
        self.lock_on_startup = False

    def is_enabled(self) -> bool:
        """Retourne True si le PIN est activé."""
        return self.enabled

    def to_dict(self) -> dict:
        return {
            'enabled': self.enabled,
            'pin_hash': self.pin_hash,
            'lock_on_startup': self.lock_on_startup,
            'max_attempts': self.max_attempts,
            'auto_lock_minutes': self.auto_lock_minutes,
            'salt': self.salt,
        }