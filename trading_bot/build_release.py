"""
SafeTrendBot V5 — Build Release Script
======================================
Génère les binaires pour Windows, Linux et macOS.

Usage:
    python build_release.py

Résultat:
    releases/
    ├── SafeTrendBot-v5.X.X-windows-x64.exe
    ├── SafeTrendBot-v5.X.X-linux-x64
    ├── SafeTrendBot-v5.X.X-macos-x64
    └── SafeTrendBot-v5.X.X-macos-arm64

⚠️  CE SCRIPT NE DOIT PAS ÊTRE DISTRIBUÉ AUX CLIENTS.
"""

import sys
import os
import shutil
import subprocess
import json
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

VERSION = "5.3.0"
APP_NAME = "SafeTrendBot"
BUILD_DIR = Path("build")
RELEASE_DIR = Path("releases")
DIST_DIR = Path("dist")

# Fichiers critiques à compiler/obfusquer
CRITICAL_MODULES = [
    "app/core/license_manager.py",
    "app/core/anti_tamper.py",
    "app/core/trading_engine_v4.py",
    "app/core/extreme_guard.py",
    "app/core/adaptive_strategies.py",
    "app/core/regime_detector.py",
    "app/core/strategies.py",
    "app/core/trading_profiles.py",
]

# Modules à inclure dans le binaire
ENTRY_POINTS = {
    "gui": "main.py",
    "headless": "headless.py",
}


def print_banner(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def run(cmd, cwd=None, check=True):
    """Exécute une commande shell."""
    print(f"$ {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and check:
        print(f"❌ ERREUR: {result.stderr.strip()}")
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 0: Vérification environnement
# ═══════════════════════════════════════════════════════════════════════════════

def check_env():
    print_banner("🔍 Vérification environnement de build")

    required = {
        "PyInstaller": "pyinstaller",
        "Cython": "cython",
    }

    ok = True
    for name, pkg in required.items():
        try:
            __import__(pkg)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} manquant — pip install {pkg}")
            ok = False

    # Vérifier PyArmor (optionnel)
    try:
        import pyarmor
        print(f"   ✅ PyArmor (optionnel)")
    except ImportError:
        print(f"   ⚠️  PyArmor manquant — pip install pyarmor (optionnel)")

    if not ok:
        print("\n❌ Installez les dépendances manquantes:")
        print("   pip install pyinstaller cython pyarmor")
        sys.exit(1)

    print("   ✅ Environnement OK\n")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1: Obfuscation Cython
# ═══════════════════════════════════════════════════════════════════════════════

def obfuscate_cython():
    print_banner("🔒 Étape 1: Obfuscation Cython (modules critiques)")

    root = Path.cwd()
    setup_py = root / "setup_cython_build.py"

    # Générer setup.py temporaire
    modules_str = ",\n            ".join(f'"{m}"' for m in CRITICAL_MODULES)
    setup_content = f'''from setuptools import setup
from Cython.Build import cythonize
from Cython.Distutils import build_ext

setup(
    name="{APP_NAME}_Critical",
    ext_modules=cythonize(
        [
            {modules_str}
        ],
        compiler_directives={{
            'language_level': "3",
            'embedsignature': False,
            'boundscheck': False,
            'wraparound': False,
        }},
        annotate=False,
    ),
    cmdclass={{'build_ext': build_ext}},
)
'''
    setup_py.write_text(setup_content)

    # Compiler
    ok = run(f"python {setup_py} build_ext --inplace")
    setup_py.unlink()

    if ok:
        print("   ✅ Fichiers critiques compilés en binaire\n")
    else:
        print("   ⚠️  Cython échoué — fallback PyInstaller simple\n")

    return ok


# ═══════════════════════════════════════════════════════════════════════════════
# Étape 2: Nettoyage
# ═══════════════════════════════════════════════════════════════════════════════

def clean_build():
    print_banner("🧹 Étape 2: Nettoyage")

    dirs = [BUILD_DIR, DIST_DIR, RELEASE_DIR]
    for d in dirs:
        if d.exists():
            shutil.rmtree(d)
            print(f"   🗑️  {d}/ supprimé")

    # Supprimer anciens builds Cython
    for f in Path(".").rglob("*.c"):
        if "cython" in f.name.lower() or any(m.replace("/", ".") in f.name for m in CRITICAL_MODULES):
            f.unlink()

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    print("   ✅ Propre\n")


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3: Build GUI (main.py)
# ═══════════════════════════════════════════════════════════════════════════════

def build_gui(target_os: str, target_arch: str, build_version: str = VERSION) -> Path:
    print_banner(f"📦 Étape 3: Build GUI — {target_os} {target_arch}")

    root = Path.cwd()
    build_name = f"{APP_NAME}-v{build_version}-{target_os}-{target_arch}"
    out_dir = DIST_DIR / build_name

    # Déterminer les options selon la plateforme
    is_win = target_os == "windows"
    console_flag = "--windowed" if is_win else "--windowed"
    onefile_flag = "--onefile"  # Single executable
    name_flag = f"--name {APP_NAME}"

    # Icon
    icon_path = root / "icon.ico"
    icon_flag = f"--icon={icon_path}" if icon_path.exists() else ""

    # Data files
    data_flags = " ".join([
        f'--add-data "{root / "app"}{os.pathsep}app"',
        f'--add-data "{root / "bot"}{os.pathsep}bot"',
        f'--add-data "{root / "backtest"}{os.pathsep}backtest"',
    ])

    # Hidden imports
    hidden = " ".join([
        "--hidden-import app.core.trading_engine_v4",
        "--hidden-import app.core.license_manager",
        "--hidden-import app.core.anti_tamper",
        "--hidden-import app.core.extreme_guard",
        "--hidden-import app.core.trading_profiles",
        "--hidden-import app.core.regime_detector",
        "--hidden-import app.core.adaptive_strategies",
        "--hidden-import app.core.portfolio_manager",
        "--hidden-import app.core.performance_metrics",
        "--hidden-import app.core.strategies",
        "--hidden-import app.core.market_filters",
        "--hidden-import app.core.trade_journal",
        "--hidden-import app.core.paper_trading",
        "--hidden-import app.brokers.mt5_adapter",
        "--hidden-import app.brokers.ib_adapter",
        "--hidden-import app.brokers.crypto_adapter",
        "--hidden-import bot.telegram_alerts",
        "--hidden-import bot.economic_calendar",
        "--hidden-import bot.news_feed",
        "--hidden-import PyQt6.sip",
        "--hidden-import numpy.core._dtype_ctypes",
    ])

    cmd = (
        f"pyinstaller {root / 'main.py'} "
        f"{onefile_flag} {console_flag} {name_flag} {icon_flag} "
        f"{data_flags} {hidden} "
        f"--distpath {out_dir} "
        f"--workpath {BUILD_DIR / 'gui'} "
        f"--specpath {BUILD_DIR} "
        f"--clean -y "
        f"--exclude-module matplotlib.tests "
        f"--exclude-module numpy.random._examples"
    )

    ok = run(cmd)
    if not ok:
        return None

    # Renommer avec extension correcte
    exe_name = f"{APP_NAME}.exe" if is_win else APP_NAME
    exe_path = out_dir / exe_name

    if not exe_path.exists():
        print(f"   ❌ Binaire introuvable: {exe_path}")
        return None

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Binaire: {exe_path} ({size_mb:.1f} MB)\n")

    return exe_path


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 4: Build Headless
# ═══════════════════════════════════════════════════════════════════════════════

def build_headless(target_os: str, target_arch: str, build_version: str = VERSION) -> Path:
    print_banner(f"🤖 Étape 4: Build Headless — {target_os} {target_arch}")

    root = Path.cwd()
    build_name = f"{APP_NAME}Headless-v{build_version}-{target_os}-{target_arch}"
    out_dir = DIST_DIR / build_name

    is_win = target_os == "windows"
    console_flag = "--console"  # Headless = console
    onefile_flag = "--onefile"
    name_flag = f"--name {APP_NAME}Headless"

    data_flags = " ".join([
        f'--add-data "{root / "app"}{os.pathsep}app"',
        f'--add-data "{root / "bot"}{os.pathsep}bot"',
    ])

    hidden = " ".join([
        "--hidden-import app.core.trading_engine_v4",
        "--hidden-import app.core.license_manager",
        "--hidden-import app.core.anti_tamper",
        "--hidden-import app.core.extreme_guard",
        "--hidden-import app.core.trading_profiles",
        "--hidden-import app.core.regime_detector",
        "--hidden-import app.core.adaptive_strategies",
        "--hidden-import app.core.portfolio_manager",
        "--hidden-import app.core.performance_metrics",
        "--hidden-import app.core.strategies",
        "--hidden-import app.core.market_filters",
        "--hidden-import app.core.trade_journal",
        "--hidden-import app.core.paper_trading",
        "--hidden-import app.brokers.mt5_adapter",
        "--hidden-import app.brokers.ib_adapter",
        "--hidden-import app.brokers.crypto_adapter",
        "--hidden-import bot.telegram_alerts",
        "--hidden-import bot.economic_calendar",
        "--hidden-import bot.news_feed",
        "--hidden-import numpy.core._dtype_ctypes",
    ])

    cmd = (
        f"pyinstaller {root / 'headless.py'} "
        f"{onefile_flag} {console_flag} {name_flag} "
        f"{data_flags} {hidden} "
        f"--distpath {out_dir} "
        f"--workpath {BUILD_DIR / 'headless'} "
        f"--specpath {BUILD_DIR} "
        f"--clean -y "
        f"--exclude-module matplotlib.tests "
        f"--exclude-module numpy.random._examples"
    )

    ok = run(cmd)
    if not ok:
        return None

    exe_name = f"{APP_NAME}Headless.exe" if is_win else f"{APP_NAME}Headless"
    exe_path = out_dir / exe_name

    if not exe_path.exists():
        return None

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Binaire: {exe_path} ({size_mb:.1f} MB)\n")

    return exe_path


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 5: Packaging
# ═══════════════════════════════════════════════════════════════════════════════

def package_release(exe_path: Path, target_os: str, target_arch: str, build_version: str = VERSION, is_headless: bool = False):
    print_banner(f"📦 Étape 5: Packaging — {target_os} {target_arch}")

    suffix = "Headless" if is_headless else ""
    base_name = f"{APP_NAME}{suffix}-v{build_version}-{target_os}-{target_arch}"

    # Créer dossier temporaire
    pkg_dir = DIST_DIR / base_name
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Copier le binaire
    ext = ".exe" if target_os == "windows" else ""
    final_name = f"{APP_NAME}{suffix}{ext}"
    shutil.copy2(exe_path, pkg_dir / final_name)

    # Copier fichiers README et docs
    docs = ["README.md", "INSTALLATION.md", "CHANGELOG.md", "BROKERS.md"]
    for doc in docs:
        src = Path(doc)
        if src.exists():
            shutil.copy2(src, pkg_dir / doc)

    # Créer archive
    if target_os == "windows":
        # ZIP pour Windows
        zip_path = RELEASE_DIR / f"{base_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in pkg_dir.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(pkg_dir))
        print(f"   ✅ ZIP: {zip_path}")
        archive = zip_path
    else:
        # tar.gz pour Linux/macOS
        tar_path = RELEASE_DIR / f"{base_name}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(pkg_dir, arcname=base_name)
        print(f"   ✅ tar.gz: {tar_path}")
        archive = tar_path

    # Info
    size_mb = archive.stat().st_size / (1024 * 1024)
    print(f"   📦 Taille: {size_mb:.1f} MB\n")

    return archive


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def detect_platform():
    """Détecte la plateforme courante."""
    if sys.platform == "win32":
        return "windows", "x64"
    elif sys.platform == "darwin":
        arch = "arm64" if os.uname().machine == "arm64" else "x64"
        return "macos", arch
    else:
        return "linux", "x64"


def build_current_platform(build_version: str = VERSION):
    """Build pour la plateforme courante (local)."""
    target_os, target_arch = detect_platform()

    print_banner(f"🚀 SafeTrendBot V{build_version} — Build pour {target_os} {target_arch}")

    check_env()
    clean_build()
    obfuscate_cython()

    # Build GUI
    gui_exe = build_gui(target_os, target_arch, build_version)
    if gui_exe:
        package_release(gui_exe, target_os, target_arch, build_version)

    # Build Headless
    headless_exe = build_headless(target_os, target_arch, build_version)
    if headless_exe:
        package_release(headless_exe, target_os, target_arch, build_version, is_headless=True)

    # Résumé
    print_banner("🎉 BUILD TERMINÉ")
    print(f"   📁 Répertoire releases/: {RELEASE_DIR.absolute()}")
    for f in RELEASE_DIR.iterdir():
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"   📦 {f.name} ({size_mb:.1f} MB)")
    print()


def build_all_platforms(build_version: str = VERSION):
    """
    Build pour toutes les plateformes (nécessite cross-compilation ou CI).
    En local, ne build que la plateforme courante.
    """
    print_banner("🚀 SafeTrendBot V5 — Build Multi-Plateforme")
    print("   En local: build uniquement pour la plateforme courante.")
    print("   Pour Windows/macOS: utilisez GitHub Actions (voir .github/workflows/)")
    print()
    build_current_platform(build_version)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build SafeTrendBot releases")
    parser.add_argument("--version", default=VERSION, help="Version number")
    parser.add_argument("--platform", choices=["windows", "linux", "macos", "all"],
                        default="current", help="Target platform")
    args = parser.parse_args()

    # Utiliser version locale sans global
    build_version = args.version

    if args.platform == "all":
        build_all_platforms(build_version)
    else:
        build_current_platform(build_version)


if __name__ == "__main__":
    main()
