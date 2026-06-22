"""Système de licence simple pour SafeTrendBot V5.

Licence embedded dans le build — pas de serveur, pas de HW-lock.

Format de clé : STB5-XXXX-XXXX-XXXX
- 4 groupes de 4 caractères séparés par '-'
- Le premier groupe est toujours 'STB5'
- Les 3 autres groupes sont alphanumériques (A-Z, 0-9)
- Checksum : somme des valeurs ord() de tous les caractères (hors '-')
  modulo 97 doit valoir 1
"""

from __future__ import annotations

import random
import re
import string
from pathlib import Path

# Format : STB5-XXXX-XXXX-XXXX
KEY_PATTERN = re.compile(r"^STB5-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")
PLACEHOLDER = "__EMBEDDED_KEY__"
ALPHABET = string.ascii_uppercase + string.digits  # A-Z0-9


def _checksum(key: str) -> int:
    """Calcule le checksum d'une clé (sans les '-')."""
    total = sum(ord(c) for c in key if c != "-")
    return total % 97


def _format_is_valid(key: str) -> bool:
    """Vérifie uniquement le format de la clé."""
    if not isinstance(key, str):
        return False
    return bool(KEY_PATTERN.match(key))


def generate_key() -> str:
    """Génère une clé valide au format STB5-XXXX-XXXX-XXXX.

    Génère aléatoirement les 12 caractères finaux, puis ajuste le dernier
    caractère pour que le checksum mod 97 == 1.
    """
    while True:
        # 3 groupes de 4 caractères aléatoires
        body = "".join(random.choice(ALPHABET) for _ in range(12))
        key = f"STB5-{body[:4]}-{body[4:8]}-{body[8:12]}"

        # Calcul du checksum actuel
        current = _checksum(key)
        # On veut que (current + delta) % 97 == 1
        # delta = (1 - current) % 97, appliqué sur le dernier caractère
        # via remplacement. On ajuste en remplaçant le dernier caractère.
        delta = (1 - current) % 97

        # On va modifier le dernier caractère pour atteindre le checksum cible.
        # Variation possible d'un caractère: au max ord('Z')=90 - ord('0')=48 = 42.
        # 97 > 42 donc il faut potentiellement modifier plusieurs caractères.
        # Plus simple: on itère en régénérant jusqu'à obtenir un checksum == 1.
        # Mais pour garantir la génération, on ajuste le dernier caractère
        # en cherchant la valeur qui convient.
        last_char = key[-1]
        base = ord(last_char)
        found = None
        for c in ALPHABET:
            new_key = key[:-1] + c
            if _checksum(new_key) == 1:
                found = new_key
                break
        if found is not None:
            return found
        # Sinon on recommence avec un nouveau body (rare)


class SimpleLicense:
    """Gestionnaire de licence simple (embedded key).

    Usage:
        lic = SimpleLicense()           # lit depuis __license_embed__
        lic = SimpleLicense("STB5-...")  # clé explicite
        if lic.validate():
            print("Licence valide:", lic.get_key())
    """

    def __init__(self, key: str | None = None):
        self._key: str = ""
        self._valid: bool = False
        if key is not None:
            self.set_key(key)
        else:
            # Lecture depuis le fichier embedded
            try:
                from app.core.__license_embed__ import EMBEDDED_KEY  # type: ignore
                self.set_key(EMBEDDED_KEY)
            except Exception:
                # Fallback: clé vide (mode libre potentiel)
                self._key = PLACEHOLDER
                self._valid = False

    def set_key(self, key: str) -> None:
        """Définit la clé et recalcule sa validité."""
        self._key = key if isinstance(key, str) else ""
        self._valid = self._compute_validity(self._key)

    @staticmethod
    def _compute_validity(key: str) -> bool:
        """Vérifie format + checksum."""
        if not _format_is_valid(key):
            return False
        return _checksum(key) == 1

    def validate(self) -> bool:
        """Valide la clé (format + checksum). Met à jour l'état interne."""
        self._valid = self._compute_validity(self._key)
        return self._valid

    def is_valid(self) -> bool:
        """Retourne True si la clé actuelle est valide."""
        return self._valid

    def get_key(self) -> str:
        """Retourne la clé courante."""
        return self._key

    def is_placeholder(self) -> bool:
        """Retourne True si la clé est encore le placeholder (mode libre)."""
        return self._key == PLACEHOLDER or not self._key


def embed_key_in_build(source_file: str, key: str) -> None:
    """Remplace __EMBEDDED_KEY__ dans un fichier Python par la clé donnée.

    Args:
        source_file: chemin vers le fichier Python contenant le placeholder.
        key: clé de licence à injecter (sera mise entre guillemets).
    """
    path = Path(source_file)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {source_file}")

    content = path.read_text(encoding="utf-8")
    # On remplace le placeholder par la clé, en préservant les guillemets.
    if PLACEHOLDER not in content:
        # Rien à remplacer — on tente quand même le pattern quoté
        content_new = content.replace(f'"{PLACEHOLDER}"', f'"{key}"')
        content_new = content_new.replace(f"'{PLACEHOLDER}'", f'"{key}"')
    else:
        content_new = content.replace(PLACEHOLDER, key)

    if content_new == content:
        raise ValueError(
            f"Placeholder {PLACEHOLDER} introuvable dans {source_file}"
        )

    path.write_text(content_new, encoding="utf-8")


# --- Tests rapides si exécuté directement ---
if __name__ == "__main__":
    k = generate_key()
    print("Clé générée:", k)
    lic = SimpleLicense(k)
    print("Valide:", lic.validate())
    print("is_valid:", lic.is_valid())
    print("Placeholder:", lic.is_placeholder())