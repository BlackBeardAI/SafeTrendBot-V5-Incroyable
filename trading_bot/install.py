#!/usr/bin/env python3
"""
Installateur cross-platform SafeTrendBot V5.
Usage: python install.py
"""
import sys
import os
import subprocess
import platform
from pathlib import Path
from urllib.request import urlretrieve


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def run(cmd, check=True):
    """Exécute une commande shell"""
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"ERREUR: {result.stderr}")
        return False
    if result.stdout:
        print(result.stdout.strip())
    return True


def check_python():
    """Vérifie que Python 3.10+ est installé"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python {version.major}.{version.minor} détecté. Python 3.10+ requis.")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Installe les dépendances pip"""
    print_header("Installation des dépendances")
    req_file = Path(__file__).parent / "requirements.txt"
    if not req_file.exists():
        print("❌ requirements.txt introuvable")
        return False
    
    # Upgrade pip d'abord
    run(f"{sys.executable} -m pip install --upgrade pip")
    
    # Installation
    ok = run(f"{sys.executable} -m pip install -r {req_file}")
    if not ok:
        print("⚠️  Échec installation standard, tentative sans dépendances optionnelles...")
        run(f"{sys.executable} -m pip install PyQt6 numpy pandas yfinance requests reportlab")
    return ok


def create_dirs():
    """Crée les répertoires de données"""
    print_header("Création des répertoires")
    base = Path.home() / ".safetrendbot"
    dirs = [base / "data", base / "logs", base / "profiles", base / "reports"]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  📁 {d}")
    # Lien symbolique dans le projet
    proj_data = Path(__file__).parent / "data"
    if not proj_data.exists():
        try:
            if platform.system() != "Windows":
                os.symlink(base / "data", proj_data)
        except Exception:
            proj_data.mkdir(exist_ok=True)
    return True


def setup_linux_service():
    """Configure le service systemd pour le mode headless"""
    if platform.system() != "Linux":
        return True
    
    print_header("Configuration service systemd (optionnel)")
    reply = input("Créer le service systemd pour le mode headless ? [y/N] ").lower()
    if reply != 'y':
        return True
    
    bot_dir = Path(__file__).parent.absolute()
    service_content = f"""[Unit]
Description=SafeTrendBot V5 Headless
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={bot_dir}
ExecStart={sys.executable} {bot_dir / 'headless.py'} --paper
Restart=always
RestartSec=10
Environment=PYTHONPATH={bot_dir}

[Install]
WantedBy=multi-user.target
"""
    service_path = Path.home() / ".config" / "systemd" / "user" / "safetrendbot.service"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    service_path.write_text(service_content)
    
    run("systemctl --user daemon-reload")
    print(f"✅ Service créé : {service_path}")
    print("   Démarrer : systemctl --user start safetrendbot")
    print("   Activer au boot : systemctl --user enable safetrendbot")
    return True


def setup_windows_shortcut():
    """Crée un raccourci Windows"""
    if platform.system() != "Windows":
        return True
    
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(Path(desktop) / "SafeTrendBot V5.lnk"))
        shortcut.Targetpath = str(sys.executable)
        shortcut.Arguments = str(Path(__file__).parent / "main.py")
        shortcut.WorkingDirectory = str(Path(__file__).parent)
        shortcut.IconLocation = str(Path(__file__).parent / "icon.ico")
        shortcut.save()
        print(f"✅ Raccourci créé sur le bureau")
    except ImportError:
        print("ℹ️  winshell non installé — raccourci ignoré")
    return True


def install_optional_ml():
    """Installe les dépendances ML optionnelles"""
    print_header("Dépendances optionnelles (Machine Learning)")
    reply = input("Installer scikit-learn + hmmlearn pour le ML régime ? [y/N] ").lower()
    if reply == 'y':
        run(f"{sys.executable} -m pip install scikit-learn hmmlearn")
    
    reply = input("Installer transformers pour le NLP sentiment ? [y/N] ").lower()
    if reply == 'y':
        run(f"{sys.executable} -m pip install transformers torch")
    
    reply = input("Installer fastapi + uvicorn pour le Web Dashboard ? [y/N] ").lower()
    if reply == 'y':
        run(f"{sys.executable} -m pip install fastapi uvicorn websockets")
    return True


def main():
    print_header("SafeTrendBot V5 — Installateur")
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    
    if not check_python():
        sys.exit(1)
    
    if not install_dependencies():
        print("⚠️  Installation partielle — vérifiez les erreurs ci-dessus")
    
    create_dirs()
    install_optional_ml()
    
    if platform.system() == "Linux":
        setup_linux_service()
    elif platform.system() == "Windows":
        setup_windows_shortcut()
    
    print_header("Installation terminée")
    print("""
Lancer SafeTrendBot:
  → UI Desktop : python main.py
  → Mode Headless : python headless.py --paper
  → Web Dashboard : http://localhost:8080 (après lancement UI)

Documentation : README.md
""")


if __name__ == "__main__":
    main()
