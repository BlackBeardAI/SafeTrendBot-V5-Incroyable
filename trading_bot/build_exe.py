#!/usr/bin/env python3
"""
Générateur de build .exe portable pour SafeTrendBot V5.
=========================================================
Crée un .exe standalone (portable) — aucun Python requis sur le PC client.

Usage:
    # Générer une clé de licence et l'afficher
    python build_exe.py --generate

    # Build avec génération automatique de clé (.exe portable)
    python build_exe.py --generate --build

    # Build avec une clé spécifique
    python build_exe.py --key STB5-XXXX-XXXX-XXXX --build

Le .exe final est dans dist/SafeTrendBot.exe (Windows) ou dist/SafeTrendBot (Linux).
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
BUILD_DIR = ROOT / "build"

# Hidden imports critiques — PyInstaller ne les détecte pas toujours
HIDDEN_IMPORTS = [
    # PyQt6
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6._QOpenGLWidgets",
    # Core
    "app.core.bot_types",
    "app.core.config_manager",
    "app.core.trading_engine",
    "app.core.trading_engine_v4",
    "app.core.strategies",
    "app.core.license_manager",
    "app.core.anti_tamper",
    "app.core.extreme_guard",
    "app.core.encryption",
    "app.core.simple_license",
    "app.core.pin_lock",
    "app.core.paper_trading",
    "app.core.regime_detector",
    "app.core.adaptive_strategies",
    "app.core.portfolio_manager",
    "app.core.performance_metrics",
    "app.core.market_filters",
    "app.core.trade_journal",
    "app.core.historical_data",
    "app.core.market_hours",
    "app.core.csv_export",
    "app.core.pdf_reports",
    "app.core.parallel_backtest",
    "app.core.walk_forward",
    "app.core.smart_order_routing",
    "app.core.ml_regime_detector",
    "app.core.triple_screen",
    "app.core.symbol_circuit_breaker",
    "app.core.news_nlp",
    "app.core.broker_failover",
    "app.core.web_dashboard",
    "app.core.decision_journal",
    "app.core.prop_firm",
    "app.core.risk_off_manager",
    "app.core.auto_reporting",
    "app.core.multi_account",
    "app.core.slippage_learner",
    "app.core.auto_hedge",
    "app.core.voice_alerts",
    "app.core.trading_profiles",
    "app.core.recommendations",
    "app.core.position_calculator",
    # Brokers
    "app.brokers.broker_adapter",
    "app.brokers.mt5_adapter",
    "app.brokers.ctrader_adapter",
    "app.brokers.xtb_adapter",
    "app.brokers.crypto_adapter",
    "app.brokers.factory",
    # UI
    "app.ui.main_window",
    "app.ui.theme",
    "app.ui.widgets",
    "app.ui.widgets_status",
    "app.ui.equity_chart",
    "app.ui.signal_monitor",
    "app.ui.pin_lock_dialog",
    "app.ui.onboarding_wizard",
    # UI Views
    "app.ui.views.dashboard_view",
    "app.ui.views.positions_view",
    "app.ui.views.backtest_view",
    "app.ui.views.settings_view",
    "app.ui.views.broker_view",
    "app.ui.views.analytics_view",
    "app.ui.views.logs_view",
    "app.ui.views.paper_trading_view",
    "app.ui.views.calendar_view",
    "app.ui.views.news_view",
    "app.ui.views.telegram_view",
    "app.ui.views.market_hours_view",
    "app.ui.views.profiles_view",
    "app.ui.views.trend_analysis_view",
    "app.ui.views.tools_view",
    "app.ui.views.watchlist_view",
    "app.ui.views.recommendations_view",
    "app.ui.views.strategy_params_view",
    # Bot
    "bot.telegram_alerts",
    "bot.news_feed",
    "bot.economic_calendar",
    # Backtest
    "backtest.backtest",
    # License
    "app.core.__license_embed__",
]

# Modules à exclure (gain de taille)
EXCLUDES = [
    "tkinter",
    "pytest",
    "pyarmor",
    "cython",
    "flask",
    "flask_cors",
    "unittest",
    "test",
    "tests",
]


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
    _write_embed_file(PLACEHOLDER)
    embed_key_in_build(str(EMBED_FILE), key)
    print(f"[OK] Clé injectée dans {EMBED_FILE.name}")


def _write_embed_file(value: str) -> None:
    """Écrit le fichier __license_embed__.py avec la valeur donnée."""
    EMBED_FILE.write_text(
        '"""Fichier d\'embedding de clé de licence.\n\n'
        "Généré automatiquement par build_exe.py.\n"
        '"""\n\n'
        f'EMBEDDED_KEY = "{value}"\n',
        encoding="utf-8",
    )


def _restore_placeholder() -> None:
    """Restaure le fichier embedded avec le placeholder."""
    _write_embed_file(PLACEHOLDER)


def _generate_spec(key: str) -> Path:
    """Génère un fichier .spec pour PyInstaller avec tous les hidden-imports."""
    spec_path = ROOT / "SafeTrendBot.spec"

    hidden_str = "\n        ".join(f'"{m}",' for m in HIDDEN_IMPORTS)
    exclude_str = "\n        ".join(f'"{m}",' for m in EXCLUDES)

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Auto-généré par build_exe.py — NE PAS MODIFIER MANUELLEMENT

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        {hidden_str}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        {exclude_str}
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SafeTrendBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)
'''
    spec_path.write_text(spec_content, encoding="utf-8")
    print(f"[OK] Spec généré: {spec_path.name}")
    return spec_path


def cmd_build(key: str) -> int:
    """Build le .exe portable avec la clé donnée."""
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

    # Vérifier PyInstaller
    try:
        import PyInstaller  # noqa
    except ImportError:
        print("[ERREUR] PyInstaller non installé. Installez avec: pip install pyinstaller")
        return 1

    # Nettoyer les anciens builds
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    # 1. Injecter la clé
    _inject_key(key)

    try:
        # 2. Générer le .spec
        spec_path = _generate_spec(key)

        # 3. Lancer PyInstaller avec le .spec
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(spec_path),
            "--noconfirm",
            "--clean",
            "--distpath", str(DIST_DIR),
            "--workpath", str(BUILD_DIR),
        ]

        print(f"[INFO] Lancement du build...")
        print(f"[INFO] Cela peut prendre 5-10 minutes...")
        result = subprocess.run(cmd, cwd=str(ROOT))

        if result.returncode != 0:
            print("[ERREUR] Build PyInstaller échoué.")
            return result.returncode

        # Vérifier le résultat
        exe_path = DIST_DIR / f"{EXE_NAME}.exe"
        bin_path = DIST_DIR / EXE_NAME

        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1024 / 1024
            print(f"\n[OK] .exe généré: {exe_path}")
            print(f"     Taille: {size_mb:.1f} MB")
            return 0
        elif bin_path.exists():
            size_mb = bin_path.stat().st_size / 1024 / 1024
            print(f"\n[OK] Binaire généré: {bin_path}")
            print(f"     Taille: {size_mb:.1f} MB")
            return 0
        else:
            print(f"[ERREUR] Fichier de sortie non trouvé dans {DIST_DIR}")
            return 1

    finally:
        # 4. Restaurer le placeholder
        _restore_placeholder()
        print("[INFO] Placeholder restauré dans __license_embed__.py")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build .exe portable SafeTrendBot V5 avec licence embedded"
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

    if key is None and not args.generate:
        parser.print_help()
        return 1

    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())