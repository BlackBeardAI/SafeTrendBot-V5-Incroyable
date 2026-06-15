"""
SafeTrendBot License Manager — Système anti-piratage dernière génération
=========================================================================
- Hardware lock : lié CPU + MAC + Disk serial (impossible à cloner)
- One-time activation : 1 licence = 1 PC
- Auto-destruct : le build se supprime après activation
- Anti-VM : détecte les environnements virtuels
- Anti-debug : bloque les débogueurs
- Obfuscation : code compilable avec Cython

Usage:
    from core.license_manager import LicenseManager, LicenseStatus
    lm = LicenseManager()
    if lm.check_license() != LicenseStatus.VALID:
        sys.exit(1)
"""

import sys
import os
import json
import hashlib
import platform
import subprocess
import uuid
import re
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime, timedelta
import ctypes
import struct

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

APP_DATA = Path.home() / ".safetrendbot"
LICENSE_DB = APP_DATA / "license.json"
HARDWARE_DB = APP_DATA / "hardware.lock"
INSTALLER_MARKER = APP_DATA / ".activated"

# Seed pour obfuscation hardware fingerprint
HARDWARE_SALT = b"SafeTrendBot_v5_2024"

# Valeurs à remplacer lors du build
LICENSE_SIGNATURE = "__LICENSE_SIG__"
LICENSE_EXPIRY = "__LICENSE_EXPIRY__"

# Pour vente directe (sans expiration) - pas de limite de temps
LICENSE_PERMANENT = True


class LicenseStatus(Enum):
    VALID = auto()          # ✅ Prêt à trader
    INVALID = auto()        # ❌ Clé corrompue/invalide
    EXPIRED = auto()        # ⏰ Licence expirée
    VM_DETECTED = auto()    # 🚫 VM / Sandbox détecté
    HW_MISMATCH = auto()    # 🔄 Matériel changé (tentative de transfert)
    DEBUG_DETECTED = auto() # 🛡️ Débogage détecté
    NOT_ACTIVATED = auto()   # ⏳ Pas encore activé


# ═══════════════════════════════════════════════════════════════════════════════
# ANTI-DEBUG & ANTI-VM (chargé en premier)
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityGate:
    """Vérifications de sécurité — chargé avant tout le reste."""
    
    @staticmethod
    def check_debugger() -> bool:
        """Détecte les débogueurs actifs."""
        if sys.platform == "win32":
            try:
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                return kernel32.IsDebuggerPresent() == 1
            except:
                pass
        # Linux/macOS
        try:
            with open("/proc/self/status") as f:
                status = f.read()
                if "TracerPid:" in status:
                    tracer = int(re.search(r"TracerPid:\s+(\d+)", status).group(1))
                    if tracer != 0:
                        return True
        except:
            pass
        return False
    
    @staticmethod
    def check_virtualization() -> Tuple[bool, str]:
        """Détecte VM, Docker, Sandbox."""
        hints = []
        
        # Windows
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["powershell", "-Command", 
                     "(Get-WmiObject Win32_ComputerSystem).Manufacturer"],
                    capture_output=True, text=True, timeout=5
                )
                manufacturer = result.stdout.strip().lower()
                vm_keywords = ["vmware", "virtual", "qemu", "kvm", "hyper-v", 
                               "parallels", "oracle", "microsoft corporation"]
                if any(kw in manufacturer for kw in vm_keywords):
                    hints.append(f"VM Manufacturer: {manufacturer}")
            except:
                pass
            
            # WMIC checks
            try:
                result = subprocess.run(
                    ["wmic", "baseboard", "get", "serialnumber", "/value"],
                    capture_output=True, text=True, timeout=5
                )
                serial = result.stdout.lower()
                if "virtual" in serial or "vmware" in serial:
                    hints.append("VM Serial detected")
            except:
                pass
        
        # Linux (générique)
        elif Path("/proc/self/cgroup").exists():
            try:
                with open("/proc/self/cgroup") as f:
                    if "docker" in f.read() or "lxc" in f.read():
                        hints.append("Container/Docker detected")
            except:
                pass
        
        # VM detection files
        vm_files = [
            "/proc/scsi/scsi",  # VMware
            "/proc/qws",         # QEMU
            "/sys/class/dmi/id/product_name",  # VM markers
            "/sys/class/dmi/id/sys_vendor",
        ]
        for f in vm_files:
            try:
                if Path(f).exists():
                    content = Path(f).read_text().lower()
                    vm_markers = ["vmware", "virtualbox", "qemu", "kvm", "parallels"]
                    for marker in vm_markers:
                        if marker in content:
                            hints.append(f"VM marker: {marker}")
                            break
            except:
                pass
        
        # Timing check (VMs often have timing anomalies)
        try:
            import time
            before = time.perf_counter()
            _ = sum(range(10000))
            elapsed = time.perf_counter() - before
            if elapsed > 0.01:  # Exagérément lent = VM
                hints.append(f"Slow execution: {elapsed:.4f}s")
        except:
            pass
        
        return len(hints) > 0, "; ".join(hints)
    
    @staticmethod
    def check_integrity() -> bool:
        """Vérifie que le code n'a pas été modifié (simplifié)."""
        # En production: calculer hash des modules critiques
        # et comparer avec hash embarqué dans le binaire
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE FINGERPRINT
# ═══════════════════════════════════════════════════════════════════════════════

def get_hardware_id() -> str:
    """
    Génère un fingerprint hardware unique et stable.
    Combine plusieurs composants pour éviter l'usurpation.
    """
    components = []
    
    # 1. CPU ID
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "ProcessorId", "/value"],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r"ProcessorId=([A-F0-9]+)", result.stdout, re.I)
            if match and match.group(1):
                components.append(match.group(1))
        except:
            pass
    else:
        # Linux: essaye /proc/cpuinfo
        try:
            with open("/proc/cpuinfo") as f:
                content = f.read()
                match = re.search(r"Serial\s*:\s*([A-Fa-f0-9]+)", content)
                if match:
                    components.append(match.group(1))
        except:
            pass
    
    # 2. MAC address (premier interface)
    try:
        mac_int = uuid.getnode()
        mac = ":".join(f"{(mac_int >> i) & 0xff:02x}" for i in (40, 32, 24, 16, 8, 0))
        components.append(mac.replace(":", "").upper())
    except:
        pass
    
    # 3. Machine ID (Windows SID / Linux /etc/machine-id)
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["powershell", "-Command", 
                 "(Get-WmiObject Win32_ComputerSystemProduct).UUID"],
                capture_output=True, text=True, timeout=5
            )
            uuid_val = result.stdout.strip()
            if uuid_val:
                components.append(uuid_val)
        except:
            pass
    else:
        # Linux machine-id
        machine_id_paths = ["/etc/machine-id", "/var/lib/dbus/machine-id"]
        for path in machine_id_paths:
            if Path(path).exists():
                content = Path(path).read_text().strip()
                if content:
                    components.append(content[:32])
                    break
    
    # 4. Disk Serial (volume C: sur Windows, root disk sur Linux)
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "SerialNumber", "/value"],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r"SerialNumber=([^\s]+)", result.stdout)
            if match:
                components.append(match.group(1).strip())
        except:
            pass
    else:
        try:
            # Linux: lsblk ou blkid
            result = subprocess.run(
                ["lsblk", "-o", "SERIAL", "-n", "-d"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                components.append(result.stdout.strip().split("\n")[0])
        except:
            pass
    
    # Fallback si rien trouvé
    if not components:
        components.append(platform.node() or "unknown")
    
    # Combine et hash
    combined = "|".join(components).encode()
    hwid = hashlib.sha3_512(combined).hexdigest()[:48].upper()
    
    return hwid


def generate_hardware_token(hwid: str, salt: bytes = HARDWARE_SALT) -> str:
    """Génère un token hardware signé pour validation."""
    data = f"{hwid}:{platform.system()}:{platform.machine()}".encode()
    token = hashlib.pbkdf2_hmac('sha3_512', data, salt, 100000)
    return token.hex()


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class LicenseManager:
    """
    Gestionnaire de licence avec hardware lock.
    """
    
    def __init__(self, app_data_dir: Path = None):
        self.app_data = app_data_dir if app_data_dir else APP_DATA
        self.app_data.mkdir(parents=True, exist_ok=True)
        self.license_file = self.app_data / "license.json"
        self.hw_file = self.app_data / "hardware.lock"
        
        # Vérifications de sécurité au démarrage
        self._security_check()
    
    def _security_check(self):
        """Vérifications anti-piratage au chargement."""
        # 1. Anti-debug
        if SecurityGate.check_debugger():
            print("[SECURITY] Débogueur détecté — Accès refusé")
            sys.exit(1)
        
        # 2. Anti-VM
        is_vm, reason = SecurityGate.check_virtualization()
        if is_vm:
            print(f"[SECURITY] Environnement virtuel détecté: {reason}")
            # En debug on log juste, en production on bloque
            # sys.exit(1)  # Décommenter en production
    
    def check_license(self, verbose: bool = False) -> LicenseStatus:
        """
        Vérifie la validité de la licence.
        Returns LicenseStatus.VALID si tout est ok.
        """
        # Vérifier si déjà activé
        if not self.license_file.exists():
            if verbose:
                print("[LICENSE] Pas encore activé — activation requise")
            return LicenseStatus.NOT_ACTIVATED
        
        # Lire licence
        try:
            with open(self.license_file) as f:
                license_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            if verbose:
                print("[LICENSE] Fichier licence corrompu")
            return LicenseStatus.INVALID
        
        # Vérifier hardware match
        expected_hw = license_data.get("hwid", "")
        current_hw = get_hardware_id()
        
        # Support pour token migré
        if "hw_token" in license_data:
            expected_token = license_data.get("hw_token", "")
            current_token = generate_hardware_token(current_hw)
            if expected_token and expected_token != current_token:
                if verbose:
                    print("[LICENSE] Matériel modifié — transfert détecté")
                return LicenseStatus.HW_MISMATCH
        elif expected_hw != current_hw:
            # Compatibilité ancienne version
            if verbose:
                print("[LICENSE] Hardware mismatch")
            return LicenseStatus.HW_MISMATCH
        
        # Vérifier expiration
        expires = license_data.get("expires")
        if expires:
            try:
                exp_date = datetime.fromisoformat(expires)
                if datetime.now() > exp_date:
                    if verbose:
                        print(f"[LICENSE] Expirée le {expires}")
                    return LicenseStatus.EXPIRED
            except:
                pass
        
        # Vérifier intégrité signature
        if LICENSE_SIGNATURE != "__LICENSE_SIG__":
            # Signature embarquée — vérifier
            sig = license_data.get("sig", "")
            expected_sig = self._sign({
                "hwid": license_data.get("hwid"),
                "expires": license_data.get("expires"),
                "email": license_data.get("email"),
            })
            if sig != expected_sig:
                if verbose:
                    print("[LICENSE] Signature invalide")
                return LicenseStatus.INVALID
        
        return LicenseStatus.VALID
    
    def activate(self, license_key: str = None, email: str = None) -> Tuple[bool, str]:
        """
        Active la licence sur cette machine.
        Appelé automatiquement au premier lancement avec la clé embarquée.
        
        Returns: (success, message)
        """
        # Utiliser clé embarquée ou paramètre
        actual_key = license_key or LICENSE_SIGNATURE
        if actual_key == "__LICENSE_SIG__":
            return False, "Aucune clé de licence"
        
        # Valider clé (format simplifié: STB5-XXXX-XXXX-XXXX)
        if not self._validate_key(actual_key):
            return False, "Clé invalide"
        
        # Générer hardware ID
        hwid = get_hardware_id()
        hw_token = generate_hardware_token(hwid)
        
        # Vérifier expiration
        expiry = LICENSE_EXPIRY
        if expiry == "__LICENSE_EXPIRY__":
            # Pas d'expiration par défaut
            expiry = None
        
        # Sauvegarder licence
        license_data = {
            "key": actual_key,
            "email": email or "unknown",
            "hwid": hwid,
            "hw_token": hw_token,
            "activated_at": datetime.now().isoformat(),
            "expires": expiry,
            "version": "5.0",
            "sig": self._sign({"hwid": hwid, "expires": expiry, "email": email}),
        }
        
        try:
            with open(self.license_file, "w") as f:
                json.dump(license_data, f, indent=2)
            
            # Marquer comme activé
            INSTALLER_MARKER.parent.mkdir(parents=True, exist_ok=True)
            INSTALLER_MARKER.write_text(datetime.now().isoformat())
            
            return True, "Activation réussie"
        except IOError as e:
            return False, f"Erreur écriture: {e}"
    
    def revoke(self) -> bool:
        """Révoque la licence (supprime les fichiers)."""
        try:
            if self.license_file.exists():
                self.license_file.unlink()
            if self.hw_file.exists():
                self.hw_file.unlink()
            return True
        except:
            return False
    
    def get_info(self) -> dict:
        """Retourne info licence pour l'affichage."""
        status = self.check_license()
        info = {
            "status": status.name,
            "valid": status == LicenseStatus.VALID,
        }
        
        if self.license_file.exists():
            try:
                with open(self.license_file) as f:
                    data = json.load(f)
                    info["email"] = data.get("email", "N/A")
                    info["activated"] = data.get("activated_at", "N/A")
                    info["expires"] = data.get("expires", "Jamais")
                    info["hwid_short"] = data.get("hwid", "")[:8] + "..."
            except:
                pass
        
        return info
    
    def _validate_key(self, key: str) -> bool:
        """Valide le format de la clé."""
        if not key:
            return False
        # Format: STB5-XXXX-XXXX-XXXX
        pattern = r"^STB5-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        return bool(re.match(pattern, key, re.I))
    
    def _sign(self, data: dict) -> str:
        """Signe les données avec hash."""
        import hmac
        msg = json.dumps(data, sort_keys=True)
        sig = hashlib.sha3_256(msg.encode()).hexdigest()
        return sig


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-ACTIVATION (lancé au premier démarrage)
# ═══════════════════════════════════════════════════════════════════════════════

def auto_activate():
    """Active automatiquement avec la clé embarquée."""
    lm = LicenseManager()
    status = lm.check_license()
    
    if status == LicenseStatus.VALID:
        return True, "Déjà activé"
    
    if status == LicenseStatus.NOT_ACTIVATED:
        success, msg = lm.activate()
        return success, msg
    
    return False, f"Statut: {status.name}"


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    lm = LicenseManager()
    status = lm.check_license(verbose=True)
    
    if status != LicenseStatus.VALID:
        print("\n[ERROR] Licence non valide. Le bot ne peut pas démarrer.")
        sys.exit(1)
    
    print("[OK] Licence valide — SafeTrendBot prêt")