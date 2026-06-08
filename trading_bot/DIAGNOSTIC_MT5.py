"""
DIAGNOSTIC MT5 - SafeTrendBot
==============================
Lancez ce fichier DIRECTEMENT dans votre venv pour diagnostiquer
pourquoi MT5 ne se connecte pas.

Usage :
    venv\Scripts\activate.bat
    python DIAGNOSTIC_MT5.py
"""

import sys
import os

print("=" * 60)
print("  DIAGNOSTIC SafeTrendBot - MT5")
print("=" * 60)
print()

# ============================================================
# ÉTAPE 1 : Python version
# ============================================================
print(f"[1/6] Python : {sys.version}")
if sys.version_info < (3, 9):
    print("  ⚠️  Python trop ancien. Requis : 3.9+")
else:
    print("  ✓ Version OK")
print()

# ============================================================
# ÉTAPE 2 : Lib MetaTrader5 installée ?
# ============================================================
print("[2/6] Bibliothèque MetaTrader5...")
try:
    import MetaTrader5 as mt5
    print(f"  ✓ MetaTrader5 installée (version {mt5.__version__})")
    MT5_LIB_OK = True
except ImportError:
    print("  ✗ MetaTrader5 NON INSTALLÉE")
    print("  → Lancez : pip install MetaTrader5")
    print("  → Assurez-vous d'être dans le venv avant !")
    MT5_LIB_OK = False
print()

if not MT5_LIB_OK:
    print("❌ Impossible de continuer sans MetaTrader5.")
    input("\nAppuyez sur Entrée pour quitter...")
    sys.exit(1)

# ============================================================
# ÉTAPE 3 : MT5 est-il installé sur le PC ?
# ============================================================
print("[3/6] Recherche du terminal MetaTrader5...")
import glob

possible_paths = [
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal\*\terminal64.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\MetaTrader 5\terminal64.exe"),
]

found_path = None
for pattern in possible_paths:
    matches = glob.glob(pattern)
    if matches:
        found_path = matches[0]
        break

if found_path:
    print(f"  ✓ Terminal trouvé : {found_path}")
else:
    print("  ⚠️  Terminal non trouvé dans les chemins standards")
    print("  → Ce n'est pas bloquant si MT5 est dans un autre dossier")
print()

# ============================================================
# ÉTAPE 4 : Connexion automatique (terminal déjà ouvert)
# ============================================================
print("[4/6] Tentative de connexion automatique à MT5...")
print("  (MT5 doit être OUVERT et CONNECTÉ à votre compte)")
print()

try:
    if mt5.initialize():
        print("  ✓ CONNEXION RÉUSSIE en mode automatique !")
        MT5_CONNECTED = True
    else:
        error = mt5.last_error()
        print(f"  ✗ Échec connexion automatique")
        print(f"  Erreur MT5 : {error}")
        print()
        print("  Causes possibles :")
        print("  • MetaTrader 5 n'est pas lancé sur votre PC")
        print("  • Vous n'êtes pas connecté à un compte dans MT5")
        print("  • MT5 attend une confirmation (popup 'Autoriser')")
        MT5_CONNECTED = False
except Exception as e:
    print(f"  ✗ Exception : {e}")
    MT5_CONNECTED = False
print()

if not MT5_CONNECTED:
    print("═" * 60)
    print("  SOLUTION :")
    print()
    print("  1. Ouvrez MetaTrader 5 sur votre PC")
    print("  2. Connectez-vous à votre compte (démo recommandé)")
    print("  3. Dans MT5 : Outils → Options → Expert Advisors")
    print("     ✓ Cochez 'Autoriser le trading automatique'")
    print("     ✓ Cochez 'Autoriser les imports de DLL'")
    print("  4. Relancez ce diagnostic")
    print("═" * 60)
    input("\nAppuyez sur Entrée pour quitter...")
    sys.exit(1)

# ============================================================
# ÉTAPE 5 : Informations du compte
# ============================================================
print("[5/6] Informations du compte...")
try:
    account = mt5.account_info()
    if account:
        print(f"  ✓ Compte    : {account.name}")
        print(f"  ✓ Serveur   : {account.server}")
        print(f"  ✓ Balance   : {account.balance:.2f} {account.currency}")
        print(f"  ✓ Équité    : {account.equity:.2f} {account.currency}")
        print(f"  ✓ Levier    : 1:{account.leverage}")
        print(f"  ✓ Démo      : {'OUI' if account.trade_mode == 0 else 'NON (compte réel !)'}")
        if account.trade_mode != 0:
            print()
            print("  ⚠️  ATTENTION : Vous êtes sur un COMPTE RÉEL !")
            print("  ⚠️  Utilisez un compte DÉMO pour commencer !")
    else:
        print(f"  ✗ Impossible de lire le compte : {mt5.last_error()}")
except Exception as e:
    print(f"  ✗ Exception : {e}")
print()

# ============================================================
# ÉTAPE 6 : Test symboles
# ============================================================
print("[6/6] Test des symboles EURUSD...")
try:
    symbols_to_test = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    found_symbols = []

    for sym in symbols_to_test:
        info = mt5.symbol_info(sym)
        if info:
            tick = mt5.symbol_info_tick(sym)
            if tick:
                found_symbols.append(sym)
                print(f"  ✓ {sym:10s} Bid={tick.bid:.5f}  Ask={tick.ask:.5f}")
            else:
                # Essayer d'activer le symbole
                mt5.symbol_select(sym, True)
                tick = mt5.symbol_info_tick(sym)
                if tick:
                    found_symbols.append(sym)
                    print(f"  ✓ {sym:10s} (activé) Bid={tick.bid:.5f}")
                else:
                    print(f"  ⚠️  {sym:10s} : pas de prix disponible (inactif?)")
        else:
            print(f"  ✗ {sym:10s} : symbole non trouvé chez votre broker")

    if not found_symbols:
        print()
        print("  ⚠️  Aucun symbole disponible.")
        print("  → Vérifiez que votre broker propose EURUSD")
        print("  → Allez dans 'Affichage → Symboles' dans MT5")
        print("     et activez les symboles manquants")
except Exception as e:
    print(f"  ✗ Exception : {e}")

print()

# ============================================================
# RÉSUMÉ
# ============================================================
print("=" * 60)
print("  RÉSUMÉ")
print("=" * 60)
print(f"  MetaTrader5 lib : ✓")
print(f"  Connexion MT5   : ✓")

if account:
    mode_str = "DÉMO ✓" if account.trade_mode == 0 else "⚠️  RÉEL"
    print(f"  Compte          : {account.name} ({mode_str})")
    print(f"  Balance         : {account.balance:.2f} {account.currency}")

if found_symbols:
    print(f"  Symboles OK     : {', '.join(found_symbols)}")
else:
    print(f"  Symboles        : ⚠️  Aucun symbole actif")

print()
print("  ✅ MT5 est correctement configuré !")
print()
print("  PROCHAINES ÉTAPES :")
print("  1. Lancez SafeTrendBot via LANCEZ_MOI.bat")
print("  2. Allez dans l'onglet 'Broker'")
print("  3. Cliquez '🔌 Tester la connexion MT5'")
print("  4. Allez dans 'Profils trading' → choisissez 'Normal'")
print("  5. Allez dans 'Paper Trading' → activez le mode PAPER")
print("  6. Tableau de bord → '▶ Démarrer le bot'")
print()
print("  ⚠️  NOTE sur les trades :")
print("  Le bot peut mettre plusieurs heures avant de placer")
print("  son premier trade. C'est NORMAL. Il attend un signal")
print("  fort (2 stratégies d'accord sur 4). Patience !")
print()

mt5.shutdown()
input("Appuyez sur Entrée pour quitter...")
