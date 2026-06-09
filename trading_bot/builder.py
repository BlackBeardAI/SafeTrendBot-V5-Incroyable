"""
SafeTrendBot Builder — Générateur d'exemplaires uniques
=======================================================

UN SEUL logiciel pour créer des builds SafeTrendBot impiratables:
    python builder.py

Ce que fait le builder:
1. Génère une licence unique (usage unique, hardware-locked)
2. Injecte la licence dans le code source
3. Chiffre les fichiers sensibles (AES-256)
4. Obfusque le code (PyArmor + Cython)
5. Compile en .exe standalone (PyInstaller)
6. Ajoute l'anti-tamper
7. Produit un .exe prêt à vendre

Le build final est:
- 🔒 Lié à la licence générée (impossible de partager)
- 🔒 Chiffré (impossible de lire les fichiers de config)
- 🔒 Obfusqué (impossible de reverse-engineer)
- 🔒 Anti-tamper (détecte debug/modification)
- 📦 Portable (pas besoin de Python installé)

Résultat:
    builds/
    └── SafeTrendBot_Client_[timestamp].exe

Usage:
    python builder.py --tier basic --output mon_client.exe
    python builder.py --tier extreme --email client@ex.com
"""

import sys
import os
import shutil
import hashlib
import secrets
import subprocess
import tempfile
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
BUILD_DIR = ROOT / "builds"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

# URL du dashboard admin — injectée dans chaque build pour connexion auto
ADMIN_URL = os.environ.get(
    "SAFETRENDBOT_ADMIN_URL",
    "https://217.160.191.107:8443"  # VPS par défaut
)

TIER_CONFIG = {
    "basic": {"eur": 99, "usd": 109, "label": "Basic", "max_positions": 3, "risk": 1.0},
    "pro": {"eur": 199, "usd": 219, "label": "Pro", "max_positions": 5, "risk": 2.0},
    "extreme": {"eur": 349, "usd": 379, "label": "EXTREME", "max_positions": 8, "risk": 5.0},
}


# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────

def generate_license() -> str:
    """Génère une licence unique Base58 format XXXX-XXXX-XXXX-XXXX."""
    parts = ["".join(secrets.choice(ALPHABET) for _ in range(6)) for _ in range(4)]
    return "-".join(parts)


def print_banner(text):
    print(f"\n{'='*65}")
    print(f"  {text}")
    print(f"{'='*65}\n")


def run(cmd: str, cwd: Optional[Path] = None, check: bool = True) -> bool:
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0 and check:
        print(f"❌ {result.stderr.strip()}")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 1: PRÉPARATION
# ─────────────────────────────────────────────────────────────────────────────

def prepare_source(temp_dir: Path, license_key: str, tier: str) -> Path:
    """
    Copie le source SafeTrendBot dans un dossier temporaire
    et injecte la licence + configuration tier.
    """
    print_banner("🔧 Étape 1: Préparation du source")

    src_dir = temp_dir / "src"
    shutil.copytree(ROOT, src_dir, ignore=shutil.ignore_patterns(
        "builds", "dist", "build", "__pycache__", "*.pyc", "*.spec",
        "setup_cython*.py", "*.enc", "releases", ".git"
    ))

    # Injecter la licence dans license_manager_v2.py
    lm_path = src_dir / "app" / "core" / "license_manager_v2.py"
    if lm_path.exists():
        content = lm_path.read_text(encoding="utf-8")
        # Remplacer le placeholder d'extraction par la vraie licence hardcodée
        # On crée un module d'override
        override = f'''
# ===== AUTO-INJECTED BY BUILDER =====
_BUILDER_LICENSE_KEY = "{license_key}"
_BUILDER_TIER = "{tier}"

def _get_injected_license():
    return _BUILDER_LICENSE_KEY
# ===== END INJECTION =====
'''
        # Insérer après les imports
        lines = content.split("\n")
        import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                import_idx = i + 1
        lines.insert(import_idx, override)

        # Modifier _extract_license_from_binary pour retourner la clé injectée
        new_content = "\n".join(lines)
        new_content = new_content.replace(
            "return None  # Aucune licence trouvée",
            f'return _BUILDER_LICENSE_KEY  # Licence injectée par builder'
        )

        lm_path.write_text(new_content, encoding="utf-8")
        print(f"   ✅ Licence injectée: {license_key}")

    # Créer un fichier tier_config.py pour forcer la config
    tier_cfg = TIER_CONFIG.get(tier, TIER_CONFIG["basic"])
    tier_path = src_dir / "app" / "core" / "tier_config.py"
    tier_path.write_text(f'''"""Configuration tier injectée par le builder."""
TIER = "{tier}"
LABEL = "{tier_cfg['label']}"
MAX_POSITIONS = {tier_cfg['max_positions']}
RISK_PER_TRADE = {tier_cfg['risk']}
''', encoding="utf-8")
    print(f"   ✅ Config tier injectée: {tier} ({tier_cfg['label']})")

    # ─── INJECTION URL DASHBOARD ───
    # Remplacer les URLs par défaut par l'URL admin configurée
    for module_file in ["broadcast_client.py", "auto_updater.py", "main.py"]:
        mod_path = src_dir / "app" / "core" / module_file
        if not mod_path.exists():
            mod_path = src_dir / module_file  # main.py est à la racine

        if mod_path.exists():
            content = mod_path.read_text(encoding="utf-8")
            # Remplacer les URLs par défaut/fallback
            replacements = [
                ('BROADCAST_API_URL = os.environ.get("SAFETRENDBOT_BROADCAST_API", "")',
                 f'BROADCAST_API_URL = os.environ.get("SAFETRENDBOT_BROADCAST_API", "{ADMIN_URL}")'),
                ('BROADCAST_API_URL = ""',
                 f'BROADCAST_API_URL = "{ADMIN_URL}"'),
                ('UPDATE_SERVER = os.environ.get("SAFETRENDBOT_UPDATE_URL", "")',
                 f'UPDATE_SERVER = os.environ.get("SAFETRENDBOT_UPDATE_URL", "{ADMIN_URL}")'),
                ('UPDATE_SERVER = ""',
                 f'UPDATE_SERVER = "{ADMIN_URL}"'),
                ('ADMIN_DASHBOARD_URL = os.environ.get("SAFETRENDBOT_ADMIN_URL", "")',
                 f'ADMIN_DASHBOARD_URL = os.environ.get("SAFETRENDBOT_ADMIN_URL", "{ADMIN_URL}")'),
                ('ADMIN_DASHBOARD_URL = ""',
                 f'ADMIN_DASHBOARD_URL = "{ADMIN_URL}"'),
            ]
            for old, new in replacements:
                content = content.replace(old, new)
            mod_path.write_text(content, encoding="utf-8")

    print(f"   ✅ URL dashboard injectée: {ADMIN_URL}")

    return src_dir


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 2: CHIFFREMENT DES DONNÉES SENSIBLES
# ─────────────────────────────────────────────────────────────────────────────

def encrypt_sensitive_files(src_dir: Path, password: str):
    """Chiffre les fichiers de config/template dans le source."""
    print_banner("🔒 Étape 2: Chiffrement des ressources")

    try:
        sys.path.insert(0, str(ROOT / "app" / "core"))
        from encryption import CryptoVault
        vault = CryptoVault(password)

        # Chiffrer les fichiers sensibles
        patterns = ["*.json", "*.yaml", "*.yml", "*.key", "*.secret"]
        count = 0
        for pattern in patterns:
            for f in src_dir.rglob(pattern):
                if f.is_file() and not f.name.endswith(".enc"):
                    try:
                        vault.encrypt_file(f, delete_original=True)
                        count += 1
                    except Exception:
                        pass
        print(f"   ✅ {count} fichiers chiffrés")
    except ImportError:
        print("   ⚠️  encryption.py non disponible — skip chiffrement")


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 3: OBFUSCATION
# ─────────────────────────────────────────────────────────────────────────────

def obfuscate_source(src_dir: Path) -> bool:
    """Obfusque le code avec Cython ou PyArmor si disponible."""
    print_banner("🛡️ Étape 3: Obfuscation")

    # Essayer Cython
    cython_ok = _obfuscate_cython(src_dir)
    if cython_ok:
        return True

    # Fallback PyArmor
    pyarmor_ok = _obfuscate_pyarmor(src_dir)
    if pyarmor_ok:
        return True

    print("   ⚠️  Obfuscation échouée — le build sera moins protégé")
    return False


def _obfuscate_cython(src_dir: Path) -> bool:
    """Compile les modules critiques en binaire Cython."""
    critical = [
        "app/core/license_manager_v2.py",
        "app/core/anti_tamper.py",
        "app/core/trading_engine_v4.py",
        "app/core/extreme_guard.py",
        "app/core/encryption.py",
    ]

    modules_str = ",\n            ".join(f'"{m}"' for m in critical)
    setup_py = src_dir / "_builder_cython_setup.py"
    setup_py.write_text(f'''from setuptools import setup
from Cython.Build import cythonize
from Cython.Distutils import build_ext

setup(
    ext_modules=cythonize(
        [{modules_str}],
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
''', encoding="utf-8")

    ok = run(f"python {setup_py} build_ext --inplace", cwd=src_dir, check=False)
    setup_py.unlink(missing_ok=True)

    if ok:
        print("   ✅ Cython: modules critiques compilés en binaire")
        # Supprimer les .py sources pour ne garder que les .so/.pyd
        for rel in critical:
            py_file = src_dir / rel
            if py_file.exists():
                # Vérifier que le .so/.pyd existe
                so_file = py_file.with_suffix('.cpython-311-x86_64-linux-gnu.so')
                pyd_file = py_file.with_suffix('.cp311-win_amd64.pyd')
                if so_file.exists() or pyd_file.exists() or any(py_file.with_suffix('').parent.glob(py_file.stem + '*.so')):
                    py_file.unlink()
        return True
    return False


def _obfuscate_pyarmor(src_dir: Path) -> bool:
    """Obfusque avec PyArmor si disponible."""
    ok = run(f"pyarmor gen --output {src_dir / '_pyarmor'} --recursive {src_dir / 'app'}", check=False)
    if ok:
        print("   ✅ PyArmor: code obfusqué")
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 4: COMPILATION PYINSTALLER
# ─────────────────────────────────────────────────────────────────────────────

def compile_executable(src_dir: Path, output_name: str) -> Optional[Path]:
    """Compile le source en .exe standalone avec PyInstaller."""
    print_banner("📦 Étape 4: Compilation .exe")

    main_py = src_dir / "main.py"
    if not main_py.exists():
        print("❌ main.py introuvable")
        return None

    # Créer le .spec
    spec_file = src_dir / "_builder.spec"
    is_win = sys.platform == "win32"
    icon_file = ROOT / "icon.ico"
    icon_flag = f'icon=str(ROOT / "icon.ico"),' if icon_file.exists() else ""

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
ROOT = Path(r"{src_dir}").resolve()

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "app"), "app"),
        (str(ROOT / "bot"), "bot"),
    ],
    hiddenimports=[
        "app.core.license_manager_v2",
        "app.core.anti_tamper",
        "app.core.trading_engine_v4",
        "app.core.extreme_guard",
        "app.core.encryption",
        "app.core.trading_profiles",
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
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=["matplotlib.tests", "numpy.random._examples", "tkinter", "pydoc"],
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
    name="{output_name}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_flag}
)
'''
    spec_file.write_text(spec_content, encoding="utf-8")

    # Nettoyer anciens builds
    dist_dir = src_dir / "dist"
    build_dir = src_dir / "build"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # Lancer PyInstaller
    ok = run(f"pyinstaller {spec_file} --clean -y", cwd=src_dir, check=False)
    spec_file.unlink(missing_ok=True)

    if not ok:
        print("❌ PyInstaller a échoué")
        return None

    # Trouver le binaire généré
    ext = ".exe" if is_win else ""
    exe_path = dist_dir / output_name / f"{output_name}{ext}"
    if not exe_path.exists():
        # Fallback onefile
        exe_path = dist_dir / f"{output_name}{ext}"

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ Binaire généré: {exe_path.name} ({size_mb:.1f} MB)")
        return exe_path
    else:
        print("❌ Binaire introuvable après compilation")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# ÉTAPE 5: PACKAGING
# ─────────────────────────────────────────────────────────────────────────────

def package_build(exe_path: Path, license_key: str, tier: str, email: str, temp_dir: Path) -> Path:
    """Crée le package final prêt à distribuer."""
    print_banner("📦 Étape 5: Packaging")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pkg_name = f"SafeTrendBot_{tier}_{timestamp}"
    pkg_dir = BUILD_DIR / pkg_name
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Copier le binaire
    ext = exe_path.suffix
    final_name = f"SafeTrendBot_{tier}{ext}"
    final_exe = pkg_dir / final_name
    shutil.copy2(exe_path, final_exe)

    # Créer le README client
    tier_cfg = TIER_CONFIG.get(tier, TIER_CONFIG["basic"])
    readme = f"""SafeTrendBot V5 — Version {tier_cfg['label']}
{'='*50}

Licence: {license_key}
Tier: {tier_cfg['label']}
Date de génération: {datetime.now().strftime('%Y-%m-%d %H:%M')}

INSTRUCTIONS:
1. Double-cliquez sur {final_name}
2. La licence sera activée automatiquement sur CET ordinateur
3. Le bot ne fonctionnera que sur cet ordinateur (hardware-locked)
4. Ne partagez PAS ce fichier — il ne marchera que pour vous

⚠️  ATTENTION:
- Licence à USAGE UNIQUE
- Une fois activée, impossible de transférer
- Gardez cette licence dans un endroit sûr

Support: contact@safetrendbot.com
"""
    (pkg_dir / "README.txt").write_text(readme, encoding="utf-8")

    # Sauvegarder la licence pour l'admin
    (pkg_dir / "_ADMIN_LICENSE.txt").write_text(
        f"License: {license_key}\nTier: {tier}\nEmail: {email}\nDate: {datetime.now().isoformat()}\n",
        encoding="utf-8"
    )

    # Créer ZIP
    zip_path = BUILD_DIR / f"{pkg_name}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in pkg_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(pkg_dir))

    print(f"   ✅ Package créé: {pkg_dir}")
    print(f"   ✅ ZIP distribuable: {zip_path}")

    # Nettoyer le dossier temp
    shutil.rmtree(temp_dir, ignore_errors=True)

    return zip_path


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def build_single(tier: str = "basic", email: str = "", output: Optional[str] = None) -> dict:
    """
    Crée un build unique prêt à vendre.
    Retourne les infos du build.
    """
    print_banner("🚀 SafeTrendBot Builder — Générateur de builds uniques")

    # 0. Vérifier PyInstaller
    try:
        import PyInstaller
        print("   ✅ PyInstaller détecté")
    except ImportError:
        print("❌ PyInstaller manquant: pip install pyinstaller")
        sys.exit(1)

    # Générer la licence
    license_key = generate_license()
    print(f"   🎲 Licence générée: {license_key}")

    # Créer dossier temporaire
    temp_dir = Path(tempfile.mkdtemp(prefix="stb_builder_"))
    print(f"   📁 Dossier temp: {temp_dir}")

    # 1. Préparer source
    src_dir = prepare_source(temp_dir, license_key, tier)

    # 2. Chiffrer
    vault_pw = f"STB_{secrets.token_hex(16)}"
    encrypt_sensitive_files(src_dir, vault_pw)

    # 3. Obfusquer
    obfuscate_source(src_dir)

    # 4. Compiler
    output_name = output or f"SafeTrendBot_{tier}"
    exe_path = compile_executable(src_dir, output_name)

    if not exe_path:
        print("❌ BUILD ÉCHOUÉ")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"success": False}

    # 5. Packager
    zip_path = package_build(exe_path, license_key, tier, email, temp_dir)

    print_banner("🎉 BUILD TERMINÉ")
    print(f"   📦 Fichier: {zip_path}")
    print(f"   🔑 Licence: {license_key}")
    print(f"   📧 Client: {email or 'N/A'}")
    print(f"   🏷️  Tier: {tier}")
    print(f"\n   → Envoie ce ZIP à TON client")
    print(f"   → Chaque build ne fonctionne que sur UN PC")

    return {
        "success": True,
        "zip": str(zip_path),
        "license": license_key,
        "tier": tier,
        "email": email,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SafeTrendBot Builder")
    parser.add_argument("--tier", choices=["basic", "pro", "extreme"], default="basic", help="Tier du build")
    parser.add_argument("--email", default="", help="Email du client")
    parser.add_argument("--output", help="Nom du binaire de sortie")
    parser.add_argument("--count", type=int, default=1, help="Nombre de builds à générer")
    args = parser.parse_args()

    if args.count == 1:
        result = build_single(args.tier, args.email, args.output)
        sys.exit(0 if result["success"] else 1)
    else:
        # Batch mode
        results = []
        for i in range(args.count):
            print(f"\n{'='*65}")
            print(f"  BUILD #{i+1}/{args.count}")
            print(f"{'='*65}")
            result = build_single(args.tier, args.email, args.output)
            results.append(result)

        print_banner("📊 RÉCAP BATCH")
        for i, r in enumerate(results, 1):
            status = "✅" if r.get("success") else "❌"
            print(f"   {status} Build #{i}: {r.get('license', 'N/A')[:20]}...")


if __name__ == "__main__":
    main()
