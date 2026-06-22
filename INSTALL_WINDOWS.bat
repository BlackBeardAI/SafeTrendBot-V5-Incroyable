@echo off
chcp 65001 >nul 2>&1
title SafeTrendBot V5 - Installation

echo.
echo  ╔═══════════════════════════════════════════════════════════════╗
echo  ║                    SafeTrendBot V5                            ║
echo  ║              Installation automatique                         ║
echo  ╚═══════════════════════════════════════════════════════════════╝
echo.

:: 1. Vérifier Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERREUR] Python n'est pas installe!
    echo.
    echo  Telechargez Python 3.11+ depuis: https://python.org/downloads
    echo  IMPORTANT: Cochez "Add Python to PATH" pendant l'installation
    echo.
    pause
    exit /b 1
)

:: 2. Vérifier la version Python
python -c "import sys; exit(0 if sys.version_info>=(3,11) else 1)" 2>nul
if %ERRORLEVEL% neq 0 (
    echo  [ERREUR] Python 3.11+ requis!
    echo  Votre version:
    python --version
    echo.
    pause
    exit /b 1
)

echo  [1/4] Python detecte:
python --version
echo.

:: 3. Installer les dépendances
echo  [2/4] Installation des dependances...
cd /d "%~dp0trading_bot"
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERREUR] Echec installation dependances
    echo  Essayez manuellement: pip install -r requirements.txt
    pause
    exit /b 1
)
echo.

:: 4. Créer le raccourci bureau
echo  [3/4] Creation du raccourci bureau...
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%USERPROFILE%\Desktop\SafeTrendBot V5.lnk'); $sc.TargetPath = '%~dp0trading_bot\main.py'; $sc.IconLocation = '%SystemRoot%\System32\shell32.dll,13'; $sc.WorkingDirectory = '%~dp0trading_bot'; $sc.Description = 'SafeTrendBot V5 - Trading Bot'; $sc.Save()" 2>nul
echo  [OK] Raccourci cree sur le bureau
echo.

:: 5. Test
echo  [4/4] Verification...
python -c "import PyQt6; import MetaTrader5; import pandas; import numpy; print('  Toutes les dependances sont OK')" 2>nul
if %ERRORLEVEL% neq 0 (
    echo  [WARN] Certaines dependances optionnelles manquent
    echo  Le bot peut quand meme fonctionner en mode papier
) else (
    echo  [OK] Tout est pret!
)
echo.

echo  ╔═══════════════════════════════════════════════════════════════╗
echo  ║                    INSTALLATION TERMINEE!                     ║
echo  ║                                                                 ║
echo  ║  Pour lancer SafeTrendBot:                                     ║
echo  ║    - Double-cliquez le raccourci sur le bureau                 ║
echo  ║    - Ou: python trading_bot\main.py                            ║
echo  ║                                                                 ║
echo  ║  Pour creer un installeur .msi:                                ║
echo  ║    python build_msi.py                                          ║
echo  ╚═══════════════════════════════════════════════════════════════╝
echo.
pause