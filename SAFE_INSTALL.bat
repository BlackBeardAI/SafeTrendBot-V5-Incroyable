@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title SafeTrendBot V5 - Installation Complète

:: ═══════════════════════════════════════════════════════════════════════════
:: SafeTrendBot V5 — Installation 100% Automatique
:: Inclut Python, dépendances, et lancement en 1 clic
:: ═══════════════════════════════════════════════════════════════════════════

set "INSTALL_DIR=%~dp0trading_bot"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.5/python-3.12.5-embed-amd64.zip"
set "PYTHON_ZIP=%TEMP%\python_embed.zip"
set "PYTHON_DIR=%INSTALL_DIR%\python"

echo.
echo  ██████╗ ███████╗███████╗ ██████╗██╗   ██╗███████╗
echo  ██╔══██╗██╔════╝██╔════╝██╔════╝██║   ██║██╔════╝
echo  ██████╔╝█████╗  ███████╗██║     ██║   ██║███████╗
echo  ██╔══██╗██╔══╝  ╚════██║██║     ██║   ██║╚════██║
echo  ██████╔╝███████╗███████║╚██████╗╚██████╔╝███████║
echo  ╚═════╝ ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝
echo.
echo  V5.3.0 — Installation 100%% Automatique
echo  ============================================
echo.

:: ─── ÉTAPE 1: Vérifier Python ───
echo [1/7] Vérification de Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Python déjà installé: 
    python --version
    set "PYTHON_CMD=python"
    goto :CHECK_VENV
)

:: ─── ÉTAPE 1bis: Python pas trouvé, installation ───
echo   ✗ Python non trouvé. Installation en cours...
echo.

:: Télécharger Python Embeddable
echo   Téléchargement de Python 3.12 (48 MB)...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'"

if not exist "%PYTHON_ZIP%" (
    echo   ERREUR: Téléchargement échoué
    echo   Vérifiez votre connexion internet
    pause
    exit /b 1
)

echo   Extraction de Python...
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

:: Configurer Python portable
if exist "%PYTHON_DIR%\python.exe" (
    echo   Python installé avec succès!
) else (
    echo   ERREUR: Extraction échouée
    pause
    exit /b 1
)

:: Ajouter Python au PATH temporaire
set "PATH=%PYTHON_DIR%;%PATH%"
set "PYTHON_CMD=%PYTHON_DIR%\python.exe"

:: ─── ÉTAPE 2: Configurer pip ───
:CHECK_VENV
echo.
echo [2/7] Configuration de pip...

:: Créer pip.ini si nécessaire (pour éviter erreurs SSL)
echo   > "%PYTHON_DIR%\pip.ini" [global]
echo   >> "%PYTHON_DIR%\pip.ini" trusted-host = pythonhosted.org pypi.org files.pythonhosted.org
echo   >> "%PYTHON_DIR%\pip.ini" trusted-host = github.com

:: Télécharger pip si absent
if not exist "%PYTHON_DIR%\Scripts\pip.exe" (
    echo   Installation de pip...
    "%PYTHON_CMD%" -m ensurepip --default-pip >nul 2>&1
    
    :: Télécharger get-pip.py
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py'"
    "%PYTHON_CMD%" "%TEMP%\get-pip.py" >nul 2>&1
)

:: ─── ÉTAPE 3: Cloner/Mise à jour du projet ───
echo.
echo [3/7] Téléchargement de SafeTrendBot...

if exist "%INSTALL_DIR%" (
    echo   Mise à jour du projet...
    cd /d "%INSTALL_DIR%"
    if exist ".git" (
        git pull origin main >nul 2>&1
    )
) else (
    echo   Clonage du projet...
    git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git "%INSTALL_DIR%"
    if !errorlevel! neq 0 (
        echo   ATTENTION: Git non installé ou erreur
        echo   Tentative de téléchargement ZIP...
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable/archive/refs/heads/main.zip' -OutFile '%TEMP%\safetrendbot.zip'"
        powershell -Command "Expand-Archive -Path '%TEMP%\safetrendbot.zip' -DestinationPath '%TEMP%' -Force"
        xcopy /E /I /Y "%TEMP%\SafeTrendBot-V5-Incroyable-main\trading_bot" "%INSTALL_DIR%\"
    )
)

cd /d "%INSTALL_DIR%"

:: ─── ÉTAPE 4: Créer venv ───
echo.
echo [4/7] Configuration de l'environnement...
if exist "venv" (
    echo   - Environnement existant trouvé
) else (
    echo   - Création de l'environnement Python...
    "%PYTHON_CMD%" -m venv venv
)

:: ─── ÉTAPE 5: Installer dépendances ───
echo.
echo [5/7] Installation des bibliothèques...
echo   (Cela peut prendre 2-3 minutes)

set "PIP_CMD=%INSTALL_DIR%\venv\Scripts\pip.exe"
if not exist "%PIP_CMD%" (
    set "PIP_CMD=%PYTHON_DIR%\Scripts\pip.exe"
)

:: Mise à jour pip
"%PIP_CMD%" install --upgrade pip -q

:: Installation des dépendances principales
echo   - MetaTrader5...
"%PIP_CMD%" install MetaTrader5 -q

echo   - Requêtes HTTP...
"%PIP_CMD%" install requests -q

echo   - Traitement de données...
"%PIP_CMD%" install pandas numpy -q

echo   - Interface graphique...
"%PIP_CMD%" install tkintertable pillow -q 2>nul

:: ─── ÉTAPE 6: Créer raccourcis ───
echo.
echo [6/7] Création des raccourcis...

:: Créer le script de lancement GUI
echo @echo off > "%INSTALL_DIR%\LAUNCHER.bat"
echo cd /d "%%~dp0" >> "%INSTALL_DIR%\LAUNCHER.bat"
echo if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat >> "%INSTALL_DIR%\LAUNCHER.bat"
echo if exist "python\python.exe" set "PATH=%%~dp0python;%%PATH%%" >> "%INSTALL_DIR%\LAUNCHER.bat"
echo python main.py >> "%INSTALL_DIR%\LAUNCHER.bat"
echo pause >> "%INSTALL_DIR%\LAUNCHER.bat"

:: Créer le script de lancement Headless
echo @echo off > "%INSTALL_DIR%\LAUNCHER_HEADLESS.bat"
echo cd /d "%%~dp0" >> "%INSTALL_DIR%\LAUNCHER_HEADLESS.bat"
echo if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat >> "%INSTALL_DIR%\LAUNCHER_HEADLESS.bat"
echo if exist "python\python.exe" set "PATH=%%~dp0python;%%PATH%%" >> "%INSTALL_DIR%\LAUNCHER_HEADLESS.bat"
echo python headless.py >> "%INSTALL_DIR%\LAUNCHER_HEADLESS.bat"

:: ─── ÉTAPE 7: Terminé ───
echo.
echo [7/7] Terminé!
echo.

:: ═══════════════════════════════════════════════════════════════════
echo   ╔══════════════════════════════════════════════════════════╗
echo   ║                                                          ║
echo   ║     INSTALLATION RÉUSSIE!                                ║
echo   ║                                                          ║
echo   ║     Pour démarrer le bot:                                ║
echo   ║     ==============================                       ║
echo   ║                                                          ║
echo   ║     DOUBLE-CLIQUEZ SUR:                                 ║
echo   ║                                                          ║
echo   ║     📁 LAUNCHER.bat     (Interface graphique)           ║
echo   ║     📁 LAUNCHER_HEADLESS.bat  (Mode serveur)            ║
echo   ║                                                          ║
echo   ╚══════════════════════════════════════════════════════════╝
echo.

:: Demander si lancement
set /p LAUNCH="Voulez-vous lancer le bot maintenant ? (O/N): "
if /i "%LAUNCH%"=="O" (
    echo.
    echo Lancement...
    echo.
    call "%INSTALL_DIR%\LAUNCHER.bat"
) else (
    echo.
    echo Au revoir! Double-cliquez sur LAUNCHER.bat pour démarrer.
)

pause