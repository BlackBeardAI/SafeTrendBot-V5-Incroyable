"""
Build Generator — Crée des builds SafeTrendBot avec licence unique
====================================================================

Ce script prend un build de base et crée N builds uniques,
chacun avec une licence différente pré-injectée.

Usage:
    python build_generator.py --base build/SafeTrendBot.exe --count 50
    → Génère 50 builds uniques dans builds_per_client/

    python build_generator.py --base build/SafeTrendBot.tar.gz --count 100 --output-dir mes_ventes/
    → Génère 100 builds pour distribution

Chaque build contient:
    - Le binaire SafeTrendBot avec licence unique injectée
    - Un fichier README client
    - La licence en clair (pour le client)

Workflow:
    1. Tu compiles le build de base avec PyInstaller
    2. Tu génères des licences avec license_generator.py
    3. Tu crées N builds avec ce script
    4. Tu distribues UN build par client
    5. Le client installe → la licence est consommée → auto-suppression
"""

import sys
import os
import shutil
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime


def inject_license_into_exe(exe_path: Path, license_key: str, output_path: Path):
    """Injecte une licence dans un fichier binaire (.exe ou Linux binary)."""
    content = exe_path.read_bytes()

    # Placeholder à rechercher dans le binaire
    # Doit correspondre à celui défini dans license_manager_v2.py
    marker = b"__LICENSE_PLACEHOLDER__"
    padded_license = license_key.encode("utf-8").ljust(64, b"_")

    if marker not in content:
        # Fallback: chercher un pattern générique
        # Le build de base doit contenir ce placeholder
        print(f"❌ Placeholder introuvable dans {exe_path}")
        print("   Assure-toi que license_manager_v2 est compilé dans le build.")
        return False

    new_content = content.replace(marker, padded_license)
    output_path.write_bytes(new_content)
    return True


def create_client_package(base_exe: Path, license_key: str, output_dir: Path, client_name: str = ""):
    """
    Crée un package complet pour un client:
    - Binaire avec licence injectée
    - Fichier README client
    - Fichier licence.txt
    """
    pkg_dir = output_dir / f"client_{client_name or license_key[:8]}"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Copier et injecter le binaire
    ext = base_exe.suffix  # .exe ou ""
    new_name = f"SafeTrendBot{ext}"
    new_exe = pkg_dir / new_name

    ok = inject_license_into_exe(base_exe, license_key, new_exe)
    if not ok:
        return None

    # Créer README client
    readme = f"""SafeTrendBot V5 — Installation Client
=====================================

Licence: {license_key}
Date: {datetime.now().strftime('%Y-%m-%d')}

INSTRUCTIONS:
1. Double-cliquez sur SafeTrendBot{ext}
2. La licence sera activée automatiquement sur cet ordinateur
3. Le fichier d'installation sera supprimé après activation
4. Ne partagez PAS ce fichier avec d'autres — il ne fonctionnera que sur ce PC

⚠️  ATTENTION:
- Cette licence est à usage UNIQUE
- Une fois activée, elle ne fonctionnera que sur cet ordinateur
- Le fichier d'installation s'autodétruira après la première utilisation

Support: contact@safetrendbot.com
"""
    (pkg_dir / "README.txt").write_text(readme, encoding="utf-8")

    # Licence en clair
    (pkg_dir / "VOTRE_LICENCE.txt").write_text(license_key, encoding="utf-8")

    return pkg_dir


def generate_builds(base_path: Path, license_keys: list, output_dir: Path):
    """Génère un build unique pour chaque licence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for i, key in enumerate(license_keys, 1):
        pkg = create_client_package(base_path, key, output_dir, f"{i:03d}")
        if pkg:
            results.append(pkg)
            print(f"✅ Build #{i}: {pkg.name} — licence {key}")
        else:
            print(f"❌ Échec build #{i}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build Generator SafeTrendBot")
    parser.add_argument("--base", required=True, help="Chemin du build de base (.exe ou binaire)")
    parser.add_argument("--count", type=int, default=10, help="Nombre de builds à générer")
    parser.add_argument("--output-dir", default="builds_per_client", help="Dossier de sortie")
    parser.add_argument("--licenses", help="Fichier licences.txt (sinon génère automatiquement)")
    args = parser.parse_args()

    base_path = Path(args.base)
    if not base_path.exists():
        print(f"❌ Build de base introuvable: {base_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir)

    # Charger ou générer les licences
    if args.licenses:
        with open(args.licenses) as f:
            license_keys = [line.strip() for line in f if line.strip()]
    else:
        # Générer automatiquement
        from license_generator import generate_licenses, LicenseStore
        store = LicenseStore()
        license_keys = generate_licenses(args.count, store)
        print(f"✅ {len(license_keys)} licences générées\n")

    # Générer les builds
    print(f"🚀 Génération de {len(license_keys)} builds uniques...")
    results = generate_builds(base_path, license_keys, output_dir)

    # Résumé
    print(f"\n🎉 {len(results)} builds créés dans: {output_dir.absolute()}")
    print(f"   Chaque build contient une licence unique pré-injectée.")
    print(f"   Distribue UN dossier par client.")


if __name__ == "__main__":
    main()
