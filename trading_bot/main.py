"""
SafeTrendBot — Point d'entrée principal
========================================
"""

import sys
import os
import argparse
from pathlib import Path

# Ajouter le path pour imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.license_manager import LicenseManager, auto_activate, LicenseStatus
from app.core.trading_engine import TradingEngine


def check_license():
    """Vérifie la licence au démarrage."""
    lm = LicenseManager()
    status = lm.check_license(verbose=True)
    
    if status != LicenseStatus.VALID:
        print(f"\n{'='*60}")
        print("  ❌ LICENCE NON VALIDE")
        print(f"  Statut: {status.name}")
        print("="*60)
        
        if status == LicenseStatus.NOT_ACTIVATED:
            print("\n  Tentative d'activation automatique...")
            success, msg = auto_activate()
            if success:
                print(f"  ✅ {msg}")
                print("  Redémarrez l'application.")
                return False
        
        return False
    
    print("\n  ✅ Licence validée — SafeTrendBot est prêt!\n")
    return True


def run_gui():
    """Lance l'interface graphique."""
    try:
        from app.ui.main_window import MainWindow
        import tkinter as tk
        
        if not check_license():
            sys.exit(1)
        
        root = tk.Tk()
        root.title("SafeTrendBot V5")
        app = MainWindow(root)
        root.mainloop()
        
    except ImportError as e:
        print(f"Erreur import GUI: {e}")
        print("L'interface graphique nécessite tkinter.")
        print("Lancez en mode headless: python main.py --headless")
        sys.exit(1)


def run_headless():
    """Lance en mode headless (sans GUI)."""
    if not check_license():
        sys.exit(1)
    
    print("\n🚀 SafeTrendBot — Mode Headless")
    print("-" * 40)
    
    engine = TradingEngine()
    engine.start()
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Arrêt du bot...")
        engine.stop()


def main():
    parser = argparse.ArgumentParser(description="SafeTrendBot Trading Bot")
    parser.add_argument("--headless", action="store_true", help="Mode sans GUI")
    parser.add_argument("--config", type=str, help="Fichier de config")
    parser.add_argument("--license-info", action="store_true", help="Affiche info licence")
    parser.add_argument("--activate", metavar="KEY", help="Active avec clé")
    
    args = parser.parse_args()
    
    # Mode info licence
    if args.license_info:
        lm = LicenseManager()
        info = lm.get_info()
        print("\n🔑 Informations Licence:")
        print(f"   Statut: {info['status']}")
        print(f"   Valide: {info['valid']}")
        if info.get('email'):
            print(f"   Email: {info['email']}")
        print(f"   HW ID: {info.get('hwid_short', 'N/A')}")
        print(f"   Expire: {info.get('expires', 'Jamais')}")
        return
    
    # Activation manuelle
    if args.activate:
        lm = LicenseManager()
        success, msg = lm.activate(args.activate)
        print(f"{'✅' if success else '❌'} {msg}")
        return
    
    # Lancement normal
    if args.headless:
        run_headless()
    else:
        run_gui()


if __name__ == "__main__":
    main()