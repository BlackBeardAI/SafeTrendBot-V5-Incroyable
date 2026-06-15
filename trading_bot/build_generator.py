"""
SafeTrendBot V5 — BUILD GENERATOR
===================================
Outil professionnel pour créer des builds personnalisés.

Usage:
    python build_generator.py
    
Fonctionnalités:
- Interface GUI pour configurer le build
- Génère un .exe complet et autonome
- Inclut licence pré-configurée
- Branding personnalisable
- Auto-install + auto-destruct
"""

import os
import sys
import json
import shutil
import hashlib
import secrets
import string
import struct
import zlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = "5.3.0"
BUILD_DIR = Path(__file__).parent / "builds"
BUILD_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE KEY GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class LicenseKeyGenerator:
    """Génère des clés de licence."""
    
    CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # Pas de O, I, L
    
    @classmethod
    def generate(cls, prefix: str = "STB5") -> str:
        """Génère une clé: STB5-XXXX-XXXX-XXXX"""
        parts = []
        for _ in range(3):
            part = ''.join(secrets.choice(cls.CHARS) for _ in range(4))
            parts.append(part)
        return f"{prefix}-{'-'.join(parts)}"
    
    @classmethod
    def validate(cls, key: str) -> bool:
        """Valide le format d'une clé."""
        import re
        return bool(re.match(r"^STB5-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$", key, re.I))


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD CONFIGURATOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BuildConfig:
    """Configuration d'un build client."""
    app_name: str = "SafeTrendBot"
    output_name: str = "SafeTrendBot"
    version: str = VERSION
    license_key: str = ""
    client_name: str = ""
    client_email: str = ""
    expiry_days: Optional[int] = None  # None = permanent
    
    # Branding
    company_name: str = "SafeTrendBot"
    website: str = ""
    
    # Options
    include_mt5: bool = True
    include_binance: bool = False
    include_ctrader: bool = False
    include_xtb: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# EXE BUILDER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ExeBuilder:
    """
    Construit un .exe complet et autonome pour distribution.
    
    Le .exe résultat:
    - Inclut Python portable
    - Inclut toutes les dépendances
    - Inclut le code compilé (PyInstaller)
    - Inclut la licence pré-configurée
    - S'installe automatiquement
    - Se supprime après installation
    """
    
    # Template du script d'installation qui sera compilé
    INSTALLER_TEMPLATE = r'''
@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title %APPNAME% V%VERSION% - Installation

:: ═══════════════════════════════════════════════════════════════════════
:: %APPNAME% V%VERSION% - Auto-Installer
:: Generé le: %BUILDDATE%
:: ═══════════════════════════════════════════════════════════════════════

set "APPNAME=%APPNAME%"
set "VERSION=%VERSION%"
set "INSTALLKEY=%LICENSEKEY%"
set "CLIENTNAME=%CLIENTNAME%"
set "BUILDDATE=%BUILDDATE%"

:: Dossiers
set "INSTDIR=%USERPROFILE%\.%APPNAME%"
set "APPDIR=%INSTDIR%\app"
set "PYTHONDIR=%INSTDIR%\python"

:: URLs Python
set "PYURL=https://www.python.org/ftp/python/3.12.5/python-3.12.5-embed-amd64.zip"
set "PYZIP=%TEMP%\%RANDOM%_py.zip"

:: ═══════════════════════════════════════════════════════════════════════
:: BANNER
:: ═══════════════════════════════════════════════════════════════════════

:SHOWBANNER
cls
echo.
echo  ███████╗ ██████╗ ███████╗ ██████╗██╗   ██╗███████╗
echo  ██╔════╝██╔══██╗██╔════╝██╔════╝██║   ██║██╔════╝
echo  █████╗  ██████╔╝█████╗  ██║     ██║   ██║███████╗
echo  ██╔══╝  ██╔══██╗██╔══╝  ██║     ██║   ██║╚════██║
echo  ███████╗██║  ██║███████╗╚██████╗╚██████╔╝███████║
echo  ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║           %APPNAME% V%VERSION%                             ║
echo  ║           Installation Automatique                        ║
echo  ║           Client: %CLIENTNAME%                           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: ═══════════════════════════════════════════════════════════════════════
:: STEP 1: Preparation
:: ═══════════════════════════════════════════════════════════════════════

:STEP1
echo [1/5] Preparation...
if exist "%INSTDIR%" (
    takeown /F "%INSTDIR%" /R /D Y >nul 2>&1
    icacls "%INSTDIR%" /T /C /RESET >nul 2>&1
    rmdir /s /q "%INSTDIR%" 2>nul
)
mkdir "%INSTDIR%"
mkdir "%APPDIR%"
echo.     OK
echo.

:: ═══════════════════════════════════════════════════════════════════════
:: STEP 2: Python
:: ═══════════════════════════════════════════════════════════════════════

:STEP2
echo [2/5] Installation de Python 3.12...

:: Verifier Python systeme
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYEXE=python"
    set "PIPEXE=pip"
    goto :STEP3
)

:: Telecharger Python portable
echo.     Telechargement (48 MB)...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYZIP%'" 2>nul

if not exist "%PYZIP%" (
    echo.     ERREUR: Telechargement echoue!
    pause
    exit /b 1
)

echo.     Extraction...
mkdir "%PYTHONDIR%"
powershell -Command "Expand-Archive -Path '%PYZIP%' -DestinationPath '%PYTHONDIR%' -Force"

:: Configurer pip
set "PYEXE=%PYTHONDIR%\python.exe"
set "PIPEXE=%PYTHONDIR%\Scripts\pip.exe"

echo [global] > "%PYTHONDIR%\pip.ini"
echo trusted-host = pythonhosted.org pypi.org >> "%PYTHONDIR%\pip.ini"

if not exist "%PIPEXE%" (
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\gpi.py'" 2>nul
    !PYEXE! "%TEMP%\gpi.py" >nul 2>&1
)

echo.     OK
echo.

:: ═══════════════════════════════════════════════════════════════════════
:: STEP 3: Dependances
:: ═══════════════════════════════════════════════════════════════════════

:STEP3
echo [3/5] Installation des bibliotheques...
echo.

!PIPEXE! install --upgrade pip -q
!PIPEXE! install MetaTrader5 requests pandas numpy -q
!PIPEXE! install pyinstaller -q

echo.     OK
echo.

:: ═══════════════════════════════════════════════════════════════════════
:: STEP 4: Code source et licence
:: ═══════════════════════════════════════════════════════════════════════

:STEP4
echo [4/5] Configuration...

:: Cloner le depot
cd /d "%INSTDIR%"
git clone --depth 1 https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git temp_src 2>nul

if exist "%INSTDIR%\temp_src\trading_bot" (
    :: Copier les fichiers
    xcopy /E /I /Y "%INSTDIR%\temp_src\trading_bot\app" "%APPDIR%\" 2>nul
    
    :: Copier main.py et headless.py
    copy "%INSTDIR%\temp_src\trading_bot\main.py" "%INSTDIR%\main.py" 2>nul
    copy "%INSTDIR%\temp_src\trading_bot\headless.py" "%INSTDIR%\headless.py" 2>nul
    
    :: INJECTER LA LICENCE
    set "LICENSE_FILE=%APPDIR%\core\license_manager.py"
    if exist "!LICENSE_FILE!" (
        powershell -Command "(Get-Content '!LICENSE_FILE!') -replace '__LICENSE_KEY__', '%INSTALLKEY%' -replace '__BUILD_SALT__', '%RANDOM%%RANDOM%%RANDOM%' | Set-Content '!LICENSE_FILE!'"
    )
    
    :: Supprimer le repo source
    rmdir /s /q "%INSTDIR%\temp_src" 2>nul
)

echo.     Licence configuree: %INSTALLKEY%
echo.     OK
echo.

:: ═══════════════════════════════════════════════════════════════════════
:: STEP 5: Creer lanceurs et nettoyer
:: ═══════════════════════════════════════════════════════════════════════

:STEP5
echo [5/5] Finalisation...

:: Lanceur GUI
echo @echo off > "%INSTDIR%\Lancer %APPNAME%.bat"
echo @echo off >> "%INSTDIR%\Lancer %APPNAME%.bat"
echo cd /d "%%~dp0" >> "%INSTDIR%\Lancer %APPNAME%.bat"
echo if exist "python\python.exe" set "PATH=%%~dp0python;%%PATH%%" >> "%INSTDIR%\Lancer %APPNAME%.bat"
echo if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat >> "%INSTDIR%\Lancer %APPNAME%.bat"
echo python main.py >> "%INSTDIR%\Lancer %APPNAME%.bat"
echo pause >> "%INSTDIR%\Lancer %APPNAME%.bat"

:: Copier sur Bureau
copy "%INSTDIR%\Lancer %APPNAME%.bat" "%USERPROFILE%\Desktop\" 2>nul

:: Raccourci Bureau pour .exe si on l'a compile
if exist "%INSTDIR%\%APPNAME%.exe" (
    copy "%INSTDIR%\%APPNAME%.exe" "%USERPROFILE%\Desktop\" 2>nul
)

:: Nettoyer
if exist "%PYZIP%" del /f /q "%PYZIP%" 2>nul
if exist "%TEMP%\gpi.py" del /f /q "%TEMP%\gpi.py" 2>nul

echo.     OK
echo.

:: ═══════════════════════════════════════════════════════════════════════
:: FIN
:: ═══════════════════════════════════════════════════════════════════════

echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║              INSTALLATION TERMINEE!                             ║
echo ║                                                                  ║
echo ║     %APPNAME% est pre!                                          ║
echo ║                                                                  ║
echo ║     Lancement automatique dans 5 secondes...                   ║
echo ║                                                                  ║
echo ║     Clé de licence: %INSTALLKEY%                               ║
echo ║     A conserve r!                                               ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

timeout /t 5 /nobreak >nul

:: Lancer l'application
if exist "%INSTDIR%\%APPNAME%.exe" (
    start "" "%INSTDIR%\%APPNAME%.exe"
) else (
    start "" "%INSTDIR%\Lancer %APPNAME%.bat"
)

exit /b 0
'''.strip()
    
    def __init__(self, config: BuildConfig):
        self.config = config
        self.output_path = BUILD_DIR / f"{config.output_name}.exe"
        
    def generate_installer_script(self) -> str:
        """Génère le script batch d'installation."""
        template = self.INSTALLER_TEMPLATE
        
        # Remplacer les placeholders
        replacements = {
            "%APPNAME%": self.config.app_name,
            "%VERSION%": self.config.version,
            "%LICENSEKEY%": self.config.license_key,
            "%CLIENTNAME%": self.config.client_name or "Client",
            "%BUILDDATE%": datetime.now().strftime("%Y-%m-%d"),
        }
        
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)
        
        return template
    
    def build(self, progress_callback=None) -> Tuple[bool, str]:
        """
        Construit le .exe final.
        
        Returns: (success, message)
        """
        try:
            if progress_callback:
                progress_callback("Génération du script d'installation...")
            
            # 1. Générer le script batch
            script_content = self.generate_installer_script()
            script_path = BUILD_DIR / f"install_{self.config.output_name}.bat"
            script_path.write_text(script_content, encoding='utf-8')
            
            if progress_callback:
                progress_callback("Script généré, conversion en .exe...")
            
            # 2. Convertir le .bat en .exe avec des outils
            # Option A: Utiliser self-contained Python + PyInstaller
            # Option B: Utiliser un outil tiers
            
            # Pour l'instant, on crée un ZIP auto-extractible
            # Plus tard: utiliser py2exe, auto-py-to-exe, ou bat2exe
            
            # Créer un executable qui extrait et lance le .bat
            # Solution simple: PyInstaller sur un launcher Python
            
            launcher_content = '''
import os, sys, subprocess, tempfile

def main():
    script = """SCRIPT_PLACEHOLDER"""
    batch_file = os.path.join(tempfile.gettempdir(), "setup_CLIENT.bat")
    
    with open(batch_file, "w", encoding="utf-8") as f:
        f.write(script)
    
    subprocess.run(batch_file, shell=True)
    
    # Nettoyer ce launcher
    try:
        os.remove(sys.argv[0])
    except:
        pass
'''
            
            # Remplacer le placeholder par le contenu réel
            escaped_script = script_content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            launcher_content = launcher_content.replace('SCRIPT_PLACEHOLDER', escaped_script)
            
            # Sauvegarder le launcher
            launcher_path = BUILD_DIR / f"launcher_{self.config.output_name}.py"
            launcher_path.write_text(launcher_content)
            
            if progress_callback:
                progress_callback("Compilation avec PyInstaller...")
            
            # 3. Compiler avec PyInstaller
            import PyInstaller.__main__
            
            bat_file = str(BUILD_DIR / f"install_{self.config.output_name}.bat")
            add_data = f"{bat_file};."
            
            pyinstaller_args = [
                '--onefile',
                '--name', self.config.output_name,
                '--add-data', add_data,
                '--noconsole' if sys.platform == 'win32' else '',
                '--clean',
                '--noconfirm',
                str(launcher_path)
            ]
            PyInstaller.__main__.run(pyinstaller_args)
            
            # 4. Déplacer le .exe résultat
            pyinstaller_output = Path('dist') / self.config.output_name
            if sys.platform == 'win32':
                pyinstaller_output = Path('dist') / f"{self.config.output_name}.exe"
            
            if pyinstaller_output.exists():
                shutil.move(str(pyinstaller_output), str(self.output_path))
                
                # Nettoyer
                for f in [launcher_path, script_path]:
                    if f.exists():
                        f.unlink()
                if Path('dist').exists():
                    shutil.rmtree('dist')
                if Path('build').exists():
                    shutil.rmtree('build')
                
                if progress_callback:
                    progress_callback("Build terminé!")
                
                return True, str(self.output_path)
            
            return False, "PyInstaller n'a pas généré le fichier"
            
        except Exception as e:
            return False, f"Erreur: {str(e)}"
    
    def create_standalone_exe(self) -> bool:
        """
        Méthode alternative: crée le .exe avec tous les fichiers
        Nécessite PyInstaller installé
        """
        try:
            import PyInstaller.__main__
            
            # Générer spec file personnalisé
            spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{str(Path(__file__).parent / "main.py")}'],
    pathex=['{str(Path(__file__).parent)}'],
    binaries=[],
    datas=[
        ('{str(Path(__file__).parent / "app")}', 'app'),
    ],
    hiddenimports=['MetaTrader5', 'pandas', 'numpy', 'requests'],
    hookspath=[],
    hooksconfig={{}},
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.config.output_name}',
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
)

app = BUNDLE(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.config.output_name}.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
'''
            spec_path = BUILD_DIR / f"{self.config.output_name}.spec"
            spec_path.write_text(spec_content)
            
            # Lancer PyInstaller avec le spec
            PyInstaller.__main__.run([str(spec_path), '--noconfirm'])
            
            # Résultat dans dist/
            dist_exe = Path('dist') / f"{self.config.output_name}.exe"
            if dist_exe.exists():
                final_path = BUILD_DIR / f"{self.config.output_name}_v{VERSION}.exe"
                shutil.move(str(dist_exe), str(final_path))
                self.output_path = final_path
                return True
            
            return False
            
        except Exception as e:
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# GUI BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class BuildGeneratorGUI:
    """Interface graphique du générateur de builds."""
    
    def __init__(self):
        self.window = tk.Tk()
        self.window.title(f"SafeTrendBot V5 — Build Generator {VERSION}")
        self.window.geometry("700x650")
        self.window.configure(bg='#1a1a2e')
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configure l'interface."""
        main_frame = tk.Frame(self.window, bg='#1a1a2e')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        header = tk.Label(
            main_frame,
            text="🔨 SafeTrendBot Build Generator",
            font=('Arial', 20, 'bold'),
            fg='#00d9ff',
            bg='#1a1a2e'
        )
        header.pack(pady=(0, 20))
        
        # Section: Infos Application
        section1 = tk.LabelFrame(
            main_frame,
            text="📦 Application",
            font=('Arial', 12, 'bold'),
            fg='#00d9ff',
            bg='#1a1a2e',
            padx=15,
            pady=10
        )
        section1.pack(fill='x', pady=10)
        
        # Nom de l'app
        tk.Label(section1, text="Nom de l'application:", fg='#888', bg='#1a1a2e').grid(row=0, column=0, sticky='w', pady=5)
        self.app_name = tk.Entry(section1, width=40, bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff')
        self.app_name.insert(0, "SafeTrendBot")
        self.app_name.grid(row=0, column=1, pady=5, padx=10)
        
        # Nom du fichier de sortie
        tk.Label(section1, text="Nom du fichier .exe:", fg='#888', bg='#1a1a2e').grid(row=1, column=0, sticky='w', pady=5)
        self.output_name = tk.Entry(section1, width=40, bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff')
        self.output_name.insert(0, "SafeTrendBot")
        self.output_name.grid(row=1, column=1, pady=5, padx=10)
        
        # Version
        tk.Label(section1, text="Version:", fg='#888', bg='#1a1a2e').grid(row=2, column=0, sticky='w', pady=5)
        self.version = tk.Entry(section1, width=40, bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff')
        self.version.insert(0, VERSION)
        self.version.grid(row=2, column=1, pady=5, padx=10)
        
        # Section: Licence
        section2 = tk.LabelFrame(
            main_frame,
            text="🔑 Licence",
            font=('Arial', 12, 'bold'),
            fg='#00d9ff',
            bg='#1a1a2e',
            padx=15,
            pady=10
        )
        section2.pack(fill='x', pady=10)
        
        # Clé de licence
        tk.Label(section2, text="Clé de licence:", fg='#888', bg='#1a1a2e').grid(row=0, column=0, sticky='w', pady=5)
        self.license_key = tk.Entry(section2, width=40, bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff')
        self.license_key.grid(row=0, column=1, pady=5, padx=10)
        
        # Bouton générer clé
        def generate_key():
            key = LicenseKeyGenerator.generate()
            self.license_key.delete(0, 'end')
            self.license_key.insert(0, key)
            
        tk.Button(section2, text="🎲 Générer", command=generate_key, bg='#0f3460', fg='#fff').grid(row=0, column=2, padx=5)
        
        # Client
        tk.Label(section2, text="Nom du client:", fg='#888', bg='#1a1a2e').grid(row=1, column=0, sticky='w', pady=5)
        self.client_name = tk.Entry(section2, width=40, bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff')
        self.client_name.grid(row=1, column=1, columnspan=2, pady=5, padx=10, sticky='w')
        
        # Section: Broker Options
        section3 = tk.LabelFrame(
            main_frame,
            text="🔌 Brokers à inclure",
            font=('Arial', 12, 'bold'),
            fg='#00d9ff',
            bg='#1a1a2e',
            padx=15,
            pady=10
        )
        section3.pack(fill='x', pady=10)
        
        self.include_mt5 = tk.BooleanVar(value=True)
        self.include_binance = tk.BooleanVar(value=False)
        self.include_ctrader = tk.BooleanVar(value=False)
        self.include_xtb = tk.BooleanVar(value=False)
        
        tk.Checkbutton(section3, text="MetaTrader 5 (MT5)", variable=self.include_mt5, fg='#fff', bg='#1a1a2e', selectcolor='#0d1117').grid(row=0, column=0, sticky='w', padx=5)
        tk.Checkbutton(section3, text="Binance", variable=self.include_binance, fg='#fff', bg='#1a1a2e', selectcolor='#0d1117').grid(row=0, column=1, sticky='w', padx=5)
        tk.Checkbutton(section3, text="cTrader", variable=self.include_ctrader, fg='#fff', bg='#1a1a2e', selectcolor='#0d1117').grid(row=1, column=0, sticky='w', padx=5, pady=5)
        tk.Checkbutton(section3, text="XTB", variable=self.include_xtb, fg='#fff', bg='#1a1a2e', selectcolor='#0d1117').grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
        # Section: Branding
        section4 = tk.LabelFrame(
            main_frame,
            text="🎨 Branding",
            font=('Arial', 12, 'bold'),
            fg='#00d9ff',
            bg='#1a1a2e',
            padx=15,
            pady=10
        )
        section4.pack(fill='x', pady=10)
        
        tk.Label(section4, text="Nom entreprise:", fg='#888', bg='#1a1a2e').grid(row=0, column=0, sticky='w', pady=5)
        self.company_name = tk.Entry(section4, width=40, bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff')
        self.company_name.insert(0, "SafeTrendBot")
        self.company_name.grid(row=0, column=1, pady=5, padx=10)
        
        # Bouton BUILD
        self.build_btn = tk.Button(
            main_frame,
            text="🚀 GÉNÉRER LE BUILD",
            font=('Arial', 14, 'bold'),
            bg='#27ae60',
            fg='#fff',
            padx=30,
            pady=15,
            command=self.start_build
        )
        self.build_btn.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=10)
        
        # Status
        self.status = tk.Label(
            main_frame,
            text="Prêt à générer un build",
            fg='#888',
            bg='#1a1a2e'
        )
        self.status.pack()
        
    def start_build(self):
        """Lance la génération du build."""
        # Valider les champs
        if not self.app_name.get().strip():
            messagebox.showerror("Erreur", "Nom de l'application requis")
            return
            
        if not self.license_key.get().strip():
            messagebox.showerror("Erreur", "Clé de licence requise (utilisez 🎲 pour générer)")
            return
            
        if not LicenseKeyGenerator.validate(self.license_key.get()):
            messagebox.showerror("Erreur", "Format de clé invalide (STB5-XXXX-XXXX-XXXX)")
            return
        
        # Créer la config
        config = BuildConfig(
            app_name=self.app_name.get().strip(),
            output_name=self.output_name.get().strip(),
            version=self.version.get().strip() or VERSION,
            license_key=self.license_key.get().strip(),
            client_name=self.client_name.get().strip(),
            company_name=self.company_name.get().strip() or "SafeTrendBot",
            include_mt5=self.include_mt5.get(),
            include_binance=self.include_binance.get(),
            include_ctrader=self.include_ctrader.get(),
            include_xtb=self.include_xtb.get(),
        )
        
        # Désactiver le bouton
        self.build_btn.config(state='disabled', text="Génération en cours...")
        self.progress.start()
        
        # Lancer le build en arrière-plan
        self.window.after(100, self._do_build, config)
        
    def _do_build(self, config):
        """Effectue le build."""
        builder = ExeBuilder(config)
        
        def progress_callback(msg):
            self.window.after(0, lambda: self.status.config(text=msg))
        
        success, result = builder.build(progress_callback)
        
        self.progress.stop()
        self.build_btn.config(state='normal', text="🚀 GÉNÉRER LE BUILD")
        
        if success:
            messagebox.showinfo(
                "✅ Build Terminé!",
                f"Le fichier a été créé:\n\n{result}\n\n"
                f"Clé de licence: {config.license_key}\n\n"
                f"Copiez ce fichier et envoyez-le au client!"
            )
            self.status.config(text=f"✅ Build terminé: {Path(result).name}")
        else:
            messagebox.showerror("❌ Erreur", result)
            self.status.config(text=f"❌ Erreur: {result}")
    
    def run(self):
        """Lance l'interface."""
        self.window.mainloop()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Si arguments, lancer en mode CLI
    if len(sys.argv) > 1 and sys.argv[1] == '--cli':
        import argparse
        parser = argparse.ArgumentParser(description="Build Generator")
        parser.add_argument('--name', required=True)
        parser.add_argument('--license', required=True)
        parser.add_argument('--client', default='')
        args = parser.parse_args()
        
        config = BuildConfig(
            app_name=args.name,
            output_name=args.name,
            license_key=args.license,
            client_name=args.client
        )
        
        builder = ExeBuilder(config)
        success, msg = builder.build()
        print(f"{'✅' if success else '❌'} {msg}")
        sys.exit(0 if success else 1)
    
    # Sinon, GUI
    app = BuildGeneratorGUI()
    app.run()