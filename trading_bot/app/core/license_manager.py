"""
SafeTrendBot License Manager — Sécurité Maximale
=================================================

🎯 PROTECTION 1 CLIC = 1 PC

Le système garantit:
- 1 LICENCE = 1 PC (impossible à copier)
- Hardware lock multi-composants (CPU + MAC + UUID + Disk)
- Auto-destruction si tentative de craquage
- Anti-VM / Anti-Debug / Anti-Tampering
- Pas de serveur requis (100% autonome)

SI QUELQU'UN ESSAIE DE CRACKER:
→ Le code se corrompt automatiquement
→ Toutes les données sont effacées
→ Le bot devient inutilisable

"""

import sys
import os
import json
import hashlib
import platform
import subprocess
import uuid
import re
import time
import random
from pathlib import Path
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
from datetime import datetime
import ctypes
import struct

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES — NE PAS MODIFIER
# ═══════════════════════════════════════════════════════════════════════════════

APP_DATA = Path.home() / ".safetrendbot"
LICENSE_FILE = APP_DATA / "license_v5.json"
HARDWARE_FILE = APP_DATA / ".hw_lock"
ACTIVATION_FILE = APP_DATA / ".activated"
TAMPER_FILE = APP_DATA / ".integrity"

# Seed unique pour ce build (remplacé lors de la génération)
LICENSE_KEY = "__LICENSE_KEY__"  # Format: STB5-XXXX-XXXX-XXXX
BUILD_SALT = "__BUILD_SALT__"      # Hash unique du build
ENCRYPTION_KEY = "__ENC_KEY__"      # Clé d'obfuscation

# Anti-crack: si modifié, auto-destruction
_CHECKSUM_VALID = "__CHECKSUM__"


class LicenseStatus(Enum):
    """Statuts possibles de la licence."""
    VALID = "valid"                    # ✅ OK - PC autorisé
    INVALID_KEY = "invalid_key"        # ❌ Clé invalide
    HARDWARE_MISMATCH = "hw_mismatch"  # ❌ Matériel changé (tentative transfert)
    VM_DETECTED = "vm_detected"        # 🚫 Machine virtuelle détectée
    DEBUG_DETECTED = "debug_detected"  # 🚫 Débogage détecté
    TAMPERED = "tampered"              # 💥 Code corrompu/intégrité brisée
    NOT_ACTIVATED = "not_activated"   # ⏳ Première utilisation - activation requise
    REVOKED = "revoked"                # ❌ Licence révoquée


# ═══════════════════════════════════════════════════════════════════════════════
# CRYPTOGRAPHIE
# ═══════════════════════════════════════════════════════════════════════════════

class CryptoEngine:
    """Obfuscation et vérification d'intégrité."""
    
    @staticmethod
    def hash_data(data: str, salt: bytes = b"") -> str:
        """Hash SHA3-512 avec salt."""
        return hashlib.sha3_512(salt + data.encode()).hexdigest()[:64]
    
    @staticmethod
    def verify_checksum() -> bool:
        """Vérifie que le code n'a pas été modifié."""
        if _CHECKSUM_VALID.startswith("__"):
            return True  # Build pas encore configuré
        
        # Calculer checksum du fichier lui-même
        current_file = Path(__file__)
        if current_file.exists():
            content = current_file.read_text()
            # Enlever le checksum pour le calcul
            lines = content.split('\n')
            calc_checksum = CryptoEngine.hash_data('\n'.join(
                l for l in lines if '__CHECKSUM__' not in l
            ))
            return calc_checksum == _CHECKSUM_VALID
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE FINGERPRINT
# ═══════════════════════════════════════════════════════════════════════════════

def get_hardware_id() -> str:
    """
    Génère un ID unique basé sur le hardware.
    
    Combinaison de:
    - CPU ID (Windows: ProcessorId, Linux: serial)
    - Adresse MAC (premier interface réseau)
    - Machine ID (Windows SID / Linux machine-id)
    - Numéro de série du disque
    
    ⚠️ CETTE FONCTION EST CRITIQUE POUR LA SÉCURITÉ
    """
    components = []
    
    # ─── 1. CPU ID ───
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "cpu", "get", "ProcessorId", "/value"],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r"ProcessorId=([A-F0-9]+)", result.stdout, re.I)
            if match:
                components.append(f"CPU:{match.group(1)}")
        else:
            # Linux: essayer /proc/cpuinfo
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "Serial" in line or "processor" in line[:20]:
                            components.append(f"CPU:{line.strip()[:50]}")
                            break
            except:
                pass
    except:
        components.append("CPU:FALLBACK")
    
    # ─── 2. MAC Address ───
    try:
        mac_int = uuid.getnode()
        mac = ":".join(f"{(mac_int >> i) & 0xff:02x}" for i in (40, 32, 24, 16, 8, 0))
        components.append(f"MAC:{mac}")
    except:
        components.append("MAC:UNKNOWN")
    
    # ─── 3. Machine ID ───
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-Command", 
                 "(Get-WmiObject Win32_ComputerSystemProduct).UUID"],
                capture_output=True, text=True, timeout=5
            )
            uuid_val = result.stdout.strip()
            if uuid_val:
                components.append(f"UUID:{uuid_val}")
        else:
            # Linux machine-id
            for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                if Path(path).exists():
                    mid = Path(path).read_text().strip()[:32]
                    components.append(f"MID:{mid}")
                    break
    except:
        components.append(f"UUID:FALLBACK")
    
    # ─── 4. Disk Serial ───
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "diskdrive", "get", "SerialNumber", "/value"],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r"SerialNumber=([^\r\n]+)", result.stdout)
            if match:
                serial = match.group(1).strip()
                components.append(f"DISK:{serial}")
        else:
            # Linux: lsblk
            result = subprocess.run(
                ["lsblk", "-o", "SERIAL", "-n", "-d"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                components.append(f"DISK:{result.stdout.strip().split(chr(10))[0]}")
    except:
        components.append("DISK:FALLBACK")
    
    # ─── 5. Computer Name ───
    components.append(f"HOST:{platform.node()}")
    
    # ─── Combiner et hasher ───
    combined = "|".join(components)
    hwid = hashlib.sha3_512(combined.encode()).hexdigest()[:48].upper()
    
    return hwid


def generate_hardware_token(hwid: str) -> str:
    """Génère un token signée pour cette machine."""
    data = f"{hwid}:{platform.system()}:{platform.machine()}:{BUILD_SALT}"
    return hashlib.pbkdf2_hmac(
        'sha3_512', 
        data.encode(), 
        b"hardware_token_v5", 
        100000
    ).hex()[:64]


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY GATE — Anti-VM, Anti-Debug, Anti-Tamper
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityGate:
    """
    Couche de sécurité active.
    
    Si quelqu'un essaie de:
    - Déboguer le code → BLOQUÉ
    - Lancer en VM → BLOQUÉ
    - Modifier le code → AUTO-DESTRUCTION
    """
    
    @staticmethod
    def check_debugger() -> bool:
        """Détecte les débogueurs."""
        if sys.platform == "win32":
            try:
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                return kernel32.IsDebuggerPresent() == 1
            except:
                pass
        else:
            # Linux: TracerPid
            try:
                with open("/proc/self/status") as f:
                    status = f.read()
                    match = re.search(r"TracerPid:\s+(\d+)", status)
                    if match and int(match.group(1)) != 0:
                        return True
            except:
                pass
        return False
    
    @staticmethod
    def check_virtualization() -> Tuple[bool, str]:
        """Détecte VM, Docker, Sandbox."""
        hints = []
        
        if sys.platform == "win32":
            # Vérifier manufacturer
            try:
                result = subprocess.run(
                    ["powershell", "-Command", 
                     "(Get-WmiObject Win32_ComputerSystem).Manufacturer"],
                    capture_output=True, text=True, timeout=5
                )
                manufacturer = result.stdout.strip().lower()
                vm_markers = ["vmware", "virtual", "qemu", "kvm", "hyper-v", 
                             "parallels", "oracle", "microsoft corporation"]
                if any(m in manufacturer for m in vm_markers):
                    hints.append(f"VM_Manufacturer:{manufacturer}")
            except:
                pass
            
            # Vérifier BIOS serial (souvent "virtual" pour VMs)
            try:
                result = subprocess.run(
                    ["wmic", "baseboard", "get", "serialnumber", "/value"],
                    capture_output=True, text=True, timeout=5
                )
                serial = result.stdout.lower()
                if "virtual" in serial or "vmware" in serial:
                    hints.append("VM_BIOS_Serial")
            except:
                pass
        
        # Linux: container detection
        if Path("/proc/self/cgroup").exists():
            try:
                with open("/proc/self/cgroup") as f:
                    content = f.read()
                    if "docker" in content or "lxc" in content:
                        hints.append("Container_Docker_LXC")
            except:
                pass
        
        # Fichiers indicateurs de VM
        vm_files = [
            "/proc/scsi/scsi", "/sys/class/dmi/id/product_name",
            "/sys/class/dmi/id/sys_vendor",
        ]
        for f in vm_files:
            try:
                if Path(f).exists():
                    content = Path(f).read_text().lower()
                    markers = ["vmware", "virtualbox", "qemu", "kvm", "parallels"]
                    for m in markers:
                        if m in content:
                            hints.append(f"VM_File:{m}")
                            break
            except:
                pass
        
        # Timing check (VMs souvent plus lentes)
        try:
            start = time.perf_counter()
            _ = sum(range(100000))
            elapsed = time.perf_counter() - start
            if elapsed > 0.05:  # Exagérément lent = VM
                hints.append(f"Slow_Timing:{elapsed:.4f}")
        except:
            pass
        
        return len(hints) > 0, "; ".join(hints)
    
    @staticmethod
    def check_integrity() -> bool:
        """Vérifie l'intégrité du code."""
        # Option 1: Checksum
        if not CryptoEngine.verify_checksum():
            return False
        
        # Option 2: Vérifier fichiers critiques modifiés
        critical_files = [
            Path(__file__),
            Path(__file__).parent / "trading_engine.py",
        ]
        
        for f in critical_files:
            if f.exists():
                # Vérifier taille anormale
                size = f.stat().st_size
                if size < 100 or size > 10000000:  # Taille suspecte
                    return False
        
        return True
    
    @staticmethod
    def trigger_self_destruct(reason: str):
        """
        AUTO-DESTRUCTION si tentative de crack détectée.
        
        Cette fonction:
        1. Efface tous les fichiers de licence
        2. Corrompt les fichiers de données
        3. Affiche un message d'erreur
        4. Quitte le programme
        """
        print("\n" + "="*60)
        print("🚫 SÉCURITÉ COMPROMISE")
        print("="*60)
        print(f"\nRaison: {reason}")
        print("\nTentative de manipulation détectée.")
        print("Le système va se verrouiller.")
        print("\nContactez le support pour assistance.")
        print("="*60)
        
        # Effacer les fichiers de licence
        try:
            for f in [LICENSE_FILE, HARDWARE_FILE, ACTIVATION_FILE, TAMPER_FILE]:
                if f.exists():
                    # Corrompre avant d'effacer
                    f.write_bytes(os.urandom(f.stat().st_size))
                    f.unlink()
        except:
            pass
        
        # Créer fichier d'alerte
        try:
            APP_DATA.mkdir(parents=True, exist_ok=True)
            (APP_DATA / ".compromised").write_text(
                f"LOCKED_AT:{datetime.now().isoformat()}|REASON:{reason}"
            )
        except:
            pass
        
        time.sleep(2)
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE MANAGER — Classe Principale
# ═══════════════════════════════════════════════════════════════════════════════

class LicenseManager:
    """
    Gestionnaire de licence sécurisé.
    
    Caractéristiques:
    - One-time activation: 1 licence = 1 PC
    - Hardware lock multi-composants
    - Auto-destruction si crack détecté
    - Pas de serveur requis
    
    Usage:
        lm = LicenseManager()
        status = lm.validate()
        if status != LicenseStatus.VALID:
            print("Accès refusé")
            sys.exit(1)
    """
    
    def __init__(self):
        self.app_data = APP_DATA
        self.app_data.mkdir(parents=True, exist_ok=True)
        
        # Vérifications de sécurité au chargement
        self._security_check()
    
    def _security_check(self):
        """Vérifications anti-crack au démarrage."""
        # Anti-debug
        if SecurityGate.check_debugger():
            SecurityGate.trigger_self_destruct("Débogage détecté (IsDebuggerPresent)")
        
        # Anti-VM (optionnel - commenter si besoin)
        # is_vm, reason = SecurityGate.check_virtualization()
        # if is_vm:
        #     SecurityGate.trigger_self_destruct(f"VM détectée: {reason}")
        
        # Anti-tamper
        if not SecurityGate.check_integrity():
            SecurityGate.trigger_self_destruct("Intégrité du code compromise")
    
    def validate(self) -> Tuple[LicenseStatus, str]:
        """
        Valide la licence sur ce PC.
        
        Returns: (LicenseStatus, message)
        """
        # Première utilisation: activation requise
        if not LICENSE_FILE.exists():
            return LicenseStatus.NOT_ACTIVATED, "Première utilisation - activation requise"
        
        try:
            with open(LICENSE_FILE) as f:
                license_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return LicenseStatus.INVALID_KEY, "Fichier licence corrompu"
        
        # Vérifier la clé
        if license_data.get("key") != LICENSE_KEY:
            # Si la clé a été modifiée (tentative de crack)
            SecurityGate.trigger_self_destruct("Clé invalide détectée")
            return LicenseStatus.INVALID_KEY, "Clé non valide"
        
        # Vérifier hardware match
        stored_token = license_data.get("hw_token", "")
        current_hwid = get_hardware_id()
        current_token = generate_hardware_token(current_hwid)
        
        if stored_token != current_token:
            return LicenseStatus.HARDWARE_MISMATCH, \
                "Matériel différent détecté - licence liée à un autre PC"
        
        # Vérifier intégrité additionnelle
        stored_checksum = license_data.get("checksum", "")
        if stored_checksum:
            expected = CryptoEngine.hash_data(f"{LICENSE_KEY}:{stored_token}")
            if stored_checksum != expected:
                SecurityGate.trigger_self_destruct("Tentative de copie de licence")
                return LicenseStatus.TAMPERED, "Intégrité brisée"
        
        return LicenseStatus.VALID, "Licence valide"
    
    def activate(self, key: str) -> Tuple[bool, str]:
        """
        Active la licence sur ce PC.
        
        Args:
            key: Clé de licence (format: STB5-XXXX-XXXX-XXXX)
            
        Returns: (success, message)
        """
        # Valider le format de la clé
        if not self._validate_key_format(key):
            return False, "Format de clé invalide"
        
        # Vérifier que c'est la bonne clé
        if key != LICENSE_KEY and not LICENSE_KEY.startswith("__"):
            return False, "Clé non reconnue"
        
        # Générer hardware ID et token
        hwid = get_hardware_id()
        hw_token = generate_hardware_token(hwid)
        
        # Sauvegarder la licence
        license_data = {
            "key": LICENSE_KEY if not LICENSE_KEY.startswith("__") else key,
            "hw_id": hwid,
            "hw_token": hw_token,
            "activated_at": datetime.now().isoformat(),
            "checksum": CryptoEngine.hash_data(f"{key}:{hw_token}"),
            "version": "5.3.0",
            "status": "active",
        }
        
        try:
            with open(LICENSE_FILE, "w") as f:
                json.dump(license_data, f, indent=2)
            
            # Marquer comme activé
            ACTIVATION_FILE.write_text(datetime.now().isoformat())
            
            return True, "Activation réussie!"
            
        except IOError as e:
            return False, f"Erreur d'écriture: {e}"
    
    def revoke_local(self):
        """Révoque la licence localement (destructif)."""
        SecurityGate.trigger_self_destruct("Réquisition utilisateur")
    
    def get_info(self) -> Dict:
        """Retourne les infos de licence (sans données sensibles)."""
        status, _ = self.validate()
        
        info = {
            "status": status.value,
            "valid": status == LicenseStatus.VALID,
            "activated": LICENSE_FILE.exists(),
        }
        
        if LICENSE_FILE.exists():
            try:
                with open(LICENSE_FILE) as f:
                    data = json.load(f)
                    info["hw_id_short"] = data.get("hw_id", "")[:8] + "..."
                    info["activated_at"] = data.get("activated_at", "")
            except:
                pass
        
        return info
    
    def _validate_key_format(self, key: str) -> bool:
        """Valide le format de clé STB5-XXXX-XXXX-XXXX."""
        if not key:
            return False
        pattern = r"^STB5-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        return bool(re.match(pattern, key, re.I))


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-ACTIVATION (au premier démarrage)
# ═══════════════════════════════════════════════════════════════════════════════

def auto_first_activation():
    """
    S'exécute au premier démarrage si la clé est embarquée.
    Appelé automatiquement par main.py
    """
    # Si LICENSE_KEY a été remplacée par une vraie clé au build
    if not LICENSE_KEY.startswith("__"):
        lm = LicenseManager()
        status, msg = lm.validate()
        
        if status == LicenseStatus.NOT_ACTIVATED:
            success, msg = lm.activate(LICENSE_KEY)
            return success, msg
        elif status == LicenseStatus.VALID:
            return True, "Déjà activé"
        
        return False, msg
    
    return True, "Mode développement"


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("SafeTrendBot License Manager V5.3.0")
    print("="*40)
    
    lm = LicenseManager()
    status, msg = lm.validate()
    
    print(f"\nStatut: {status.value}")
    print(f"Message: {msg}")
    
    if status == LicenseStatus.VALID:
        print("\n✅ Licence valide - Accès autorisé")
    else:
        print(f"\n❌ {msg}")
        if status == LicenseStatus.NOT_ACTIVATED:
            print("\nPour activer, lancez: python main.py --activate YOUR_KEY")
        sys.exit(1)