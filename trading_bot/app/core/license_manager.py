"""
SafeTrendBot — License Manager (NEUTRALISÉ)
============================================
Toutes les vérifications de licence ont été retirées.
Le bot fonctionne sans activation, sans HW-lock, sans restriction.
"""
from enum import Enum
from datetime import datetime
from typing import Tuple, Dict


class LicenseStatus(Enum):
    VALID = "valid"
    INVALID_KEY = "invalid_key"
    HARDWARE_MISMATCH = "hw_mismatch"
    VM_DETECTED = "vm_detected"
    DEBUG_DETECTED = "debug_detected"
    TAMPERED = "tampered"
    NOT_ACTIVATED = "not_activated"
    REVOKED = "revoked"


class LicenseManager:
    """Stub — toujours valide, aucune restriction."""

    def __init__(self, *args, **kwargs):
        pass

    def validate(self) -> Tuple[LicenseStatus, str]:
        return (LicenseStatus.VALID, "Licence valide (mode libre)")

    def check_license(self, verbose: bool = False) -> LicenseStatus:
        if verbose:
            print("[OK] Licence valide — mode libre")
        return LicenseStatus.VALID

    def get_info(self) -> Dict:
        return {
            'valid': True,
            'status': 'valid',
            'hw_id_short': 'FREE',
            'activated_at': datetime.now().isoformat(),
        }

    def activate(self, key: str = "") -> Tuple[bool, str]:
        return (True, "Activation réussie (mode libre)")

    def revoke_local(self) -> None:
        pass

    def generate_license(self, *args, **kwargs) -> str:
        return "STB5-FREE-MODE-LIBRE"


def auto_first_activation() -> Tuple[bool, str]:
    return (True, "Activation automatique (mode libre)")


def auto_activate() -> Tuple[bool, str]:
    return (True, "Activation automatique (mode libre)")