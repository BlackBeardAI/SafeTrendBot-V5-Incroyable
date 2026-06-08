"""
Système de verrouillage de l'application par PIN.
Le PIN est stocké hashé (SHA-256 + sel) dans le fichier de config.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Optional


def hash_pin(pin: str, salt: str) -> str:
    """Hash un PIN avec sel via SHA-256 (10000 itérations)."""
    pin_bytes = pin.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    derived = hashlib.pbkdf2_hmac('sha256', pin_bytes, salt_bytes, 10000)
    return derived.hex()


def generate_salt() -> str:
    """Génère un sel cryptographique aléatoire."""
    return secrets.token_hex(16)


@dataclass
class PinConfig:
    """Configuration du verrouillage PIN"""
    enabled: bool = False
    pin_hash: str = ""
    salt: str = ""
    lock_on_startup: bool = True       # Verrouille au démarrage
    lock_on_idle_minutes: int = 0      # 0 = jamais. Sinon timer d'inactivité
    max_attempts: int = 5              # Nombre max d'essais avant délai
    require_pin_for_trading: bool = True  # PIN requis pour démarrer le bot

    def set_pin(self, pin: str):
        """Définit un nouveau PIN (4-12 chiffres)"""
        if not pin or not pin.isdigit() or not (4 <= len(pin) <= 12):
            raise ValueError("Le PIN doit être de 4 à 12 chiffres")
        self.salt = generate_salt()
        self.pin_hash = hash_pin(pin, self.salt)
        self.enabled = True

    def verify_pin(self, pin: str) -> bool:
        """Vérifie un PIN"""
        if not self.enabled or not self.pin_hash or not self.salt:
            return False
        try:
            return hash_pin(pin, self.salt) == self.pin_hash
        except Exception:
            return False

    def disable(self):
        """Désactive le verrouillage PIN"""
        self.enabled = False
        self.pin_hash = ""
        self.salt = ""
