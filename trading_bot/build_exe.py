#!/usr/bin/env python3
"""Générateur de build .exe pour SafeTrendBot V5.

Usage:
    # Générer une clé de licence et l'afficher
    python build_exe.py --generate

    # Build avec une clé existante
    python build_exe.py --key STB5-XXXX-XXXX-XXXX

    # Build avec génération automatique de clé
    python build_exe.py --generate --build

Le build utilise PyInstaller en --onefile --noconsole.
Le .exe final est dans dist/SafeTrendBot.exe.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Racine du projet trading_bot/
ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "main.py"
EMBED_FILE = ROOT / "app" / "core" / "__license_embed__.py"
PLACEHOLDER = "__EMBEDDED_KEY__"
EXE_NAME = "SafeTrendBot"
DIST_DIR = ROOT / "dist"


def _import_license():
    """Importe le module simple_license depuis app/core."""
    sys.path.insert(0, str(ROOT))
    from app.core.simple_license import (  # type: ignore
        generate_key,
        SimpleLicense,
        embed_key_in_build,
    )
    return generate_key, SimpleLicense, embed_key_in_build


def cmd_generate() -> int:
    """Génère et affiche une clé valide."""
    generate_key, SimpleLicense, _ = _import_license()
    key = generate_key()
    lic = SimpleLicense(key)
    assert lic.validate(), "Clé générée invalide!"
    print(key)
    return 0


def _inject_key(key: str) -> None:
    """Injecte la clé dans le fichier __license_embed__.py."""
    _, _, embed_key_in_build = _import_license()
    # Réinitialiser le fichier avec le placeholder avant injection
    EMBED_FILE.write_text(
        '"""Fichier d\'embedding de clé de licence.\n\n'
        "Généré automatiquement par build_exe.py.\n"
        '"""\n\n'
        f'EMBEDDED_KEY = "{PLACEHOLDER}"\n',
        encoding="utf-8",
    )
    embed_key_in_build(str(EMBED_FILE), key)
    print(f"[OK] Clé injectée dans {EMBED_FILE}")


def _restore_placeholder() -> None:
    """Restaure le fichier embedded avec le placeholder."""
    EMBED_FILE.write_text(
        '"""Fichier d\'embedding de clé de licence.\n\n'
        "Généré automatiquement par build_exe.py.\n"
        '"""\n\n'
        f'EMBEDDED_KEY = "{PLACEHOLDER}"\n',
        encoding="utf-8",
    )


def cmd_build(key: str) -> int:
    """Build le .exe avec la clé donnée."""
    if not ENTRY.exists():
        print(f"[ERREUR] Point d'entrée introuvable: {ENTRY}")
        return 1

    # Valider la clé
    _, SimpleLicense, _ = _import_license()
    lic = SimpleLicense(key)
    if not lic.validate():
        print(f"[ERREUR] Clé de licence invalide: {key}")
        return 1

    print(f"[INFO] Clé de licence: {key}")
    print(f"[INFO] Validation: {'OK' if lic.is_valid() else 'ÉCHEC'}")

    # 1. Injecter la clé
    _inject_key(key)

    try:
        # 2. Lancer PyInstaller
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--noconsole",
            "--name", EXE_NAME,
            "--distpath", str(DIST_DIR),
            "--workpath", str(ROOT / "build"),
            "--specpath", str(ROOT),
            str(ENTRY),
        ]

        # Inclure les datas éventuels (icône, etc.) si présents
        icon = ROOT / "assets" / "icon.ico"
        if icon.exists():
            cmd += ["--icon", str(icon)]

        print(f"[INFO] Commande PyInstaller: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(ROOT))
        if result.returncode != 0:
            print("[ERREUR] Build PyInstaller échoué.")
            return result.returncode

        exe_path = DIST_DIR / f"{EXE_NAME}.exe"
        if not exe_path.exists():
            # Sur Linux, PyInstaller ne produit pas de .exe mais un binaire
            bin_path = DIST_DIR / EXE_NAME
            if bin_path.exists():
                print(f"[OK] Binaire généré: {bin_path}")
                return 0
            print(f"[ERREUR] .exe non trouvé: {exe_path}")
            return 1

        print(f"[OK] .exe généré: {exe_path}")
        return 0
    finally:
        # 3. Restaurer le placeholder pour ne pas committer la clé
        _restore_placeholder()
        print("[INFO] Placeholder restauré dans __license_embed__.py")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build .exe SafeTrendBot V5 avec licence embedded"
    )
    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="Clé de licence STB5-XXXX-XXXX-XXXX",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Génère une clé de licence valide",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Lancer le build PyInstaller (sinon affiche juste la clé)",
    )
    args = parser.parse_args()

    key = args.key

    if args.generate:
        generate_key, _, _ = _import_license()
        key = generate_key()
        if not args.build:
            print(key)
            return 0

    if args.build:
        if key is None:
            print("[ERREUR] --build nécessite --key ou --generate")
            return 1
        return cmd_build(key)

    # Par défaut: si --generate seul → déjà géré. Sinon aide.
    if key is None and not args.generate:
        parser.print_help()
        return 1

    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())