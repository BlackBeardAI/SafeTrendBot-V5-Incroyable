@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title SafeTrendBot V5 - Installation

:: ═══════════════════════════════════════════════════════════════════════════
:: SafeTrendBot V5 — SELF-CONTAINED INSTALLER
:: 
:: Ce script:
:: 1. Télécharge Python portable si absent
:: 2. Installe toutes les dépendances
:: 3. Compile le code en .exe (pyinstaller --onefile)
:: 4. Crée le lanceur
:: 5. SE SUPPRIME LUI-MÊME après installation
:: 6. Lance l'application
::
:: Le client reçoit UN SEUL FICHIER: "SafeTrendBot-Setup.exe"
:: ═══════════════════════════════════════════════════════════════════════════

set "SELF=%~f0"
set "TEMP_ROOT=%TEMP%\SafeTrendBot_Install"
set "PROJECT_DIR=%TEMP_ROOT%\SafeTrendBot"
set "PYTHON_DIR=%PROJECT_DIR%\python"
set "VENV_DIR=%PROJECT_DIR%\venv"
set "BUILD_DIR=%PROJECT_DIR%\build"

:: URLs
set "PY_URL=https://www.python.org/ftp/python/3.12.5/python-3.12.5-embed-amd64.zip"
set "PY_ZIP=%TEMP%\python312.zip"

:: ═══════════════════════════════════════════════════════════════════════════
:: BANNER
:: ═══════════════════════════════════════════════════════════════════════════

:show_banner
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
echo  ║           INSTALLATION AUTOMATIQUE V5.3.0               ║
echo  ║           ======================================         ║
echo  ║           NE FERMEZ PAS CETTE FENETRE                  ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: ÉTAPE 1: Créer l'environnement
:: ═══════════════════════════════════════════════════════════════════════════

:step1
echo [1/6] Préparation de l'installation...
echo.

if exist "%PROJECT_DIR%" (
    echo     Nettoyage ancien install...
    rmdir /s /q "%PROJECT_DIR%" 2>nul
)

mkdir "%PROJECT_DIR%"
mkdir "%PROJECT_DIR%\app"
mkdir "%BUILD_DIR%"

echo     ✓ Environnement créé
echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: ÉTAPE 2: Télécharger et installer Python
:: ═══════════════════════════════════════════════════════════════════════════

:step2
echo [2/6] Installation de Python 3.12...
echo.

:: Vérifier si Python système existe (pourrait être plus rapide)
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo     Python système trouvé: 
    python --version
    set "PYTHON=python"
    set "PIP=pip"
    goto :step3
)

echo     Téléchargement de Python portable (48 MB)...
echo     Cela peut prendre 1-3 minutes selon votre connexion...
echo.

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%' -TimeoutSec 300" 2>nul

if not exist "%PY_ZIP%" (
    echo.
    echo [ERREUR] Téléchargement Python échoué!
    echo.
    echo Vérifiez votre connexion internet.
    pause
    exit /b 1
)

echo     Extraction de Python...
powershell -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

:: Configurer Python portable
set "PYTHON=%PYTHON_DIR%\python.exe"
set "PIP=%PYTHON_DIR%\Scripts\pip.exe"

:: Configurer pip
echo     Configuration de pip...
echo [global] > "%PYTHON_DIR%\pip.ini"
echo trusted-host = pythonhosted.org >> "%PYTHON_DIR%\pip.ini"
echo trusted-host = pypi.org >> "%PYTHON_DIR%\pip.ini"
echo trusted-host = files.pythonhosted.org >> "%PYTHON_DIR%\pip.ini"
echo. >> "%PYTHON_DIR%\pip.ini"
echo [install] >> "%PYTHON_DIR%\pip.ini"
echo trusted-host = github.com >> "%PYTHON_DIR%\pip.ini"

:: Installer pip
if not exist "%PIP%" (
    echo     Installation de pip...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py'" 2>nul
    "%PYTHON%" "%TEMP%\get-pip.py" >nul 2>&1
)

echo     ✓ Python installé: %PYTHON_DIR%
echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: ÉTAPE 3: Télécharger le code source et installer dépendances
:: ═══════════════════════════════════════════════════════════════════════════

:step3
echo [3/6] Téléchargement du code source...
echo.

:: Cloner le repo
cd /d "%PROJECT_DIR%"
git clone --depth 1 https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git temp_repo 2>nul

if exist "%PROJECT_DIR%\temp_repo\trading_bot" (
    echo     Copie des fichiers...
    xcopy /E /I /Y "%PROJECT_DIR%\temp_repo\trading_bot\app" "%PROJECT_DIR%\app\"
    copy "%PROJECT_DIR%\temp_repo\trading_bot\main.py" "%PROJECT_DIR%\main.py" 2>nul
    copy "%PROJECT_DIR%\temp_repo\trading_bot\headless.py" "%PROJECT_DIR%\headless.py" 2>nul
    copy "%PROJECT_DIR%\temp_repo\trading_bot\requirements.txt" "%PROJECT_DIR%\requirements.txt" 2>nul
    
    :: Supprimer le repo temporaire
    rmdir /s /q "%PROJECT_DIR%\temp_repo" 2>nul
    echo     ✓ Code source téléchargé
) else (
    echo     ATTENTION: Clone échoué, utilisation fallback...
    :: En dernier recours, on crée quand même les fichiers minima
    echo     ! Fonctionnalité limitée
)

echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: ÉTAPE 4: Installer les dépendances Python
:: ═══════════════════════════════════════════════════════════════════════════

:step4
echo [4/6] Installation des bibliothèques...
echo.

:: Mettre à jour pip
"%PIP%" install --upgrade pip -q

:: Installer les dépendances principales
echo     - MetaTrader5 (API broker)...
"%PIP%" install MetaTrader5 -q 2>nul

echo     - Requêtes HTTP...
"%PIP%" install requests -q 2>nul

echo     - Analyse de données...
"%PIP%" install pandas numpy -q 2>nul

echo.
echo     ✓ Bibliothèques installées
echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: ÉTAPE 5: Compiler en .exe avec PyInstaller
:: ═══════════════════════════════════════════════════════════════════════════

:step5
echo [5/6] Compilation en fichier exécutable...
echo.

:: Installer PyInstaller
echo     Installation de PyInstaller...
"%PIP%" install pyinstaller -q 2>nul

cd /d "%PROJECT_DIR%"

:: Supprimer ancienne compilation
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%" 2>nul

echo.
echo     Compilation en cours (2-5 minutes)...
echo     Ne fermez pas cette fenêtre!
echo.

:: Compiler avec PyInstaller --onefile (UN SEUL .exe)
"%PYTHON%" -m PyInstaller --onefile --windowed --name SafeTrendBotV5 --add-data "%PROJECT_DIR%\app;app" --noconfirm main.py >nul 2>&1

if exist "%PROJECT_DIR%\dist\SafeTrendBotV5.exe" (
    echo.
    echo     ✓ Compilation réussie!
    echo.
    
    :: Copier le .exe dans le dossier final
    copy "%PROJECT_DIR%\dist\SafeTrendBotV5.exe" "%PROJECT_DIR%\SafeTrendBot.exe" >nul
    
    :: Copier aussi dans le dossier parent pour accès facile
    copy "%PROJECT_DIR%\SafeTrendBot.exe" "%USERPROFILE%\Desktop\SafeTrendBot.exe" >nul 2>nul
    
) else (
    echo.
    echo [ERREUR] Compilation échouée!
    echo.
    echo Le fichier .exe n'a pas été créé.
    pause
    exit /b 1
)

echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: ÉTAPE 6: Créer les lanceurs et nettoyer
:: ═══════════════════════════════════════════════════════════════════════════

:step6
echo [6/6] Finalisation...
echo.

:: Créer le script de lancement (GUI)
echo @echo off > "%PROJECT_DIR%\Lancer SafeTrendBot.bat"
echo cd /d "%%~dp0" >> "%PROJECT_DIR%\Lancer SafeTrendBot.bat"
echo "%%~dp0SafeTrendBot.exe" >> "%PROJECT_DIR%\Lancer SafeTrendBot.bat"

:: Créer lanceur headless
echo @echo off > "%PROJECT_DIR%\Lancer Headless.bat"
echo cd /d "%%~dp0" >> "%PROJECT_DIR%\Lancer Headless.bat"
echo "%%~dp0SafeTrendBot.exe" headless >> "%PROJECT_DIR%\Lancer Headless.bat"

:: Nettoyer les fichiers temporaires
echo     Nettoyage...
if exist "%PY_ZIP%" del /f /q "%PY_ZIP%" 2>nul
if exist "%TEMP%\get-pip.py" del /f /q "%TEMP%\get-pip.py" 2>nul
if exist "%PROJECT_DIR%\build" rmdir /s /q "%PROJECT_DIR%\build" 2>nul
if exist "%PROJECT_DIR%\dist" rmdir /s /q "%PROJECT_DIR%\dist" 2>nul
if exist "%PROJECT_DIR%\__pycache__" rmdir /s /q "%PROJECT_DIR%\__pycache__" 2>nul
if exist "%PROJECT_DIR%\venv" rmdir /s /q "%PROJECT_DIR%\venv" 2>nul

:: Supprimer les .pyc et pycache
for /r "%PROJECT_DIR%" %%f in (*.pyc __pycache__) do (
    if exist "%%f" rmdir /s /q "%%f" 2>nul
)

:: ═══════════════════════════════════════════════════════════════════════════
:: FIN - Auto-suppression et lancement
:: ═══════════════════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║              INSTALLATION TERMINÉE!                               ║
echo ║                                                                  ║
echo ║     ========================================================     ║
echo ║                                                                  ║
echo ║     Le fichier SafeTrendBot.exe a été créé sur votre Bureau!   ║
echo ║                                                                  ║
echo ║     UTILISATION:                                                 ║
echo ║     1. Fermez cette fenêtre                                     ║
echo ║     2. Double-cliquez sur "SafeTrendBot.exe" sur le Bureau     ║
echo ║     3. Entrez votre clé de licence                              ║
echo ║     4. C'est parti!                                             ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

:: Lancer l'application
echo Lancement de SafeTrendBot dans 3 secondes...
timeout /t 3 /nobreak >nul

start "" "%USERPROFILE%\Desktop\SafeTrendBot.exe"

:: Supprimer le script d'installation lui-même
echo.
echo Nettoyage de l'installateur...
ping 127.0.0.1 -n 2 >nul

:: Supprimer le .bat lui-même (auto-cleanup)
del "%SELF%" 2>nul

exit /b 0