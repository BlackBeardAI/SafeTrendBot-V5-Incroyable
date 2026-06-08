@echo off
REM ASCII uniquement - compatible toutes versions Windows
title SafeTrendBot - Installation

echo.
echo ==============================================================
echo           SafeTrendBot - Installation automatique
echo ==============================================================
echo.
echo Cette installation va :
echo   1. Verifier / installer Python 3.12
echo   2. Installer toutes les dependances necessaires
echo   3. Creer un raccourci sur le bureau
echo   4. Lancer l'application
echo.
echo Duree estimee : 5 a 15 minutes selon votre connexion.
echo.
pause
echo.

REM ===================================================================
REM  1. VERIFICATION DE PYTHON
REM ===================================================================
echo [1/5] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 goto :install_python
for /f "tokens=*" %%v in ('python --version') do echo       %%v detecte - OK
goto :python_ok

:install_python
echo       Python non detecte. Telechargement en cours...
echo.
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 (
    echo.
    echo       ERREUR : Impossible de telecharger Python.
    echo       Veuillez l'installer manuellement depuis https://www.python.org
    echo       IMPORTANT : cocher "Add Python to PATH" pendant l'installation.
    echo.
    pause
    exit /b 1
)

echo       Installation de Python en cours (silencieuse)...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

echo       Attente de la fin de l'installation...
timeout /t 10 /nobreak >nul

REM Rafraichir le PATH pour cette session
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo       ERREUR : Python ne fonctionne pas apres installation.
    echo       Redemarrez votre PC et relancez ce script.
    echo.
    pause
    exit /b 1
)
echo       Python installe avec succes

:python_ok
echo.

REM ===================================================================
REM  2. ENVIRONNEMENT VIRTUEL
REM ===================================================================
echo [2/5] Creation de l'environnement virtuel...
if exist "venv\Scripts\python.exe" (
    echo       Environnement virtuel existant - OK
    goto :venv_ok
)

python -m venv venv
if errorlevel 1 (
    echo.
    echo       ERREUR : Impossible de creer l'environnement virtuel.
    echo       Verifiez que vous avez les droits d'ecriture dans ce dossier.
    echo.
    pause
    exit /b 1
)
echo       Environnement virtuel cree

:venv_ok
echo.

REM ===================================================================
REM  3. DEPENDANCES
REM ===================================================================
echo [3/5] Installation des dependances (peut prendre plusieurs minutes)...
call "venv\Scripts\activate.bat"

echo       Mise a jour de pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 goto :deps_error

echo       PyQt6 (interface graphique)...
pip install PyQt6 --quiet
if errorlevel 1 goto :deps_error

echo       numpy, pandas...
pip install numpy pandas --quiet
if errorlevel 1 goto :deps_error

echo       yfinance, matplotlib (backtesting)...
pip install yfinance matplotlib --quiet
if errorlevel 1 goto :deps_error

echo       requests (news, calendrier)...
pip install requests --quiet
if errorlevel 1 goto :deps_error

echo       reportlab (rapports PDF)...
pip install reportlab --quiet
if errorlevel 1 goto :deps_error

echo       ib_insync (Interactive Brokers)...
pip install ib_insync --quiet
if errorlevel 1 (
    echo       [AVERTISSEMENT] ib_insync non installe - IB non disponible.
)

echo       ccxt (crypto: Binance, Bybit, Kraken, Coinbase)...
pip install ccxt --quiet
if errorlevel 1 (
    echo       [AVERTISSEMENT] ccxt non installe - crypto non disponible.
)

echo       MetaTrader5 (trading)...
pip install MetaTrader5 --quiet
if errorlevel 1 (
    echo       [AVERTISSEMENT] MetaTrader5 non installe.
    echo       Le bot fonctionnera mais pas avec MT5.
    echo       Installez manuellement : pip install MetaTrader5
)

echo       Toutes les dependances principales installees
goto :after_deps

:deps_error
echo.
echo       ERREUR : Installation d'une dependance echouee.
echo       Verifiez votre connexion internet et relancez.
echo.
pause
exit /b 1

:after_deps
echo.

REM ===================================================================
REM  4. LAUNCHER + RACCOURCI
REM ===================================================================
echo [4/5] Creation du raccourci bureau...

set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%SCRIPT_DIR%launch.bat"

REM Creer le script de lancement (sans fenetre console)
> "%LAUNCHER%" echo @echo off
>> "%LAUNCHER%" echo cd /d "%%~dp0"
>> "%LAUNCHER%" echo call venv\Scripts\activate.bat
>> "%LAUNCHER%" echo start "" pythonw main.py

REM Creer le raccourci via un script PowerShell temporaire
set "PS_SCRIPT=%TEMP%\create_shortcut.ps1"
> "%PS_SCRIPT%" echo $WshShell = New-Object -ComObject WScript.Shell
>> "%PS_SCRIPT%" echo $Desktop = [Environment]::GetFolderPath('Desktop')
>> "%PS_SCRIPT%" echo $Shortcut = $WshShell.CreateShortcut("$Desktop\SafeTrendBot.lnk")
>> "%PS_SCRIPT%" echo $Shortcut.TargetPath = '%LAUNCHER%'
>> "%PS_SCRIPT%" echo $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'
>> "%PS_SCRIPT%" echo $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
>> "%PS_SCRIPT%" echo $Shortcut.Description = 'SafeTrendBot - Trading Automation'
>> "%PS_SCRIPT%" echo $Shortcut.Save()

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
if errorlevel 1 (
    echo       [AVERTISSEMENT] Impossible de creer le raccourci bureau.
    echo       Lancez l'app avec launch.bat dans ce dossier.
) else (
    echo       Raccourci cree sur le bureau
)
del "%PS_SCRIPT%" 2>nul
echo.

REM ===================================================================
REM  5. LANCEMENT
REM ===================================================================
echo [5/5] Installation terminee !
echo.
echo ==============================================================
echo   INSTALLATION REUSSIE
echo ==============================================================
echo.
echo   Pour lancer l'application :
echo     - Double-cliquer sur le raccourci "SafeTrendBot" du bureau
echo     - OU double-cliquer sur launch.bat dans ce dossier
echo.
echo   AVANT de commencer a trader :
echo     1. Ouvrir MetaTrader 5 (en compte DEMO)
echo     2. Dans MT5 : Outils ^> Options ^> Expert Advisors
echo        Cocher "Autoriser le trading automatique"
echo     3. Dans l'app : onglet "Broker" ^> Tester la connexion
echo.
echo ==============================================================
echo.

choice /c ON /n /m "Lancer SafeTrendBot maintenant ? [O/N] : "
if errorlevel 2 goto :end
if errorlevel 1 (
    echo.
    echo       Lancement de SafeTrendBot...
    start "" "%LAUNCHER%"
    timeout /t 2 /nobreak >nul
)

:end
echo.
echo Au revoir !
timeout /t 3 /nobreak >nul
exit /b 0
