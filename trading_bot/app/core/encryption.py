"""
Encryption (NEUTRALISÉ) — ne chiffre plus rien.
Garde l'interface CryptoVault pour compatibilité.
"""


class CryptoVault:
    """Stub — ne chiffre/déchiffre rien, passe les données en clair."""

    @staticmethod
    def encrypt(data: str) -> str:
        return data

    @staticmethod
    def decrypt(data: str) -> str:
        return data

    @staticmethod
    def encrypt_file(path) -> None:
        pass

    @staticmethod
    def decrypt_file(path) -> None:
        pass