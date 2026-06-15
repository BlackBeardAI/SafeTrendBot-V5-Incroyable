"""
SafeTrendBot V5 — Point d'entrée principal
============================================

🎯 Sécurité maximale:
- Vérification licence au démarrage
- Hardware lock anti-copie
- Auto-destruct si crack détecté
"""

import sys
import os
from pathlib import Path

# Ajouter le path pour imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.license_manager import (
    LicenseManager, LicenseStatus, auto_first_activation
)
from app.core.trading_engine import TradingEngine


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "SafeTrendBot V5.3.0"
CONFIG_DIR = Path.home() / ".safetrendbot"
LOG_FILE = CONFIG_DIR / "bot.log"


def print_banner():
    """Affiche la bannière du bot."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   ███████╗ ██████╗██╗  ██╗ ██████╗ ███████╗███████╗██████╗         ║
║   ██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝██╔════╝██╔══██╗        ║
║   █████╗  ╚█████╗ ███████║██║   ██║█████╗  ███████╗██████╔╝        ║
║   ██╔══╝   ╚═══██╗██╔══██║██║   ██║██╔══╝  ╚════██║██╔══██╗        ║
║   ███████╗██████╔╝██║  ██║╚██████╔╝███████╗███████║██║  ██║        ║
║   ╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝        ║
║                                                                      ║
║                    Trading Bot Intelligent                           ║
║                    Version 5.3.0                                    ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def check_license(verbose: bool = True) -> bool:
    """
    Vérifie la licence au démarrage.
    Retourne True si accès autorisé, False sinon.
    """
    if verbose:
        print("[SÉCURITÉ] Vérification de la licence...")
    
    lm = LicenseManager()
    
    # Première activation?
    status, msg = lm.validate()
    
    if status == LicenseStatus.NOT_ACTIVATED:
        if verbose:
            print(f"[INFO] {msg}")
            print("[INFO] Tentative d'activation automatique...")
        
        # Essayer auto-activation avec clé embarquée
        success, act_msg = auto_first_activation()
        
        if success:
            if verbose:
                print(f"[✅] {act_msg}")
            return True
        else:
            if verbose:
                print(f"[❌] Activation échouée: {act_msg}")
            return False
    
    elif status == LicenseStatus.VALID:
        if verbose:
            info = lm.get_info()
            print(f"[✅] Licence valide")
            print(f"     HW-ID: {info.get('hw_id_short', 'N/A')}")
            print(f"     Activé: {info.get('activated_at', 'N/A')[:10]}")
        return True
    
    else:
        if verbose:
            print(f"[❌] ACCÈS REFUSÉ")
            print(f"     Raison: {msg}")
            print()
            
            if status == LicenseStatus.HARDWARE_MISMATCH:
                print("     ⚠️  Ce PC ne correspond pas à l'activation initiale.")
                print("     → La licence est liée à un autre ordinateur.")
                print("     → Contactez le support pour transfert.")
            elif status == LicenseStatus.TAMPERED:
                print("     🚫 INTÉGRITÉ COMPROMISE")
                print("     → Tentative de manipulation détectée")
                print("     → Toutes les données ont été effacées")
            elif status == LicenseStatus.VM_DETECTED:
                print("     🚫 Machine virtuelle détectée")
                print("     → Lancez sur un PC réel pour utiliser le bot")
            elif status == LicenseStatus.DEBUG_DETECTED:
                print("     🚫 Débogage détecté")
                print("     → Fermez votre débogueur et relancez")
            else:
                print(f"     → Statut: {status.value}")
        
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFACE GRAPHIQUE (Tkinter)
# ═══════════════════════════════════════════════════════════════════════════════

def run_gui():
    """Lance l'interface graphique."""
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        print("[ERREUR] Tkinter non disponible")
        print("Lancez en mode headless: python main.py --headless")
        return False
    
    # Fenêtre principale
    root = tk.Tk()
    root.title(f"{APP_NAME} - Interface de Trading")
    root.geometry("900x700")
    root.configure(bg='#1a1a2e')
    
    # Bannière
    banner = tk.Frame(root, bg='#16213e', pady=10)
    banner.pack(fill='x')
    
    tk.Label(
        banner, 
        text="SafeTrendBot V5", 
        font=('Arial', 24, 'bold'),
        fg='#00d9ff', 
        bg='#16213e'
    ).pack()
    
    tk.Label(
        banner,
        text="Bot de Trading Intelligent",
        font=('Arial', 12),
        fg='#888',
        bg='#16213e'
    ).pack()
    
    # Status licence
    status_frame = tk.Frame(root, bg='#1a1a2e', pady=20)
    status_frame.pack(fill='x', padx=20)
    
    lm = LicenseManager()
    info = lm.get_info()
    
    status_color = '#2ecc71' if info['valid'] else '#e74c3c'
    status_text = "✅ LICENCE VALIDE" if info['valid'] else "❌ LICENCE INVALIDE"
    
    tk.Label(
        status_frame,
        text=status_text,
        font=('Arial', 16, 'bold'),
        fg=status_color,
        bg='#1a1a2e'
    ).pack()
    
    if info.get('hw_id_short'):
        tk.Label(
            status_frame,
            text=f"PC ID: {info['hw_id_short']}",
            font=('Consolas', 10),
            fg='#666',
            bg='#1a1a2e'
        ).pack()
    
    # Zone principale
    main_frame = tk.Frame(root, bg='#1a1a2e', padx=40, pady=20)
    main_frame.pack(fill='both', expand=True)
    
    #placeholder pour le dashboard
    tk.Label(
        main_frame,
        text="🎯 Dashboard de Trading",
        font=('Arial', 18, 'bold'),
        fg='#fff',
        bg='#1a1a2e'
    ).pack(pady=20)
    
    tk.Label(
        main_frame,
        text="Le bot analysera les marchés et exécutera vos trades automatiquement.\n\n"
             "Configuration actuelle:\n"
             "• Symboles: EURUSD, GBPUSD, USDJPY\n"
             "• Timeframe: H1\n"
             "• Max positions: 3\n"
             "• Risk: 2%% par trade",
        font=('Arial', 11),
        fg='#ccc',
        bg='#1a1a2e',
        justify='left'
    ).pack(pady=20)
    
    # Boutons
    btn_frame = tk.Frame(main_frame, bg='#1a1a2e')
    btn_frame.pack(pady=20)
    
    def on_start():
        if not check_license(verbose=False):
            messagebox.showerror("Erreur", "Licence invalide ou expirée")
            return
        messagebox.showinfo("Info", "Bot démarré en mode trading...")
    
    def on_stop():
        messagebox.showinfo("Info", "Bot arrêté")
    
    tk.Button(
        btn_frame,
        text="▶️  DÉMARRER LE TRADING",
        font=('Arial', 12, 'bold'),
        bg='#27ae60',
        fg='#fff',
        padx=30,
        pady=15,
        command=on_start
    ).pack(side='left', padx=10)
    
    tk.Button(
        btn_frame,
        text="⏹️  ARRÊTER",
        font=('Arial', 12),
        bg='#e74c3c',
        fg='#fff',
        padx=30,
        pady=15,
        command=on_stop
    ).pack(side='left', padx=10)
    
    # Footer
    footer = tk.Frame(root, bg='#0d1117', pady=10)
    footer.pack(fill='x', side='bottom')
    
    tk.Label(
        footer,
        text="SafeTrendBot V5.3.0 — © 2026 — Trading automatique",
        font=('Arial', 9),
        fg='#666',
        bg='#0d1117'
    ).pack()
    
    root.mainloop()
    return True


def run_headless():
    """Lance en mode serveur (sans GUI)."""
    print("\n🚀 Mode Headless - Serveur de Trading")
    print("-" * 50)
    
    if not check_license(verbose=True):
        print("\n❌ Arrêt du bot: licence invalide")
        return False
    
    print("\n[INFO] Démarrage du moteur de trading...")
    print("[INFO] Ctrl+C pour arrêter")
    print()
    
    try:
        engine = TradingEngine()
        engine.start()
        
        # Boucle principale
        while True:
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Arrêt du bot...")
        engine.stop()
        print("[INFO] Bot arrêté")
    
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="SafeTrendBot V5")
    parser.add_argument("--headless", action="store_true", help="Mode serveur (sans GUI)")
    parser.add_argument("--check", action="store_true", help="Vérifier la licence")
    parser.add_argument("--activate", metavar="KEY", help="Activer avec une clé")
    parser.add_argument("--revoke", action="store_true", help="Révoquer la licence locale")
    
    args = parser.parse_args()
    
    print_banner()
    
    # Mode vérification
    if args.check:
        lm = LicenseManager()
        info = lm.get_info()
        print("\n📋 Informations Licence:")
        print(f"   Statut: {info['status']}")
        print(f"   Valide: {'Oui' if info['valid'] else 'Non'}")
        if info.get('hw_id_short'):
            print(f"   HW-ID: {info['hw_id_short']}")
        if info.get('activated_at'):
            print(f"   Activé le: {info['activated_at'][:10]}")
        return
    
    # Mode activation manuelle
    if args.activate:
        lm = LicenseManager()
        success, msg = lm.activate(args.activate)
        print(f"\n{'✅' if success else '❌'} {msg}")
        return
    
    # Mode révocation
    if args.revoke:
        print("\n⚠️  ATTENTION: Cette action détruira votre licence locale!")
        confirm = input("Êtes-vous sûr? (oui/non): ")
        if confirm.lower() == 'oui':
            lm = LicenseManager()
            lm.revoke_local()
        return
    
    # Mode normal
    if args.headless:
        run_headless()
    else:
        if not check_license():
            print("\n❌ Arrêt: Licence invalide")
            sys.exit(1)
        run_gui()


if __name__ == "__main__":
    main()