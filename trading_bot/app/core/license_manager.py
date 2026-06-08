"""
SafeTrendBot License Manager — Système de protection commerciale.
Génère, valide et protège les licences utilisateur.
"""
import hashlib
import hmac
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
import platform
import uuid
import subprocess


class LicenseManager:
    """
    Gestionnaire de licences locales.
    Chaque licence est liée à un hardware fingerprint unique.
    """

    def __init__(self, secret_key: str, license_file: Optional[Path] = None):
        self.secret = secret_key.encode()
        self.license_file = license_file or Path.home() / ".safetrendbot" / "license.key"
        self.license_file.parent.mkdir(parents=True, exist_ok=True)
        self._cached_license: Optional[Dict] = None
        self._last_check: Optional[datetime] = None

    # ========================================================================
    # HARDWARE FINGERPRINT
    # ========================================================================

    @staticmethod
    def get_hardware_fingerprint() -> str:
        """
        Génère un fingerprint unique basé sur le matériel.
        Combine: MAC, CPU, disque, hostname.
        """
        components = []

        # MAC address
        try:
            mac = uuid.getnode()
            components.append(f"mac:{mac:012x}")
        except Exception:
            pass

        # Hostname
        components.append(f"host:{platform.node()}")

        # Machine / processor
        components.append(f"machine:{platform.machine()}")
        components.append(f"proc:{platform.processor()}")

        # Windows: WMI pour plus de détails
        if platform.system() == "Windows":
            try:
                import wmi
                c = wmi.WMI()
                for cpu in c.Win32_Processor():
                    components.append(f"cpu_id:{cpu.ProcessorId}")
                for disk in c.Win32_DiskDrive():
                    components.append(f"disk_sn:{disk.SerialNumber}")
                for board in c.Win32_BaseBoard():
                    components.append(f"board_sn:{board.SerialNumber}")
            except Exception:
                pass
        elif platform.system() == "Linux":
            try:
                # CPU serial
                with open('/proc/cpuinfo') as f:
                    for line in f:
                        if 'Serial' in line:
                            components.append(line.strip())
                            break
                # Machine ID
                machine_id = Path('/etc/machine-id').read_text().strip()
                components.append(f"machine_id:{machine_id}")
            except Exception:
                pass
        elif platform.system() == "Darwin":
            try:
                result = subprocess.run(['ioreg', '-l'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'IOPlatformSerialNumber' in line:
                        sn = line.split('"')[-2] if '"' in line else 'unknown'
                        components.append(f"mac_sn:{sn}")
                        break
            except Exception:
                pass

        raw = '|'.join(sorted(components))
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    # ========================================================================
    # LICENCE GENERATION (appelé par le serveur de vente)
    # ========================================================================

    def generate_license(self, customer_email: str, license_type: str = "lifetime",
                         expires_days: Optional[int] = None,
                         max_machines: int = 1) -> str:
        """
        Génère une clé de licence signée.
        À utiliser côté serveur de vente uniquement.
        """
        hw_id = self.get_hardware_fingerprint()
        now = datetime.utcnow()
        expiry = None
        if expires_days:
            expiry = (now + timedelta(days=expires_days)).isoformat()

        payload = {
            "email": customer_email,
            "type": license_type,
            "hw_id": hw_id,
            "issued": now.isoformat(),
            "expires": expiry,
            "max_machines": max_machines,
            "version": "5.0",
        }

        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(self.secret, payload_json.encode(), hashlib.sha256).hexdigest()[:32]

        license_data = {
            "payload": payload,
            "sig": signature,
        }

        # Encode en base64 pour faciliter le copier-coller
        license_str = base64.urlsafe_b64encode(
            json.dumps(license_data).encode()
        ).decode().rstrip('=')

        return license_str

    # ========================================================================
    # LICENCE VALIDATION (côté client)
    # ========================================================================

    def validate_license(self, license_str: Optional[str] = None) -> Tuple[bool, str]:
        """
        Valide une licence.
        Retourne (is_valid, message).
        """
        if license_str is None:
            # Charger depuis fichier
            if not self.license_file.exists():
                return False, "Aucune licence trouvée. Achetez une licence sur safetrendbot.com"
            try:
                license_str = self.license_file.read_text().strip()
            except Exception:
                return False, "Fichier licence corrompu"

        try:
            # Ajouter padding si nécessaire
            padding = 4 - len(license_str) % 4
            if padding != 4:
                license_str += '=' * padding

            decoded = base64.urlsafe_b64decode(license_str)
            license_data = json.loads(decoded)
        except Exception:
            return False, "Format de licence invalide"

        payload = license_data.get("payload", {})
        signature = license_data.get("sig", "")

        # Vérifier la signature
        payload_json = json.dumps(payload, sort_keys=True)
        expected_sig = hmac.new(self.secret, payload_json.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(signature, expected_sig):
            return False, "Licence frauduleuse détectée (signature invalide)"

        # Vérifier le hardware fingerprint
        current_hw = self.get_hardware_fingerprint()
        if payload.get("hw_id") != current_hw:
            return False, f"Licence non valide sur cette machine. HW ID: {current_hw[:16]}..."

        # Vérifier l'expiration
        expiry = payload.get("expires")
        if expiry:
            expiry_dt = datetime.fromisoformat(expiry)
            if datetime.utcnow() > expiry_dt:
                return False, f"Licence expirée le {expiry}"

        # Vérifier la version
        if payload.get("version", "5.0") != "5.0":
            return False, "Licence incompatible avec cette version"

        self._cached_license = payload
        return True, f"Licence valide — {payload.get('email')} ({payload.get('type')})"

    def save_license(self, license_str: str) -> bool:
        """Sauvegarde la licence dans le fichier local"""
        try:
            self.license_file.write_text(license_str)
            return True
        except Exception:
            return False

    def get_license_info(self) -> Optional[Dict]:
        """Retourne les infos de la licence courante"""
        return self._cached_license

    def is_validated(self) -> bool:
        """Vrai si une licence valide est en cache"""
        return self._cached_license is not None

    # ========================================================================
    # ONLINE ACTIVATION
    # ========================================================================

    def activate_online(self, license_key: str, activation_server: str) -> Tuple[bool, str]:
        """
        Active la licence en ligne auprès du serveur.
        Retourne (success, message).
        """
        import requests
        try:
            hw_id = self.get_hardware_fingerprint()
            response = requests.post(
                f"{activation_server}/api/activate",
                json={
                    "license_key": license_key,
                    "hw_id": hw_id,
                    "machine": platform.node(),
                    "os": platform.system(),
                },
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Sauvegarder la licence signée retournée
                    signed_license = data.get("signed_license")
                    if signed_license:
                        self.save_license(signed_license)
                        return True, f"Activation réussie — {data.get('message', '')}"
                return False, data.get("message", "Activation refusée")
            elif response.status_code == 429:
                return False, "Trop de tentatives d'activation — réessayez dans 1h"
            else:
                return False, f"Erreur serveur ({response.status_code})"
        except requests.exceptions.ConnectionError:
            return False, "Impossible de contacter le serveur d'activation — vérifiez votre connexion"
        except Exception as e:
            return False, f"Erreur activation: {e}"

    def heartbeat(self, activation_server: str) -> Tuple[bool, str]:
        """
        Ping régulier au serveur pour vérifier que la licence est toujours valide.
        Retourne (is_valid, message).
        """
        if self._last_check and (datetime.utcnow() - self._last_check).seconds < 3600:
            return True, "Cache valide"

        import requests
        try:
            license_str = self.license_file.read_text().strip() if self.license_file.exists() else ""
            response = requests.post(
                f"{activation_server}/api/heartbeat",
                json={"license_hash": hashlib.sha256(license_str.encode()).hexdigest()[:16]},
                timeout=5,
            )
            self._last_check = datetime.utcnow()
            if response.status_code == 200:
                return True, "Licence confirmée"
            return False, "Licence révoquée ou invalide"
        except Exception:
            # Si offline, accepter le cache pendant 24h
            if self._last_check and (datetime.utcnow() - self._last_check).days < 1:
                return True, "Mode offline — cache accepté"
            return False, "Vérification impossible — connexion requise"

    # ========================================================================
    # TRIAL MODE
    # ========================================================================

    def start_trial(self, days: int = 7) -> str:
        """Génère une licence d'essai limitée"""
        trial_license = self.generate_license(
            customer_email="trial@demo.local",
            license_type="trial",
            expires_days=days,
            max_machines=1,
        )
        self.save_license(trial_license)
        return trial_license

    def is_trial(self) -> bool:
        info = self.get_license_info()
        return info is not None and info.get("type") == "trial"

    def get_trial_remaining_days(self) -> Optional[int]:
        info = self.get_license_info()
        if not info or not info.get("expires"):
            return None
        expiry = datetime.fromisoformat(info["expires"])
        remaining = (expiry - datetime.utcnow()).days
        return max(0, remaining)
