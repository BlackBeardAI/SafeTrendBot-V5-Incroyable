"""
License Generator — Générateur de licences SafeTrendBot V5
==========================================================

Génère des licences uniques à usage unique pour SafeTrendBot.
Chaque licence est une chaîne aléatoire de 24 caractères (base58).

Usage:
    python license_generator.py generate 50
    → Génère 50 licences uniques, les sauvegarde dans licenses.json

    python license_generator.py generate --output mes_clients.csv
    → Exporte en CSV pour import dans CRM

    python license_generator.py status
    → Liste les licences (utilisées / inutilisées)

    python license_generator.py inject --license XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    → Injecte une licence dans un build
"""

import sys
import json
import csv
import secrets
import string
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

LICENSE_FILE = Path("licenses.json")
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"  # Base58
LICENSE_PART_LEN = 6
LICENSE_PARTS = 4  # Total: 24 chars (ex: A3x9K-LmP2Q-rT5vW-zB8nJ)


@dataclass
class License:
    key: str
    created_at: str
    used: bool = False
    used_at: Optional[str] = None
    hardware_id: Optional[str] = None
    build_id: Optional[str] = None
    revoked: bool = False
    notes: str = ""


class LicenseStore:
    """Stockage JSON des licences."""

    def __init__(self, path: Path = LICENSE_FILE):
        self.path = path
        self.licenses: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            self.licenses = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.licenses = {}

    def _save(self):
        self.path.write_text(
            json.dumps(self.licenses, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def add(self, license_obj: License):
        self.licenses[license_obj.key] = asdict(license_obj)
        self._save()

    def get(self, key: str) -> Optional[License]:
        data = self.licenses.get(key)
        if data:
            return License(**data)
        return None

    def mark_used(self, key: str, hardware_id: str, build_id: str):
        if key in self.licenses:
            self.licenses[key]["used"] = True
            self.licenses[key]["used_at"] = datetime.utcnow().isoformat()
            self.licenses[key]["hardware_id"] = hardware_id
            self.licenses[key]["build_id"] = build_id
            self._save()

    def revoke(self, key: str):
        if key in self.licenses:
            self.licenses[key]["revoked"] = True
            self._save()

    def list_all(self) -> List[License]:
        return [License(**v) for v in self.licenses.values()]

    def stats(self) -> dict:
        total = len(self.licenses)
        used = sum(1 for v in self.licenses.values() if v.get("used"))
        revoked = sum(1 for v in self.licenses.values() if v.get("revoked"))
        return {"total": total, "used": used, "available": total - used, "revoked": revoked}


# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_key() -> str:
    """Génère une licence unique format XXXX-XXXX-XXXX-XXXX."""
    parts = []
    for _ in range(LICENSE_PARTS):
        part = "".join(secrets.choice(ALPHABET) for _ in range(LICENSE_PART_LEN))
        parts.append(part)
    return "-".join(parts)


def generate_licenses(n: int, store: LicenseStore) -> List[str]:
    """Génère N licences uniques, évite les doublons."""
    keys = []
    for _ in range(n):
        while True:
            key = generate_key()
            if key not in store.licenses:
                break
        lic = License(key=key, created_at=datetime.utcnow().isoformat())
        store.add(lic)
        keys.append(key)
    return keys


# ─────────────────────────────────────────────────────────────────────────────
# INJECTION DANS UN BUILD
# ─────────────────────────────────────────────────────────────────────────────

def inject_license_into_build(build_path: Path, license_key: str, output_path: Path):
    """
    Injecte une licence dans un fichier binaire compilé.
    Remplace le placeholder __LICENSE_PLACEHOLDER__ par la vraie licence.
    """
    content = build_path.read_bytes()

    # Placeholder attendu dans le binaire (injecté à la compilation)
    placeholder = b"__LICENSE_PLACEHOLDER__" + b"_" * 32

    # Padding pour atteindre la taille du placeholder
    license_bytes = license_key.encode("utf-8")
    padded = license_bytes + b"\x00" * (len(placeholder) - len(license_bytes))

    if placeholder not in content:
        print(f"❌ Placeholder introuvable dans {build_path}")
        print("   Le build doit être compilé avec le placeholder.")
        return False

    new_content = content.replace(placeholder, padded)
    output_path.write_bytes(new_content)

    print(f"✅ Licence injectée: {license_key}")
    print(f"   Build: {output_path}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def cli_generate(args):
    n = int(args[0]) if args else 10
    store = LicenseStore()
    keys = generate_licenses(n, store)

    print(f"✅ {n} licences générées")
    for k in keys:
        print(f"   {k}")

    # Sauvegarde aussi dans un fichier texte facile à copier
    txt_file = LICENSE_FILE.with_suffix(".txt")
    with open(txt_file, "w") as f:
        for k in keys:
            f.write(f"{k}\n")
    print(f"\n📁 Sauvegardées dans: {LICENSE_FILE} et {txt_file}")

    stats = store.stats()
    print(f"\n📊 Total: {stats['total']} | Utilisées: {stats['used']} | Disponibles: {stats['available']}")


def cli_export_csv(args):
    store = LicenseStore()
    output = args[0] if args else "licenses_export.csv"

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["License Key", "Created At", "Used", "Used At", "Hardware ID", "Revoked", "Notes"])
        for lic in store.list_all():
            writer.writerow([lic.key, lic.created_at, lic.used, lic.used_at or "", lic.hardware_id or "", lic.revoked, lic.notes])

    print(f"✅ Export CSV: {output} ({len(store.licenses)} lignes)")


def cli_status(args):
    store = LicenseStore()
    stats = store.stats()
    print(f"📊 Statistiques licences:")
    print(f"   Total:      {stats['total']}")
    print(f"   Utilisées:  {stats['used']}")
    print(f"   Disponibles: {stats['available']}")
    print(f"   Révoquées:  {stats['revoked']}")

    # Afficher les 10 dernières
    print(f"\n📝 10 dernières licences:")
    for lic in sorted(store.list_all(), key=lambda x: x.created_at, reverse=True)[:10]:
        status = "✅" if lic.used else "🟢" if not lic.revoked else "🚫"
        print(f"   {status} {lic.key} | {lic.created_at[:10]}")


def cli_inject(args):
    if len(args) < 2:
        print("Usage: python license_generator.py inject <build_path> <license_key>")
        sys.exit(1)
    build_path = Path(args[0])
    license_key = args[1]
    output_path = Path(args[2]) if len(args) > 2 else build_path.with_suffix(".licensed" + build_path.suffix)

    store = LicenseStore()
    lic = store.get(license_key)
    if not lic:
        print(f"❌ Licence inconnue: {license_key}")
        sys.exit(1)
    if lic.used:
        print(f"❌ Licence déjà utilisée: {license_key}")
        print(f"   Hardware ID: {lic.hardware_id}")
        sys.exit(1)

    ok = inject_license_into_build(build_path, license_key, output_path)
    if ok:
        print(f"\n⚠️  Ce build est maintenant lié à la licence {license_key}")
        print(f"   Distribuez-le à UN SEUL client.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "generate":
        cli_generate(args)
    elif cmd == "export":
        cli_export_csv(args)
    elif cmd == "status":
        cli_status(args)
    elif cmd == "inject":
        cli_inject(args)
    else:
        print(f"Commande inconnue: {cmd}")
        print("Commands: generate, export, status, inject")
        sys.exit(1)


if __name__ == "__main__":
    main()
