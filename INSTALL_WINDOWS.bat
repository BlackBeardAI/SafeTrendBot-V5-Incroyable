@echo off
title SafeTrendBot V5 - Installation
setlocal enabledelayedexpansion

echo.
echo  ============================================================
echo  |                    SafeTrendBot V5                        |
echo  |              Installation automatique                      |
echo  ============================================================
echo.

rem --- Etape 1: Verifier Python ---
echo  [1/4] Verification de Python...
where python >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo.
    echo  [ERREUR] Python n'est pas installe ou n'est pas dans le PATH
    echo.
    echo  Solution:
    echo    1. Telechargez Python 3.11+ sur https://python.org/downloads
    echo    2. Pendant l'installation, COCHEZ "Add Python to PATH"
    echo    3. Relancez ce script
    echo.
    pause
    exit /b 1
)

python --version 2>nul
if !ERRORLEVEL! neq 0 (
    echo.
    echo  [ERREUR] Python detecte mais ne se lance pas correctement
    echo  Essayez de reinstaller Python 3.11+
    echo.
    pause
    exit /b 1
)

echo  Python OK:
python --version
echo.

rem --- Verifier version Python ---
python -c "import sys; exit(0 if sys.version_info>=(3,11) else 1)" 2>nul
if !ERRORLEVEL! neq 0 (
    echo  [ERREUR] Python 3.11+ requis. Votre version:
    python --version
    echo.
    echo  Mettez a jour Python depuis https://python.org/downloads
    echo.
    pause
    exit /b 1
)
echo  Version Python OK
echo.

rem --- Etape 2: Aller dans le dossier trading_bot ---
echo  [2/4] Installation des dependances...
echo  Dossier courant: %~dp0
echo  Destination: %~dp0trading_bot
echo.

cd /d "%~dp0trading_bot"
if !ERRORLEVEL! neq 0 (
    echo  [ERREUR] Impossible d'acceder au dossier trading_bot
    echo  Verifiez que le dossier existe a cote de ce .bat
    echo  Dossier attendu: %~dp0trading_bot
    echo.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo  [ERREUR] requirements.txt non trouve dans:
    echo  %CD%
    echo.
    echo  Verifiez que vous avez extrait tout le dossier du zip GitHub
    echo.
    pause
    exit /b 1
)

echo  Installation de pip (mise a jour)...
python -m pip install --upgrade pip
echo.

echo  Installation des dependances (cela peut prendre quelques minutes)...
python -m pip install -r requirements.txt
if !ERRORLEVEL! neq 0 (
    echo.
    echo  [ATTENTION] Certaines dependances n'ont pas pu etre installees
    echo  Essayez manuellement: pip install PyQt6 numpy pandas MetaTrader5
    echo.
    echo  Le bot peut fonctionner avec les dependances de base
    echo.
    pause
)
echo.

rem --- Etape 3: Raccourci bureau ---
echo  [3/4] Creation du raccourci bureau...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%USERPROFILE%\Desktop\SafeTrendBot V5.lnk'); $sc.TargetPath = 'pythonw.exe'; $sc.Arguments = '"%~dp0trading_bot\main.py"'; $sc.WorkingDirectory = '%~dp0trading_bot'; $sc.Description = 'SafeTrendBot V5 - Trading Bot'; $sc.Save()"
if !ERRORLEVEL! neq 0 (
    echo  [ATTENTION] Le raccourci n'a pas pu etre cree automatiquement
    echo  Vous pouvez lancer le bot avec: python %~dp0trading_bot\main.py
) else (
    echo  [OK] Raccourci cree sur le bureau
)
echo.

rem --- Etape 4: Verification ---
echo  [4/4] Verification des modules...
python -c "import PyQt6; print('  PyQt6: OK')" 2>nul || echo  PyQt6: MANQUANT
python -c "import numpy; print('  numpy: OK')" 2>nul || echo  numpy: MANQUANT
python -c "import pandas; print('  pandas: OK')" 2>nul || echo  pandas: MANQUANT
python -c "import MetaTrader5; print('  MetaTrader5: OK')" 2>nul || echo  MetaTrader5: MANQUANT (optionnel)
echo.

echo  ============================================================
echo  |                  INSTALLATION TERMINEE!                   |
echo  |                                                            |
echo  |  Pour lancer SafeTrendBot:                                 |
echo  |    - Double-cliquez le raccourci sur le bureau             |
echo  |    - Ou ouvrez un terminal et tapez:                       |
echo  |      python "%~dp0trading_bot\main.py"                     |
echo  |                                                            |
echo  |  En cas de probleme, lancez le bot en ligne de commande    |
echo  |  pour voir les messages d'erreur.                          |
echo  ============================================================
echo.
echo  Appuyez sur une touche pour fermer...
pause >nul