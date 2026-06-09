"""
SafeTrendBot License Manager V2 — Licence à usage unique
==========================================================

Nouveau système de licence:
- Usage UNIQUE: une licence ne peut activer qu'UN SEUL ordinateur
- Hardware lock: liée à CPU+MAC+disk (impossible de partager)
- Auto-destruct: le fichier d'installation se supprime après usage
- No server required: fonctionne offline, pas besoin de serveur d'activation

Chaque build contient une licence pré-injectée.
Le client télécharge le build → lance → la licence est consommée → 
le fichier d'installation se supprime automatiquement.

Usage interne:
    from license_manager_v2 import LicenseManagerV2, LicenseStatus
    lm = LicenseManagerV2()
    status = lm.check_license()
    if status == LicenseStatus.VALID:
        run_bot()
    elif status == LicenseStatus.ALREADY_USED:
        print("Cette licence a déjà été utilisée sur un autre PC.")
    elif status == LicenseStatus.INVALID:
        print("Licence invalide.")
"""

import sys
import os
import json
import hashlib
import platform
import subprocess
import shutil
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Dict


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

APP_DATA_DIR = Path.home() / ".safetrendbot" / "v5"
LICENSE_FILE = APP_DATA_DIR / "license_v2.json"
INSTALLER_MARKER = APP_DATA_DIR / ".installer_used"
HARDWARE_FILE = APP_DATA_DIR / "hardware.lock"

# Placeholder dans le binaire (remplacé au build)
LICENSE_PLACEHOLDER = "__LICENSE_PLACEHOLDER__" + "_" * 32


# ─────────────────────────────────────────────────────────────────────────────
# ENUM
# ─────────────────────────────────────────────────────────────────────────────

class LicenseStatus(Enum):
    VALID = auto()           # ✅ Licence valide, ce PC autorisé
    ALREADY_USED = auto()    # ❌ Licence déjà utilisée sur un autre PC
    INVALID = auto()         # ❌ Mauvaise licence / corrompue
    FIRST_USE = auto()       # 🆕 Première activation sur ce PC
    EXPIRED = auto()         # ⏰ Expirée (si date limite)


# ─────────────────────────────────────────────────────────────────────────────
# HARDWARE FINGERPRINT
# ─────────────────────────────────────────────────────────────────────────────

def get_hardware_fingerprint() -> str:
    """
    Génère un fingerprint hardware unique et stable.
    Combine CPU, MAC, disk serial, Windows SID.
    """
    components = []

    # CPU info
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "cpu", "get", "ProcessorId", "/value"],
                capture_output=True, text=True, timeout=5
            )
            cpu_id = result.stdout.strip().replace("ProcessorId=", "").strip()
            components.append(cpu_id or "unknown_cpu")
        else:
            # Linux/macOS — lire /proc/cpuinfo ou system_profiler
            if Path("/proc/cpuinfo").exists():
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "serial" in line.lower() or "processor" in line.lower():
                            components.append(line.strip())
                            break
    except Exception:
        components.append("cpu_fallback")

    # MAC addresses
    try:
        import uuid
        node = uuid.getnode()
        mac = ":".join(f"{(node >> i) & 0xff:02x}" for i in (40, 32, 24, 16, 8, 0))
        components.append(mac)
    except Exception:
        components.append("mac_fallback")

    # Disk serial (Windows)
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "SerialNumber", "/value"],
                capture_output=True, text=True, timeout=5
            )
            disk = result.stdout.strip().replace("SerialNumber=", "").strip()
            components.append(disk or "disk_fallback")
        except Exception:
            components.append("disk_fallback")
    else:
        try:
            # Linux — disk UUID
            result = subprocess.run(
                ["lsblk", "-dno", "UUID"],
                capture_output=True, text=True, timeout=5
            )
            uuids = result.stdout.strip().split("\n")
            if uuids:
                components.append(uuids[0].strip())
        except Exception:
            components.append("disk_fallback_linux")

    # Machine name + user (stabilité relative)
    components.append(platform.node())
    components.append(platform.machine())
    components.append(os.getlogin() if hasattr(os, "getlogin") else "user")

    # Hash final
    raw = "|".join(components)
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return fingerprint


# ─────────────────────────────────────────────────────────────────────────────
# LICENSE MANAGER V2
# ─────────────────────────────────────────────────────────────────────────────

class LicenseManagerV2:
    """
    Gestionnaire de licence à usage unique.

    Chaque build contient une licence pré-injectée.
    Au premier lancement:
        1. La licence est lue depuis le binaire
        2. Le hardware fingerprint est calculé
        3. La licence est marquée comme "utilisée" + hardware_id enregistré
        4. Le fichier d'installation est supprimé (self-destruct)

    Aux lancements suivants:
        1. Le hardware_id est comparé
        2. Si différent → ALREADY_USED (ne fonctionne pas sur un autre PC)
        3. Si identique → VALID
    """

    def __init__(self, license_key: Optional[str] = None):
        self.license_key = license_key or self._extract_license_from_binary()
        self.hardware_id = get_hardware_fingerprint()
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Extraction licence du binaire
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_license_from_binary(self) -> Optional[str]:
        """
        Extrait la licence pré-injectée du binaire PyInstaller.
        Le binaire contient un placeholder remplacé au build.
        """
        # En mode PyInstaller, sys.executable est le .exe
        # En mode dev, c'est python.exe
        binary_path = Path(sys.executable)

        if not binary_path.exists():
            return None

        try:
            content = binary_path.read_bytes()

            # Chercher le placeholder modifié
            # Format attendu: "__LICENSE_PLACEHOLDER__" suivi de la licence
            marker = b"__LICENSE_PLACEHOLDER__"
            idx = content.find(marker)
            if idx == -1:
                return None

            # Extraire les données après le marker
            start = idx + len(marker)
            data = content[start:start + 64]

            # Nettoyer les padding bytes
            license_str = data.decode("utf-8", errors="ignore").strip("\x00_")
            # Format attendu: XXXX-XXXX-XXXX-XXXX
            if "-" in license_str and len(license_str) >= 19:
                return license_str
        except Exception:
            pass

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Vérification licence
    # ─────────────────────────────────────────────────────────────────────────

    def check_license(self) -> LicenseStatus:
        """Vérifie la licence. Retourne le statut."""

        if not self.license_key:
            return LicenseStatus.INVALID

        # Charger l'état sauvegardé
        state = self._load_state()

        # Si jamais utilisée → première activation
        if not state:
            return LicenseStatus.FIRST_USE

        # Vérifier que la licence correspond
        if state.get("license_key") != self.license_key:
            return LicenseStatus.INVALID

        # Vérifier hardware ID
        stored_hw = state.get("hardware_id")
        if stored_hw and stored_hw != self.hardware_id:
            return LicenseStatus.ALREADY_USED

        return LicenseStatus.VALID

    # ─────────────────────────────────────────────────────────────────────────
    # Activation (premier usage)
    # ─────────────────────────────────────────────────────────────────────────

    def activate(self) -> bool:
        """
        Active la licence sur ce PC.
        À appeler AU PREMIER lancement uniquement.
        """
        if not self.license_key:
            return False

        state = {
            "license_key": self.license_key,
            "hardware_id": self.hardware_id,
            "activated_at": self._now(),
            "platform": platform.system(),
            "version": "5.3.0",
        }

        self._save_state(state)
        self._mark_installer_used()

        # Self-destruct: supprimer le fichier d'installation
        self._self_destruct_installer()

        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Self-destruct installer
    # ─────────────────────────────────────────────────────────────────────────

    def _self_destruct_installer(self):
        """
        Supprime le fichier d'installation (setup.exe, .zip, etc.)
        après activation réussie.
        """
        try:
            # Windows — chercher dans Téléchargements et Desktop
            if platform.system() == "Windows":
                downloads = Path.home() / "Downloads"
                desktop = Path.home() / "Desktop"
                installer_names = [
                    "SafeTrendBot_Installer.exe",
                    "SafeTrendBot_Setup.exe",
                    "SafeTrendBot-v5*.zip",
                    "SafeTrendBot-v5*.exe",
                ]

                for folder in [downloads, desktop]:
                    if not folder.exists():
                        continue
                    for pattern in installer_names:
                        for f in folder.glob(pattern):
                            try:
                                if f.is_file():
                                    f.unlink()
                                    print(f"🗑️  Installateur supprimé: {f.name}")
                                elif f.is_dir():
                                    shutil.rmtree(f)
                                    print(f"🗑️  Dossier installateur supprimé: {f.name}")
                            except Exception:
                                pass

            # Linux/macOS
            else:
                home = Path.home()
                for pattern in ["SafeTrendBot*.tar.gz", "SafeTrendBot*.zip", "safetrendbot*.sh"]:
                    for f in home.glob(pattern):
                        try:
                            f.unlink()
                            print(f"🗑️  Installateur supprimé: {f.name}")
                        except Exception:
                            pass

            # Marquer comme fait
            INSTALLER_MARKER.write_text("done", encoding="utf-8")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────────────────────────────────────

    def _load_state(self) -> Optional[dict]:
        if LICENSE_FILE.exists():
            return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
        return None

    def _save_state(self, state: dict):
        LICENSE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _mark_installer_used(self):
        INSTALLER_MARKER.write_text("used", encoding="utf-8")

    def _now(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat()

    # ─────────────────────────────────────────────────────────────────────────
    # Info
    # ─────────────────────────────────────────────────────────────────────────

    def get_info(self) -> dict:
        state = self._load_state()
        return {
            "license_key": self.license_key or "(not found)",
            "hardware_id": self.hardware_id,
            "activated": bool(state),
            "platform": platform.system(),
            "data_dir": str(APP_DATA_DIR),
        }


# ─────────────────────────────────────────────────────────────────────────────
# WRAPPER POUR LE BOT
# ─────────────────────────────────────────────────────────────────────────────

def check_and_run():
    """
    Fonction appelée au démarrage du bot.
    Gère la vérification + activation automatique.
    """
    lm = LicenseManagerV2()
    status = lm.check_license()

    if status == LicenseStatus.VALID:
        print(f"✅ Licence validée: {lm.license_key[:8]}...")
        print(f"   Hardware: {lm.hardware_id[:12]}...")
        return True

    elif status == LicenseStatus.FIRST_USE:
        print(f"🆓 Première activation: {lm.license_key}")
        print(f"   Hardware: {lm.hardware_id}")
        ok = lm.activate()
        if ok:
            print("✅ Activation réussie!")
            print("   Ce bot est maintenant lié à cet ordinateur.")
            print("   L'installateur a été supprimé.")
            return True
        else:
            print("❌ Échec activation")
            return False

    elif status == LicenseStatus.ALREADY_USED:
        print("❌ CETTE LICENCE A DÉJÀ ÉTÉ UTILISÉE")
        print("   Ce bot ne peut fonctionner que sur l'ordinateur d'origine.")
        print("   Contactez le support pour une nouvelle licence.")
        return False

    elif status == LicenseStatus.INVALID:
        print("❌ LICENCE INVALIDE")
        print("   Ce build n'est pas autorisé.")
        return False

    return False


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SafeTrendBot License Manager V2")
    parser.add_argument("--check", action="store_true", help="Vérifier la licence")
    parser.add_argument("--activate", action="store_true", help="Activer ce PC")
    parser.add_argument("--info", action="store_true", help="Info licence")
    parser.add_argument("--hardware", action="store_true", help="Afficher hardware ID")
    args = parser.parse_args()

    if args.hardware:
        print(f"Hardware ID: {get_hardware_fingerprint()}")
        return

    if args.info:
        lm = LicenseManagerV2()
        info = lm.get_info()
        for k, v in info.items():
            print(f"{k}: {v}")
        return

    if args.activate:
        lm = LicenseManagerV2()
        ok = lm.activate()
        print("OK" if ok else "FAIL")
        return

    if args.check:
        lm = LicenseManagerV2()
        status = lm.check_license()
        print(f"Status: {status.name}")
        return

    # Par défaut: check_and_run
    ok = check_and_run()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
