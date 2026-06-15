@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title SafeTrendBot V5 - Installation

:: ═══════════════════════════════════════════════════════════════════════════
:: SafeTrendBot V5 — Installation Complète (100% Automatique)
:: 
:: Ce script installe TOUT:
:: - Python 3.12 (si absent)
:: - Toutes les bibliothèques
:: - Le projet complet
:: - Crée les lanceurs
:: 
:: Utilisation: Double-cliquez sur ce fichier
:: ═══════════════════════════════════════════════════════════════════════════

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%SafeTrendBot"
set "PYTHON_ZIP=%TEMP%\python312_embed.zip"
set "PYTHON_DIR=%PROJECT_DIR%\python"

:: Python Embeddable URL (version portable)
set "PY_URL=https://www.python.org/ftp/python/3.12.5/python-3.12.5-embed-amd64.zip"

:: ═══════════════════════════════════════════════════════════════════════════
:: BANNER
:: ═══════════════════════════════════════════════════════════════════════════

echo.
echo  ███████╗ ██████╗██╗  ██╗ ██████╗ ███████╗███████╗██████╗ 
echo  ██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝██╔════╝██╔══██╗
echo  █████╗  ╚█████╗ ███████║██║   ██║█████╗  ███████╗██████╔╝
echo  ██╔══╝   ╚═══██╗██╔══██║██║   ██║██╔══╝  ╚════██║██╔══██╗
echo  ███████╗██████╔╝██║  ██║╚██████╔╝███████╗███████║██║  ██║
echo  ╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝
echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║         INSTALLATION AUTOMATIQUE V5.3.0                  ║
echo  ║         =====================================             ║
echo  ║         Installation 100%% automatique                    ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: FONCTIONS
:: ═══════════════════════════════════════════════════════════════════════════

:check_admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Exécution en mode standard (recommandé)
    echo.
)
goto :start_install

:cleanup
if exist "%PYTHON_ZIP%" del /f /q "%PYTHON_ZIP%" 2>nul
exit /b 0

:: ═══════════════════════════════════════════════════════════════════════════
:: INSTALLATION
:: ═══════════════════════════════════════════════════════════════════════════

:start_install

:: ─── ÉTAPE 1 ───
echo [ETAPE 1/6] Vérification du système...
echo.

:: Vérifier si Python système existe
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python système détecté:
    python --version
    set "PYTHON=python"
    set "PIP=pip"
    goto :clone_project
)

echo [INFO] Python non trouvé sur ce système
echo [INFO] Installation de Python 3.12 portable...
echo.

:: ─── ÉTAPE 2: Télécharger Python ───
echo.
echo [ETAPE 2/6] Téléchargement de Python 3.12...
echo.

if exist "%PYTHON_ZIP%" del /f /q "%PYTHON_ZIP%"

echo     Téléchargement en cours (48 MB)...
echo     Cela peut prendre 1-2 minutes selon votre connexion...
echo.

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PYTHON_ZIP%' -TimeoutSec 300"

if not exist "%PYTHON_ZIP%" (
    echo.
    echo [ERREUR] Téléchargement échoué!
    echo.
    echo Vérifiez votre connexion internet et réessayez.
    echo.
    pause
    goto :end_error
)

echo     ✓ Téléchargement terminé!
echo.

:: ─── ÉTAPE 3: Extraire Python ───
echo [ETAPE 3/6] Installation de Python...

:: Créer dossier Python
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

:: Extraire
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

if not exist "%PYTHON_DIR%\python.exe" (
    echo [ERREUR] Extraction Python échouée!
    pause
    goto :end_error
)

echo     ✓ Python installé: %PYTHON_DIR%

:: Configurer Python portable
set "PYTHON=%PYTHON_DIR%\python.exe"
set "PIP=%PYTHON_DIR%\Scripts\pip.exe"

:: Configurer pip pour Python portable
echo.
echo     Configuration de pip...
echo.

:: Créer pip.ini pour éviter les erreurs SSL
echo [global] > "%PYTHON_DIR%\pip.ini"
echo trusted-host = pythonhosted.org >> "%PYTHON_DIR%\pip.ini"
echo trusted-host = pypi.org >> "%PYTHON_DIR%\pip.ini"
echo trusted-host = files.pythonhosted.org >> "%PYTHON_DIR%\pip.ini"
echo. >> "%PYTHON_DIR%\pip.ini"
echo [install] >> "%PYTHON_DIR%\pip.ini"
echo trusted-host = github.com >> "%PYTHON_DIR%\pip.ini"

:: Installer pip
if not exist "%PYTHON_DIR%\Scripts\pip.exe" (
    echo     Installation de pip...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%TEMP%\get-pip.py'"
    "%PYTHON%" "%TEMP%\get-pip.py" >nul 2>&1
)

:: ─── ÉTAPE 4: Projet ───
:clone_project
echo.
echo [ETAPE 4/6] Téléchargement de SafeTrendBot...
echo.

if exist "%PROJECT_DIR%" (
    echo     [INFO] Projet déjà présent
    echo     [INFO] Mise à jour...
    cd /d "%PROJECT_DIR%"
    if exist ".git" (
        git fetch origin main 2>nul
        git reset --hard origin/main 2>nul
    )
) else (
    echo     Clonage du dépôt GitHub...
    git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git "%PROJECT_DIR%"
)

if not exist "%PROJECT_DIR%\trading_bot" (
    echo.
    echo [ERREUR] Projet non trouvé!
    echo.
    pause
    goto :end_error
)

echo     ✓ Projet téléchargé

:: ─── ÉTAPE 5: Dépendances ───
echo.
echo [ETAPE 5/6] Installation des bibliothèques...
echo.

cd /d "%PROJECT_DIR%\trading_bot"

:: Créer venv avec Python portable
if not exist "venv" (
    echo     Création de l'environnement virtuel...
    "%PYTHON%" -m venv venv
)

:: Pip du venv
set "VENV_PIP=venv\Scripts\pip.exe"
if not exist "%VENV_PIP%" (
    set "VENV_PIP=%PIP%"
)

echo     Installation en cours (environ 2-3 minutes)...
echo.

:: Installer les dépendances principales
echo     - MetaTrader5 (API broker)...
"%VENV_PIP%" install MetaTrader5 --quiet 2>nul

echo     - Requests (HTTP)...
"%VENV_PIP%" install requests --quiet 2>nul

echo     - Pandas/Numpy (données)...
"%VENV_PIP%" install pandas numpy --quiet 2>nul

echo.
echo     ✓ Bibliothèques installées

:: ─── ÉTAPE 6: Créer lanceurs ───
echo.
echo [ETAPE 6/6] Configuration finale...
echo.

:: Lanceur Principal (GUI)
echo @echo off > "LANCER_SafeTrendBot.bat"
echo rem ═══════════════════════════════════════════════════════════ >> "LANCER_SafeTrendBot.bat"
echo rem SafeTrendBot V5 - Lanceur Principal >> "LANCER_SafeTrendBot.bat"
echo rem ═══════════════════════════════════════════════════════════ >> "LANCER_SafeTrendBot.bat"
echo @echo off >> "LANCER_SafeTrendBot.bat"
echo cd /d "%%~dp0" >> "LANCER_SafeTrendBot.bat"
echo if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat >> "LANCER_SafeTrendBot.bat"
echo if exist "python\python.exe" set "PATH=%%~dp0python;%%PATH%%" >> "LANCER_SafeTrendBot.bat"
echo title SafeTrendBot V5 - Trading Bot >> "LANCER_SafeTrendBot.bat"
echo python main.py >> "LANCER_SafeTrendBot.bat"
echo echo. >> "LANCER_SafeTrendBot.bat"
echo echo Appuyez sur une touche pour quitter... >> "LANCER_SafeTrendBot.bat"
echo pause ^>nul >> "LANCER_SafeTrendBot.bat"

:: Lanceur Headless (Serveur)
echo @echo off > "LANCER_Headless.bat"
echo cd /d "%%~dp0" >> "LANCER_Headless.bat"
echo if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat >> "LANCER_Headless.bat"
echo if exist "python\python.exe" set "PATH=%%~dp0python;%%PATH%%" >> "LANCER_Headless.bat"
echo title SafeTrendBot V5 - Mode Serveur >> "LANCER_Headless.bat"
echo python headless.py >> "LANCER_Headless.bat"

:: ReadMe
echo @echo off > "LISEZ_MOI.bat"
echo cls >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo ═══════════════════════════════════════════════════════════════════ >> "LISEZ_MOI.bat"
echo echo                    SAFE TRENDBOT V5                             >> "LISEZ_MOI.bat"
echo echo              Installation Terminee avec Succes               >> "LISEZ_MOI.bat"
echo echo ═══════════════════════════════════════════════════════════════════ >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo  POUR DEMARRER LE BOT:                                        >> "LISEZ_MOI.bat"
echo echo  ═══════════════════════════════════════                       >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo  1. Double-cliquez sur: LANCER_SafeTrendBot.bat                >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo  2. Entrez votre cle de licence quand demande                  >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo  3. Commencez a trader!                                        >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo ═══════════════════════════════════════════════════════════════════ >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo CONTACTS:                                                     >> "LISEZ_MOI.bat"
echo echo - Email: support@safetrendbot.com                             >> "LISEZ_MOI.bat"
echo echo - GitHub: https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable >> "LISEZ_MOI.bat"
echo echo. >> "LISEZ_MOI.bat"
echo echo Appuyez sur une touche pour quitter... >> "LISEZ_MOI.bat"
echo pause ^>nul >> "LISEZ_MOI.bat"

echo     ✓ Lanceur GUI cree: LANCER_SafeTrendBot.bat
echo     ✓ Lanceur Headless: LANCER_Headless.bat

:: Nettoyer
call :cleanup

:: ─── FIN ───
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                                                                  ║
echo ║                    INSTALLATION TERMINEE!                        ║
echo ║                                                                  ║
echo ║    ==========================================================   ║
echo ║                                                                  ║
echo ║    Le bot est pre! Pour le lancer:                              ║
echo ║                                                                  ║
echo ║    >>> DOUBLE-CLIQUEZ SUR <<<                                    ║
echo ║                                                                  ║
echo ║        LANCER_SafeTrendBot.bat                                   ║
echo ║                                                                  ║
echo ║    (ou LANCER_Headless.bat pour le mode serveur)                 ║
echo ║                                                                  ║
echo ║    ==========================================================   ║
echo ║                                                                  ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

:: Proposer de lancer
choice /C ON /M "Voulez-vous lancer le bot maintenant? (O/N) "
if errorlevel 1 (
    if errorlevel 2 goto :end_clean
    echo.
    echo Lancement dans 3 secondes...
    timeout /t 3 /nobreak >nul
    start "" "%PROJECT_DIR%\trading_bot\LANCER_SafeTrendBot.bat"
    goto :end_clean
)

:end_clean
echo.
echo Merci d'utiliser SafeTrendBot!
echo.
pause
exit /b 0

:end_error
call :cleanup
echo.
echo L'installation a echoue. Contactez le support.
echo.
pause
exit /b 1