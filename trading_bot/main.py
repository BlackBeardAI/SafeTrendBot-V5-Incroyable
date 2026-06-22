#!/usr/bin/env python3
"""
SafeTrendBot V5 — Point d'entrée principal
============================================
Lance l'interface desktop PyQt6 complète.

Licence: si une clé embedded est présente (≠ "__EMBEDDED_KEY__"), elle est
validée au démarrage. Si invalide → dialog + exit. Sinon mode libre.
"""

import sys
import os
from pathlib import Path

# Ajouter le path pour imports
sys.path.insert(0, str(Path(__file__).parent))

PLACEHOLDER = "__EMBEDDED_KEY__"


def check_license() -> bool:
    """Vérifie la licence embedded au démarrage.

    Returns:
        True si on peut continuer (mode libre ou clé valide),
        False si clé présente mais invalide.
    """
    try:
        from app.core.__license_embed__ import EMBEDDED_KEY
    except Exception:
        # Fichier d'embedding absent → mode libre
        return True

    # Mode libre si placeholder
    if EMBEDDED_KEY == PLACEHOLDER or not EMBEDDED_KEY:
        print("[LICENCE] Mode libre (pas de clé embedded)")
        return True

    # Clé présente → validation
    from app.core.simple_license import SimpleLicense
    lic = SimpleLicense(EMBEDDED_KEY)
    if lic.validate():
        print(f"[LICENCE] Clé valide: {lic.get_key()}")
        return True

    print(f"[LICENCE] Clé invalide: {EMBEDDED_KEY}")
    return False


def show_license_error_dialog() -> None:
    """Affiche une boîte de dialogue 'Clé de licence invalide' et quitte."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
    except ImportError:
        # Pas de PyQt6 → message console
        print("[ERREUR] Clé de licence invalide. Contactez le support.")
        return

    app = QApplication.instance() or QApplication(sys.argv)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("SafeTrendBot V5 — Licence")
    msg.setText("Clé de licence invalide")
    msg.setInformativeText(
        "La clé de licence intégrée à cette version est invalide.\n"
        "Contactez le support pour obtenir une clé valide."
    )
    msg.exec()

# Forcer high-DPI avant création QApplication
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║   ███████╗ ██████╗██╗  ██╗ ██████╗ ███████╗███████╗██████╗         ║
║   ██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝██╔════╝██╔══██╗        ║
║   █████╗  ╚█████╗ ███████║██║   ██║█████╗  ███████╗██████╔╝        ║
║   ██╔══╝   ╚═══██╗██╔══██║██║   ██║██╔══╝  ╚════██║██╔══██╗        ║
║   ███████╗██████╔╝██║  ██║╚██████╔╝███████╗███████║██║  ██║        ║
║   ╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝        ║
║                   Trading Bot Intelligent — V5                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def run_gui():
    """Lance l'interface graphique PyQt6."""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
    except ImportError:
        print("[ERREUR] PyQt6 non installé")
        print("Installez avec: pip install PyQt6")
        print("Ou lancez en mode headless: python main.py --headless")
        return False

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SafeTrendBot V5")
    app.setOrganizationName("SafeTrendBot")

    # Police par défaut
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    from app.ui.main_window import MainWindow

    # Onboarding wizard au premier lancement
    # (si config.onboarding_completed == False)
    try:
        from app.ui.onboarding_wizard import run_onboarding_if_needed
        if not run_onboarding_if_needed():
            # L'utilisateur a annulé l'onboarding → on quitte
            print("[INFO] Onboarding annulé par l'utilisateur. Au revoir.")
            return True
    except Exception as e:
        print(f"[WARNING] Onboarding wizard indisponible: {e}")
        # On continue quand même vers MainWindow

    window = MainWindow(engine_version='v4')
    window.show()
    return app.exec() == 0


def run_headless():
    """Lance en mode serveur (sans GUI)."""
    print("\n🚀 Mode Headless — Serveur de Trading")
    print("-" * 50)
    print("[INFO] Démarrage du moteur de trading...")
    print("[INFO] Ctrl+C pour arrêter\n")

    try:
        from app.core.trading_engine_v4 import TradingEngineV4 as TradingEngine
        engine = TradingEngine()
        engine.start()
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Arrêt du bot...")
        engine.stop()
        print("[INFO] Bot arrêté")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SafeTrendBot V5")
    parser.add_argument("--headless", action="store_true",
                        help="Mode serveur (sans GUI)")
    parser.add_argument("--version", action="store_true",
                        help="Afficher la version")
    args = parser.parse_args()

    if args.version:
        print("SafeTrendBot V5.4.0")
        return

    print_banner()

    # Vérification de la licence (mode libre si placeholder)
    if not check_license():
        # Clé invalide → dialog + exit
        show_license_error_dialog()
        sys.exit(1)

    if args.headless:
        run_headless()
    else:
        run_gui()


if __name__ == "__main__":
    main()