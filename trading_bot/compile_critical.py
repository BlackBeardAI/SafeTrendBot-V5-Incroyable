"""
Compile les fichiers critiques en modules binaires (.pyd / .so).
Le source Python devient illisible — impossible à décompiler.
"""
import sys
import os
import shutil
from pathlib import Path
from Cython.Build import cythonize
from distutils.core import setup
from distutils.extension import Extension


def compile_critical_files():
    root = Path(__file__).parent
    
    # Liste des fichiers CRITIQUES à compiler
    # Ces fichiers seront transformés en DLL binaires
    CRITICAL = [
        "app/core/license_manager.py",
        "app/core/anti_tamper.py",
        "app/core/trading_engine_v4.py",
        "app/core/adaptive_strategies.py",
        "app/core/regime_detector.py",
        "app/core/strategies.py",
    ]
    
    # Créer un setup temporaire
    extensions = []
    for rel_path in CRITICAL:
        full_path = str(root / rel_path)
        module_name = rel_path.replace('/', '.').replace('.py', '')
        ext = Extension(
            module_name,
            [full_path],
            extra_compile_args=["-O3"],  # Optimisation max
        )
        extensions.append(ext)
    
    # Compiler
    print("🔒 Compilation Cython des fichiers critiques en binaire...")
    print("   Cela transforme le Python en code machine (.pyd / .so)")
    print("   Le source original devient illisible.")
    print()
    
    ext_modules = cythonize(
        extensions,
        compiler_directives={'language_level': "3"},
        annotate=False,
    )
    
    setup(
        name="SafeTrendBot_Critical",
        ext_modules=ext_modules,
        script_args=["build_ext", "--inplace"],
    )
    
    # Supprimer les .py sources? Non — les garder pour le dev
    # Mais pour la distribution, on garde SEULEMENT les .pyd/.so
    print()
    print("✅ Compilation terminée")
    
    # Vérifier les fichiers générés
    for rel_path in CRITICAL:
        base = (root / rel_path).with_suffix('')
        if sys.platform == "win32":
            compiled = base.with_suffix('.cpython-311-x86_64-linux-gnu.pyd')
            if not compiled.exists():
                compiled = root / (base.name + ".cp311-win_amd64.pyd")
        else:
            compiled = base.with_suffix('.cpython-311-x86_64-linux-gnu.so')
        
        if compiled.exists():
            size_kb = compiled.stat().st_size / 1024
            print(f"   ✅ {compiled.name} ({size_kb:.0f} KB)")
        else:
            print(f"   ⚠️  {rel_path}: fichier compilé introuvable")
    
    print()
    print("📦 POUR LA DISTRIBUTION:")
    print("   Gardez SEULEMENT les .pyd / .so")
    print("   SUPPRIMEZ les .py sources des fichiers critiques!")
    print("   Le .exe PyInstaller incluera automatiquement les binaires.")


if __name__ == "__main__":
    compile_critical_files()
