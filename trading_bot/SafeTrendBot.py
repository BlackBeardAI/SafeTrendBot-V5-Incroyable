#!/usr/bin/env python3
"""
SafeTrendBot - Launcher universel

Ce script :
1. Vérifie que Python est la bonne version
2. Crée l'environnement virtuel si absent
3. Installe les dépendances manquantes
4. Lance l'application

Usage : python SafeTrendBot.py
       ou double-clic sur SafeTrendBot.py (si Python associé)
       ou double-clic sur LANCEZ_MOI.bat
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

MIN_PYTHON = (3, 9)
REQUIRED_PYTHON = (3, 12)

# Dépendances essentielles (doivent s'installer sans quoi l'app ne démarre pas)
ESSENTIAL_DEPS = [
    "PyQt6",
    "numpy",
    "pandas",
    "requests",
]

# Dépendances optionnelles (l'app démarre sans, mais certaines fonctions manquent)
OPTIONAL_DEPS = {
    "yfinance": "Backtest (données historiques gratuites)",
    "matplotlib": "Graphiques dans les rapports",
    "reportlab": "Export PDF des rapports",
    "ib_insync": "Support Interactive Brokers",
    "ccxt": "Support crypto (Binance, Bybit, Kraken, Coinbase)",
}

# MT5 est installé à part (Windows uniquement)
MT5_DEP = ("MetaTrader5", "Trading via MetaTrader 5 (Windows uniquement)")


SCRIPT_DIR = Path(__file__).parent.absolute()
VENV_DIR = SCRIPT_DIR / "venv"


# ============================================================================
# HELPERS
# ============================================================================

class Colors:
    """Codes couleur ANSI — fonctionnent sur Win10+ et terminaux modernes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'


def enable_windows_ansi():
    """Active les couleurs ANSI sous Windows 10+"""
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def print_banner(text, color=Colors.CYAN):
    line = "=" * 66
    print(f"\n{color}{line}")
    print(f"  {text}")
    print(f"{line}{Colors.RESET}\n")


def print_step(n, total, text):
    print(f"{Colors.BLUE}[{n}/{total}]{Colors.RESET} {text}")


def print_ok(text):
    print(f"      {Colors.GREEN}OK{Colors.RESET} {text}")


def print_warn(text):
    print(f"      {Colors.YELLOW}!!{Colors.RESET} {text}")


def print_error(text):
    print(f"      {Colors.RED}ERREUR{Colors.RESET} {text}")


def press_enter_to_exit(code=0):
    print()
    try:
        input("Appuyez sur Entrée pour fermer...")
    except (KeyboardInterrupt, EOFError):
        pass
    sys.exit(code)


# ============================================================================
# VERIFICATIONS
# ============================================================================

def check_python_version():
    """Vérifie que Python est assez récent"""
    current = sys.version_info[:2]
    if current < MIN_PYTHON:
        print_error(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ requis.")
        print(f"      Vous avez Python {current[0]}.{current[1]}")
        print(f"      Téléchargez Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} sur https://www.python.org")
        return False
    print_ok(f"Python {current[0]}.{current[1]} détecté")
    return True


def get_venv_python():
    """Retourne le chemin du python dans le venv"""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_venv_pip():
    """Retourne le chemin du pip dans le venv"""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def ensure_venv():
    """Crée le venv s'il n'existe pas"""
    if get_venv_python().exists():
        print_ok("Environnement virtuel existant")
        return True

    print("      Création de l'environnement virtuel (10-20 secondes)...")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            check=True, capture_output=True, text=True
        )
        print_ok("Environnement virtuel créé")
        return True
    except subprocess.CalledProcessError as e:
        print_error("Impossible de créer l'environnement virtuel")
        print(f"      {e.stderr}")
        return False
    except Exception as e:
        print_error(f"Exception : {e}")
        return False


def is_installed(package_name):
    """Vérifie si un package est installé dans le venv"""
    pip = get_venv_pip()
    if not pip.exists():
        return False
    try:
        # pip show retourne 0 si installé
        result = subprocess.run(
            [str(pip), "show", package_name],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def install_package(package_name, quiet=True):
    """Installe un package dans le venv"""
    pip = get_venv_pip()
    if not pip.exists():
        return False
    cmd = [str(pip), "install", package_name]
    if quiet:
        cmd.append("--quiet")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        return False


def install_dependencies():
    """Installe toutes les dépendances nécessaires"""
    # Upgrade pip d'abord
    print("      Mise à jour de pip...")
    try:
        python = get_venv_python()
        subprocess.run(
            [str(python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
            check=True, capture_output=True
        )
    except Exception:
        print_warn("Pip n'a pas pu être mis à jour (non bloquant)")

    # Essentielles
    missing_essential = []
    for pkg in ESSENTIAL_DEPS:
        if is_installed(pkg):
            print_ok(f"{pkg} déjà installé")
        else:
            print(f"      Installation de {pkg}...")
            if install_package(pkg):
                print_ok(f"{pkg} installé")
            else:
                print_error(f"Impossible d'installer {pkg}")
                missing_essential.append(pkg)

    if missing_essential:
        print()
        print_error("Dépendances essentielles manquantes : " + ", ".join(missing_essential))
        print("      Vérifiez votre connexion internet et relancez.")
        return False

    # Optionnelles (ne bloquent pas)
    print()
    print("      Dépendances optionnelles...")
    for pkg, description in OPTIONAL_DEPS.items():
        if is_installed(pkg):
            print_ok(f"{pkg} déjà installé ({description})")
        else:
            if install_package(pkg):
                print_ok(f"{pkg} installé ({description})")
            else:
                print_warn(f"{pkg} non installé - {description} indisponible")

    # MT5 uniquement sur Windows
    if platform.system() == "Windows":
        pkg, desc = MT5_DEP
        if is_installed(pkg):
            print_ok(f"{pkg} déjà installé ({desc})")
        else:
            if install_package(pkg):
                print_ok(f"{pkg} installé ({desc})")
            else:
                print_warn(f"{pkg} non installé - trading MT5 indisponible")
    else:
        print_warn("MetaTrader5 non disponible (OS autre que Windows)")

    return True


def verify_main_py():
    """Vérifie que main.py existe et est valide"""
    main_py = SCRIPT_DIR / "main.py"
    if not main_py.exists():
        print_error("main.py introuvable dans le dossier !")
        print(f"      Dossier : {SCRIPT_DIR}")
        return False

    app_dir = SCRIPT_DIR / "app"
    if not app_dir.exists():
        print_error("Dossier app/ introuvable !")
        return False

    print_ok(f"main.py trouvé dans {SCRIPT_DIR.name}/")
    return True


def launch_app():
    """Lance l'application avec le python du venv"""
    python = get_venv_python()
    main_py = SCRIPT_DIR / "main.py"

    print()
    print_banner("Lancement de SafeTrendBot", Colors.GREEN)

    try:
        if platform.system() == "Windows":
            # Lancer detaché (sans console) via pythonw
            pythonw = VENV_DIR / "Scripts" / "pythonw.exe"
            if pythonw.exists():
                subprocess.Popen(
                    [str(pythonw), str(main_py)],
                    cwd=str(SCRIPT_DIR),
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                )
                print_ok("Application lancée (fenêtre PyQt6 en cours de chargement)")
                print()
                print("      Si aucune fenêtre n'apparaît dans 30 secondes :")
                print("      → Lancer launch_debug.bat pour voir les erreurs")
            else:
                # Fallback : lancer avec console visible
                subprocess.Popen([str(python), str(main_py)], cwd=str(SCRIPT_DIR))
                print_ok("Application lancée")
        else:
            # Linux/Mac : lancer en arrière-plan
            subprocess.Popen([str(python), str(main_py)], cwd=str(SCRIPT_DIR))
            print_ok("Application lancée")

        return True
    except Exception as e:
        print_error(f"Impossible de lancer l'application : {e}")
        return False


def run_app_directly():
    """Lance directement l'app sans sous-processus (mode debug)"""
    python = get_venv_python()
    main_py = SCRIPT_DIR / "main.py"

    os.chdir(str(SCRIPT_DIR))
    # Exec remplace le processus courant
    if platform.system() == "Windows":
        os.execv(str(python), [str(python), str(main_py)])
    else:
        os.execv(str(python), [str(python), str(main_py)])


def create_desktop_shortcut():
    """Crée un raccourci bureau (Windows uniquement)"""
    if platform.system() != "Windows":
        return False

    try:
        import ctypes
        # Utiliser PowerShell qui est garanti sur toutes les Windows 10+
        desktop = Path(os.path.expanduser("~/Desktop"))
        if not desktop.exists():
            desktop = Path(os.path.expanduser("~")) / "Bureau"  # Windows FR
        if not desktop.exists():
            return False

        shortcut_path = desktop / "SafeTrendBot.lnk"
        target = SCRIPT_DIR / "LANCEZ_MOI.bat"

        ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{target}"
$Shortcut.WorkingDirectory = "{SCRIPT_DIR}"
$Shortcut.IconLocation = "$env:SystemRoot\\System32\\shell32.dll,13"
$Shortcut.Description = "SafeTrendBot"
$Shortcut.Save()
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True, timeout=10
        )
        return shortcut_path.exists()
    except Exception:
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    enable_windows_ansi()

    print_banner("SafeTrendBot - Installation et Lancement")
    print("Ce script va installer et lancer SafeTrendBot automatiquement.")
    print("Durée estimée : 1 à 10 minutes selon l'état actuel du système.\n")

    total = 5

    # 1. Python
    print_step(1, total, "Vérification de Python")
    if not check_python_version():
        press_enter_to_exit(1)

    # 2. Fichiers projet
    print()
    print_step(2, total, "Vérification des fichiers du projet")
    if not verify_main_py():
        press_enter_to_exit(1)

    # 3. Venv
    print()
    print_step(3, total, "Préparation de l'environnement virtuel")
    if not ensure_venv():
        press_enter_to_exit(1)

    # 4. Dépendances
    print()
    print_step(4, total, "Installation des dépendances")
    if not install_dependencies():
        press_enter_to_exit(1)

    # 5. Raccourci bureau + Lancement
    print()
    print_step(5, total, "Finalisation")
    if create_desktop_shortcut():
        print_ok("Raccourci bureau créé")
    else:
        print_warn("Raccourci bureau non créé (pas bloquant)")

    # Lancer l'app
    print()
    print_banner("INSTALLATION REUSSIE", Colors.GREEN)
    print("Pour relancer plus tard :")
    print("  - Double-cliquer sur le raccourci 'SafeTrendBot' du bureau")
    print("  - OU sur LANCEZ_MOI.bat dans ce dossier")
    print()
    print("AVANT de trader avec MT5 :")
    print("  1. Ouvrir MetaTrader 5 en mode DEMO")
    print("  2. Outils > Options > Expert Advisors")
    print("     → Cocher 'Autoriser le trading automatique'")
    print("  3. Dans l'app : onglet 'Broker' > Tester la connexion")
    print()

    try:
        response = input("Lancer SafeTrendBot maintenant ? [O/n] : ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        response = "n"

    if response in ("", "o", "oui", "y", "yes"):
        launch_app()
        print()
        print("Cette fenêtre peut être fermée.")
        print()
        try:
            input("Appuyez sur Entrée pour fermer...")
        except (KeyboardInterrupt, EOFError):
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation interrompue.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.RED}Erreur inattendue :{Colors.RESET} {e}")
        import traceback
        traceback.print_exc()
        press_enter_to_exit(1)
