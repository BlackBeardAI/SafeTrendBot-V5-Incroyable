#!/usr/bin/env python3
"""
SafeTrendBot V5 — Point d'entrée principal
Lance l'interface desktop PyQt6.
Aucune vérification de licence, aucun HW-lock, mode libre.
"""

import sys
import os
import traceback
from pathlib import Path

# Ajouter le path pour imports
sys.path.insert(0, str(Path(__file__).parent))

# Forcer high-DPI avant création QApplication
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


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
import logging

logger = logging.getLogger("main")


def show_error_dialog(title, message):
    """Affiche une boîte de dialogue d'erreur — même sans PyQt6."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()
    except Exception:
        # Fallback: tkinter si PyQt6 crash
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(title, message)
            root.destroy()
        except Exception:
            # Dernier recours: console
            print(f"\n[ERREUR] {title}\n{message}\n")
            input("Appuyez sur Entrée pour fermer...")


def check_dependencies():
    """Vérifie que les dépendances critiques sont installées."""
    missing = []
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        import pandas
    except ImportError:
        missing.append("pandas")
    return missing


def check_license():
    """Vérifie la licence simple (clé embedded)."""
    try:
        from app.core.__license_embed__ import EMBEDDED_KEY
        if EMBEDDED_KEY == "__EMBEDDED_KEY__":
            # Mode libre (pas de clé embedded)
            print("[LICENCE] Mode libre — aucune clé embedded")
            return True
        # Clé embedded → valider
        from app.core.simple_license import SimpleLicense
        lic = SimpleLicense(EMBEDDED_KEY)
        if lic.validate():
            logger.info(f"[LICENCE] Clé valide: {EMBEDDED_KEY}")
            return True
        else:
            logger.info(f"[LICENCE] Clé invalide: {EMBEDDED_KEY}")
            show_error_dialog(
                "Clé de licence invalide",
                f"La clé de licence intégrée dans cette version est invalide.\n\n"
                f"Clé: {EMBEDDED_KEY}\n\n"
                f"Contactez le support: @BlackBeardAI sur Telegram"
            )
            return False
    except Exception as e:
        logger.warning(f"[LICENCE] Erreur vérification: {e}")
        # En cas d'erreur, on laisse passer (mode libre)
        return True


def run_gui():
    """Lance l'interface graphique PyQt6."""
    # 1. Vérifier les dépendances
    missing = check_dependencies()
    if missing:
        show_error_dialog(
            "Dépendances manquantes",
            f"Les modules suivants ne sont pas installés:\n\n"
            f"{', '.join(missing)}\n\n"
            f"Installez-les avec:\n"
            f"pip install {' '.join(missing)}\n\n"
            f"Ou relancez INSTALL_WINDOWS.bat"
        )
        return False

    # 2. Vérifier la licence
    if not check_license():
        return False

    # 3. Lancer PyQt6
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
    except Exception as e:
        show_error_dialog(
            "Erreur PyQt6",
            f"Impossible d'initialiser PyQt6:\n\n{e}\n\n"
            f"Essayez: pip install --upgrade PyQt6"
        )
        return False

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SafeTrendBot V5")
    app.setOrganizationName("SafeTrendBot")

    # Police par défaut
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # 4. Onboarding wizard si premier lancement
    try:
        from app.core.config_manager import config_manager
        if not config_manager.config.onboarding_completed:
            try:
                from app.ui.onboarding_wizard import run_onboarding_if_needed
                run_onboarding_if_needed()
            except Exception as e:
                logger.warning(f"[WARN] Onboarding non disponible: {e}")
    except Exception as e:
        logger.warning(f"[WARN] Config onboarding: {e}")

    # 5. Fenêtre principale
    try:
        from app.ui.main_window import MainWindow
        window = MainWindow(engine_version='v4')
        window.show()
        return app.exec() == 0
    except Exception as e:
        tb = traceback.format_exc()
        show_error_dialog(
            "Erreur au démarrage",
            f"SafeTrendBot n'a pas pu démarrer:\n\n{e}\n\n"
            f"Détails:\n{tb[:500]}\n\n"
            f"Contactez @BlackBeardAI sur Telegram"
        )
        return False


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
        print("SafeTrendBot V5.4.0 — Mode Libre")
        return

    print_banner()

    if args.headless:
        run_headless()
    else:
        run_gui()


if __name__ == "__main__":
    main()