#!/usr/bin/env python3
"""
SafeTrendBot V5 — Point d'entrée principal
============================================
Lance l'interface desktop PyQt6 complète.
Aucune vérification de licence, aucun HW-lock, mode libre.
"""

import sys
import os
from pathlib import Path

# Ajouter le path pour imports
sys.path.insert(0, str(Path(__file__).parent))

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
        from app.core.trading_engine import TradingEngine
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
        print("SafeTrendBot V5.4.0 — Mode Libre")
        return

    print_banner()

    if args.headless:
        run_headless()
    else:
        run_gui()


if __name__ == "__main__":
    main()