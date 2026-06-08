"""
Build script — compile SafeTrendBot en .exe standalone avec obfuscation.
Usage: python build.py
"""
import sys
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def run(cmd, check=True):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and check:
        print(f"ERREUR: {result.stderr.strip()}")
        return False
    return True


def check_tools():
    """Vérifie les outils nécessaires"""
    print_header("Vérification des outils")
    
    tools_ok = True
    
    # PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller disponible")
    except ImportError:
        print("❌ PyInstaller manquant — pip install pyinstaller")
        tools_ok = False
    
    # Cython (optionnel mais recommandé)
    try:
        import Cython
        print("✅ Cython disponible")
    except ImportError:
        print("⚠️  Cython manquant — pip install cython (optionnel)")
    
    # PyArmor (optionnel, plus fort)
    try:
        import pyarmor
        print("✅ PyArmor disponible")
    except ImportError:
        print("⚠️  PyArmor manquant — pip install pyarmor (optionnel)")
    
    return tools_ok


def obfuscate_with_cython():
    """
    Compile les fichiers critiques en .pyd (Windows) / .so (Linux)
    pour empêcher la décompilation du source Python.
    """
    print_header("Obfuscation Cython — compilation en modules binaires")
    
    root = Path(__file__).parent
    core_dir = root / "app" / "core"
    build_dir = root / "build_cython"
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    
    # Fichiers critiques à compiler
    critical_files = [
        "license_manager.py",
        "anti_tamper.py",
        "trading_engine_v4.py",
        "adaptive_strategies.py",
        "strategies.py",
    ]
    
    # Créer le setup.py temporaire pour Cython
    setup_content = """
from setuptools import setup
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

setup(
    ext_modules=cythonize(
        [
            "app/core/license_manager.py",
            "app/core/anti_tamper.py",
            "app/core/trading_engine_v4.py",
            "app/core/adaptive_strategies.py",
            "app/core/strategies.py",
        ],
        compiler_directives={'language_level': "3"},
    ),
    cmdclass={'build_ext': build_ext},
)
"""
    setup_file = root / "setup_cython.py"
    setup_file.write_text(setup_content)
    
    # Compiler
    ok = run(f"cd {root} && python setup_cython.py build_ext --inplace")
    setup_file.unlink()
    
    if ok:
        print("✅ Fichiers critiques compilés en binaire (.pyd / .so)")
        print("   Le source Python original peut être supprimé du build final")
    else:
        print("⚠️  Échec Cython — fallback vers PyInstaller simple")
    
    return ok


def obfuscate_with_pyarmor():
    """
    Obfuscation avancée avec PyArmor.
    Le code devient illisible même avant compilation.
    """
    print_header("Obfuscation PyArmor")
    
    root = Path(__file__).parent
    dist_dir = root / "dist_pyarmor"
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # Obfusquer le package app/ entier
    ok = run(
        f"cd {root} && pyarmor gen --output dist_pyarmor/app "
        f"--recursive app/core/license_manager.py "
        f"app/core/anti_tamper.py "
        f"app/core/trading_engine_v4.py"
    )
    
    if ok:
        print("✅ Code obfusqué avec PyArmor")
        # Remplacer les sources par les obfusqués
        for f in dist_dir.rglob("*.py"):
            rel = f.relative_to(dist_dir)
            target = root / rel
            if target.exists():
                shutil.copy2(f, target)
        print("   Sources originales remplacées par versions obfusquées")
    
    return ok


def build_exe():
    """
    Compile le projet en .exe standalone avec PyInstaller.
    """
    print_header("Compilation PyInstaller — .exe standalone")
    
    root = Path(__file__).parent
    spec_file = root / "SafeTrendBot.spec"
    
    # Créer le .spec si inexistant
    if not spec_file.exists():
        create_spec_file(root, spec_file)
    
    # Nettoyer les builds précédents
    for d in [root / "build", root / "dist"]:
        if d.exists():
            shutil.rmtree(d)
    
    # Lancer PyInstaller
    ok = run(f"cd {root} && pyinstaller SafeTrendBot.spec --clean -y")
    
    if not ok:
        print("❌ Échec compilation PyInstaller")
        return False
    
    # Vérifier le résultat
    exe_path = root / "dist" / "SafeTrendBot" / "SafeTrendBot.exe"
    if sys.platform != "win32":
        exe_path = root / "dist" / "SafeTrendBot" / "SafeTrendBot"
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ .exe généré: {exe_path}")
        print(f"   Taille: {size_mb:.1f} MB")
        
        # Créer un ZIP distribuable
        zip_name = f"SafeTrendBot_v5_{datetime.now().strftime('%Y%m%d')}"
        zip_path = root / "dist" / f"{zip_name}.zip"
        
        shutil.make_archive(
            str(zip_path.with_suffix('')),
            'zip',
            root / "dist",
            "SafeTrendBot"
        )
        print(f"✅ ZIP distribuable: {zip_path}")
        
        return True
    else:
        print("❌ .exe introuvable")
        return False


def create_spec_file(root: Path, spec_file: Path):
    """Crée le fichier .spec PyInstaller"""
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

ROOT = Path(r"{root}").resolve()

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "app"), "app"),
        (str(ROOT / "bot"), "bot"),
        (str(ROOT / "backtest"), "backtest"),
        (str(ROOT / "README.md"), "."),
        (str(ROOT / "requirements.txt"), "."),
    ],
    hiddenimports=[
        "app.core.trading_engine_v4",
        "app.core.license_manager",
        "app.core.anti_tamper",
        "app.core.regime_detector",
        "app.core.adaptive_strategies",
        "app.core.portfolio_manager",
        "app.core.performance_metrics",
        "app.core.strategies",
        "app.core.market_filters",
        "app.core.trade_journal",
        "app.core.paper_trading",
        "app.brokers.mt5_adapter",
        "app.brokers.ib_adapter",
        "app.brokers.crypto_adapter",
        "bot.telegram_alerts",
        "bot.economic_calendar",
        "bot.news_feed",
        "PyQt6.sip",
        "numpy.core._dtype_ctypes",
        "sklearn",
        "hmmlearn",
        "fastapi",
        "uvicorn",
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=["matplotlib.tests", "numpy.random._examples"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SafeTrendBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compression UPX si disponible
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = GUI (pas de console noire)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "icon.ico") if (ROOT / "icon.ico").exists() else None,
)

# Single directory (pas one-file, pour des performances)
# Si tu veux un seul fichier .exe, remplace par:
# coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, ...)
'''
    spec_file.write_text(spec_content)
    print(f"✅ Fichier .spec créé: {spec_file}")


def main():
    print_header("SafeTrendBot V5 — Build .exe Standalone")
    
    if not check_tools():
        print("\nInstallez les outils manquants:")
        print("  pip install pyinstaller cython pyarmor")
        sys.exit(1)
    
    # Option A: Obfuscation Cython (recommandé)
    cython_ok = obfuscate_with_cython()
    
    # Option B: Si Cython échoue, essayer PyArmor
    if not cython_ok:
        pyarmor_ok = obfuscate_with_pyarmor()
    
    # Compilation finale
    build_exe()
    
    print_header("Build terminé")
    print("""
Le .exe est dans: dist/SafeTrendBot/

⚠️  IMPORTANT — Sécurité:
1. Supprimez les fichiers .py sources critiques AVANT distribution
   (license_manager.py, trading_engine_v4.py, anti_tamper.py)
   Seuls les .pyd/.so compilés doivent rester.

2. Changez la SECRET_KEY dans license_manager.py avant build!

3. Testez le .exe sur une machine vierge (sans Python installé).

4. Pour distribution: utilisez le ZIP dans dist/
""")


if __name__ == "__main__":
    main()
