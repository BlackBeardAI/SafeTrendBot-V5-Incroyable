"""
CryptoVault — Chiffrement AES-256-GCM pour SafeTrendBot V5
=============================================================

Chiffre tous les fichiers sensibles du bot:
- Configuration utilisateur (config.json)
- Fichier de licence (license_v2.json)
- Journal de trading (journal/)
- Données de marché sensibles

Algorithme: AES-256-GCM (chiffrement authentifié)
Dérivation de clé: PBKDF2-HMAC-SHA256 (100k iterations)
Format: salt(16B) + nonce(12B) + ciphertext + tag(16B)

Usage:
    from app.core.encryption import CryptoVault
    vault = CryptoVault("mon_mot_de_passe_fort")
    vault.encrypt_file("config.json")
    vault.decrypt_file("config.json.enc")
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Union, Optional

# Essayer d'importer cryptography, sinon fallback warning
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️  cryptography manquant — pip install cryptography")


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
KEY_LEN = 32  # 256 bits
KDF_ITERATIONS = 100_000

# Fichiers à chiffrer automatiquement
SENSITIVE_PATTERNS = [
    "license_v2.json",
    "config.json",
    "*.key",
    "*.secret",
    "journal/*.json",
    "paper/*.json",
    "journal/*.csv",
]


class CryptoVault:
    """
    Vault de chiffrement AES-256-GCM.
    """

    def __init__(self, password: str, salt: Optional[bytes] = None):
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Install 'cryptography': pip install cryptography")

        self.password = password.encode("utf-8")
        self.salt = salt or secrets.token_bytes(SALT_LEN)
        self._key = self._derive_key(self.password, self.salt)

    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        """Dérive une clé AES-256 à partir du mot de passe."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LEN,
            salt=salt,
            iterations=KDF_ITERATIONS,
        )
        return kdf.derive(password)

    # ─────────────────────────────────────────────────────────────────────────
    # Chiffrement / Déchiffrement bytes
    # ─────────────────────────────────────────────────────────────────────────

    def encrypt(self, plaintext: bytes) -> bytes:
        """Chiffre des bytes, retourne salt+nonce+ciphertext+tag."""
        nonce = secrets.token_bytes(NONCE_LEN)
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # ciphertext contient déjà le tag GCM à la fin
        return self.salt + nonce + ciphertext

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Déchiffre des bytes chiffrés."""
        if len(ciphertext) < SALT_LEN + NONCE_LEN + TAG_LEN:
            raise ValueError("Données chiffrées trop courtes")

        salt = ciphertext[:SALT_LEN]
        nonce = ciphertext[SALT_LEN:SALT_LEN + NONCE_LEN]
        encrypted = ciphertext[SALT_LEN + NONCE_LEN:]

        # Redériver la clé avec le salt trouvé
        key = self._derive_key(self.password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, encrypted, None)

    # ─────────────────────────────────────────────────────────────────────────
    # Chiffrement / Déchiffrement fichiers
    # ─────────────────────────────────────────────────────────────────────────

    def encrypt_file(self, file_path: Union[str, Path], delete_original: bool = True) -> Path:
        """Chiffre un fichier, sauvegarde en .enc"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        plaintext = file_path.read_bytes()
        encrypted = self.encrypt(plaintext)

        enc_path = file_path.with_suffix(file_path.suffix + ".enc")
        enc_path.write_bytes(encrypted)

        if delete_original:
            # Écrasement sécurisé (simple) puis suppression
            self._secure_delete(file_path)

        return enc_path

    def decrypt_file(self, enc_path: Union[str, Path], output_path: Optional[Path] = None) -> Path:
        """Déchiffre un fichier .enc"""
        enc_path = Path(enc_path)
        if not enc_path.exists():
            raise FileNotFoundError(enc_path)

        encrypted = enc_path.read_bytes()
        plaintext = self.decrypt(encrypted)

        if output_path is None:
            # Retirer .enc
            if str(enc_path).endswith(".enc"):
                output_path = Path(str(enc_path)[:-4])
            else:
                output_path = enc_path.with_suffix(".dec")

        output_path.write_bytes(plaintext)
        return output_path

    # ─────────────────────────────────────────────────────────────────────────
    # Batch chiffrement dossier
    # ─────────────────────────────────────────────────────────────────────────

    def encrypt_directory(self, directory: Union[str, Path], patterns: Optional[list] = None) -> list:
        """Chiffre tous les fichiers sensibles d'un dossier."""
        directory = Path(directory)
        patterns = patterns or SENSITIVE_PATTERNS
        encrypted = []

        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file() and not str(file_path).endswith(".enc"):
                    try:
                        enc = self.encrypt_file(file_path)
                        encrypted.append(enc)
                    except Exception as e:
                        print(f"⚠️  Échec chiffrement {file_path}: {e}")

        return encrypted

    def decrypt_directory(self, directory: Union[str, Path]) -> list:
        """Déchiffre tous les fichiers .enc d'un dossier."""
        directory = Path(directory)
        decrypted = []

        for enc_path in directory.rglob("*.enc"):
            try:
                out = self.decrypt_file(enc_path)
                decrypted.append(out)
            except Exception as e:
                print(f"⚠️  Échec déchiffrement {enc_path}: {e}")

        return decrypted

    # ─────────────────────────────────────────────────────────────────────────
    # Utils
    # ─────────────────────────────────────────────────────────────────────────

    def _secure_delete(self, file_path: Path, passes: int = 3):
        """Écrasement simple avant suppression."""
        try:
            size = file_path.stat().st_size
            with open(file_path, "ba+") as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(secrets.token_bytes(size))
                    f.flush()
                    os.fsync(f.fileno())
            file_path.unlink()
        except Exception:
            # Fallback: suppression simple
            file_path.unlink(missing_ok=True)

    @staticmethod
    def generate_password(length: int = 32) -> str:
        """Génère un mot de passe aléatoire fort."""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION BOT
# ─────────────────────────────────────────────────────────────────────────────

def get_vault_password() -> str:
    """
    Récupère le mot de passe du vault.
    Priorité:
    1. Variable d'environnement SAFETRENDBOT_VAULT_PASSWORD
    2. Fichier .vault_key dans le dossier app_data
    3. Génération automatique + sauvegarde
    """
    # 1. Env var
    env_pw = os.environ.get("SAFETRENDBOT_VAULT_PASSWORD")
    if env_pw:
        return env_pw

    # 2. Fichier clé
    key_file = Path.home() / ".safetrendbot" / ".vault_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()

    # 3. Générer et sauvegarder
    password = CryptoVault.generate_password(32)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(password, encoding="utf-8")
    # Limiter les permissions
    os.chmod(key_file, 0o600)

    print(f"🔐 Clé de chiffrement générée et sauvegardée dans {key_file}")
    print(f"   SAUVEGARDEZ CE FICHIER! Sans lui, vos données sont perdues.")

    return password


def encrypt_sensitive_data(data_dir: Optional[Path] = None):
    """Chiffre automatiquement tous les fichiers sensibles."""
    if not CRYPTO_AVAILABLE:
        return

    data_dir = data_dir or Path.home() / ".safetrendbot" / "v5"
    password = get_vault_password()
    vault = CryptoVault(password)

    encrypted = vault.encrypt_directory(data_dir)
    print(f"🔒 {len(encrypted)} fichiers chiffrés")


def decrypt_sensitive_data(data_dir: Optional[Path] = None):
    """Déchiffre tous les fichiers sensibles."""
    if not CRYPTO_AVAILABLE:
        return

    data_dir = data_dir or Path.home() / ".safetrendbot" / "v5"
    password = get_vault_password()
    vault = CryptoVault(password)

    decrypted = vault.decrypt_directory(data_dir)
    print(f"🔓 {len(decrypted)} fichiers déchiffrés")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CryptoVault SafeTrendBot")
    parser.add_argument("--encrypt", help="Chiffrer un fichier")
    parser.add_argument("--decrypt", help="Déchiffrer un fichier .enc")
    parser.add_argument("--encrypt-dir", help="Chiffrer un dossier")
    parser.add_argument("--decrypt-dir", help="Déchiffrer un dossier")
    parser.add_argument("--password", help="Mot de passe (sinon auto)")
    parser.add_argument("--gen-password", action="store_true", help="Générer un mot de passe")
    args = parser.parse_args()

    if args.gen_password:
        print(CryptoVault.generate_password(32))
        return

    password = args.password or get_vault_password()
    vault = CryptoVault(password)

    if args.encrypt:
        enc = vault.encrypt_file(args.encrypt)
        print(f"🔒 Chiffré: {enc}")
    elif args.decrypt:
        dec = vault.decrypt_file(args.decrypt)
        print(f"🔓 Déchiffré: {dec}")
    elif args.encrypt_dir:
        files = vault.encrypt_directory(args.encrypt_dir)
        print(f"🔒 {len(files)} fichiers chiffrés dans {args.encrypt_dir}")
    elif args.decrypt_dir:
        files = vault.decrypt_directory(args.decrypt_dir)
        print(f"🔓 {len(files)} fichiers déchiffrés dans {args.decrypt_dir}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
