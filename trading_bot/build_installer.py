"""
Script de build - Crée un exécutable Windows .exe avec toutes les dépendances.
Utilise PyInstaller pour l'exe puis Inno Setup pour l'installeur.

Usage sur Windows (depuis le dossier du projet) :
    python build_installer.py

Prérequis :
    pip install pyinstaller
    Inno Setup (optionnel) : https://jrsoftware.org/isdl.php
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLER_DIR = PROJECT_ROOT / "installer"


def step(num, title):
    print()
    print("=" * 60)
    print(f"{num}. {title}")
    print("=" * 60)


def ensure_dependencies():
    step(1, "Verification des dependances")

    required = {
        "pyinstaller": "pyinstaller",
        "PyQt6": "PyQt6",
        "numpy": "numpy",
        "pandas": "pandas",
        "yfinance": "yfinance",
        "matplotlib": "matplotlib",
        "requests": "requests",
        "MetaTrader5": "MetaTrader5",
    }

    for module, package in required.items():
        try:
            __import__(module)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [..] Installation de {package}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package, "--quiet"]
            )


def clean_previous_builds():
    step(2, "Nettoyage des builds precedents")

    for path in [DIST_DIR, BUILD_DIR, PROJECT_ROOT / "main.spec"]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            print(f"  Supprime : {path.name}")
    print("  OK")


def build_executable():
    step(3, "Creation de l'executable avec PyInstaller")

    sep = os.pathsep
    args = [
        "pyinstaller",
        "--name=SafeTrendBot",
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=MetaTrader5",
        "--hidden-import=numpy",
        "--hidden-import=pandas",
        "--hidden-import=yfinance",
        "--hidden-import=matplotlib",
        "--hidden-import=requests",
        "--collect-all=yfinance",
        f"--add-data={PROJECT_ROOT / 'bot'}{sep}bot",
        f"--add-data={PROJECT_ROOT / 'backtest'}{sep}backtest",
        f"--add-data={PROJECT_ROOT / 'app'}{sep}app",
        str(PROJECT_ROOT / "main.py"),
    ]

    print("  Lancement de PyInstaller (plusieurs minutes)...")
    subprocess.check_call(args)
    exe_path = DIST_DIR / "SafeTrendBot" / "SafeTrendBot.exe"
    print(f"  [OK] Executable : {exe_path}")


def create_inno_script():
    """Genere le script .iss depuis le template"""
    step(4, "Generation du script Inno Setup")

    INSTALLER_DIR.mkdir(exist_ok=True)
    template_path = INSTALLER_DIR / "SafeTrendBot_Installer.iss.template"
    output_path = INSTALLER_DIR / "SafeTrendBot_Installer.iss"

    if not template_path.exists():
        print(f"  [ERREUR] Template introuvable : {template_path}")
        return None

    # Lire le template
    content = template_path.read_text(encoding='utf-8')

    # Remplacer les variables
    source_dir = str(DIST_DIR / "SafeTrendBot").replace('/', '\\')
    output_dir = str(INSTALLER_DIR).replace('/', '\\')
    content = content.replace("{{SOURCE_DIR}}", source_dir)
    content = content.replace("{{OUTPUT_DIR}}", output_dir)

    output_path.write_text(content, encoding='utf-8')
    print(f"  [OK] Script : {output_path}")
    return output_path


def compile_installer(iss_path):
    step(5, "Compilation de l'installeur (Inno Setup)")

    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    ]

    iscc = next((p for p in candidates if os.path.exists(p)), None)

    if not iscc:
        print("  [INFO] Inno Setup non trouve.")
        print("  Telecharger : https://jrsoftware.org/isdl.php")
        print(f"  Compilation manuelle possible : {iss_path}")
        return False

    print(f"  Inno Setup : {iscc}")
    subprocess.check_call([iscc, str(iss_path)])
    print("  [OK] Installeur cree")
    return True


def create_portable_zip():
    step(6, "Creation du ZIP portable")

    zip_path = INSTALLER_DIR / "SafeTrendBot_Portable_v1.0.0.zip"
    source_dir = DIST_DIR / "SafeTrendBot"

    if not source_dir.exists():
        print("  [ERREUR] Dossier source introuvable")
        return

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                filepath = Path(root) / file
                arcname = filepath.relative_to(source_dir.parent)
                zf.write(filepath, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] {zip_path.name} ({size_mb:.1f} MB)")


def main():
    print()
    print("=" * 60)
    print("  BUILD SAFETRENDBOT - Installeur Windows")
    print("=" * 60)

    if sys.platform != 'win32':
        print()
        print("Ce script est concu pour Windows.")
        print("Sur Linux, utilisez : python main.py")
        return 1

    try:
        ensure_dependencies()
        clean_previous_builds()
        build_executable()
        iss_path = create_inno_script()
        if iss_path:
            compile_installer(iss_path)
        create_portable_zip()

        print()
        print("=" * 60)
        print("  BUILD TERMINE")
        print("=" * 60)
        print()
        print(f"Executable      : {DIST_DIR / 'SafeTrendBot' / 'SafeTrendBot.exe'}")
        print(f"Version portable: {INSTALLER_DIR / 'SafeTrendBot_Portable_v1.0.0.zip'}")
        print(f"Installeur      : {INSTALLER_DIR} (si Inno Setup installe)")
        print()

    except subprocess.CalledProcessError as e:
        print(f"\n[ERREUR] Build echoue : {e}")
        return 1
    except Exception as e:
        print(f"\n[ERREUR] {type(e).__name__}: {e}")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
