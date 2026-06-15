@echo off
chcp 65001 >nul
title SafeTrendBot V5 - Installation

:: ═══════════════════════════════════════════════════════════════════
:: SafeTrendBot V5 — Installation Automatique (Un Clic)
:: ═══════════════════════════════════════════════════════════════════

echo.
echo  ███████╗ ██████╗██╗  ██╗ ██████╗ ███████╗███████╗
echo  ██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝██╔════╝
echo  █████╗  ╚█████╗ ███████║██║   ██║█████╗  ███████╗
echo  ██╔══╝   ╚═══██╗██╔══██║██║   ██║██╔══╝  ╚════██║
echo  ███████╗██████╔╝██║  ██║╚██████╔╝███████╗███████║
echo  ╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝
echo.
echo  Installation Automatique V5.3.0
echo  ==================================
echo.

:: Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/5] Python non trouvé. Installation en cours...
    echo.
    echo Rendez-vous sur: https://www.python.org/downloads/windows/
    echo.
    echo Téléchargez Python 3.10+ et relancez ce script.
    echo.
    pause
    exit /b 1
)

echo [1/5] Python détecté: 
python --version
echo.

:: Aller dans le dossier utilisateur
cd /d "%USERPROFILE%"

:: Vérifier si le projet existe déjà
if exist "SafeTrendBot-V5-Incroyable" (
    echo [2/5] Projet existant. Mise à jour...
    cd SafeTrendBot-V5-Incroyable
    git pull origin main
) else (
    echo [2/5] Téléchargement du projet...
    git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
    cd SafeTrendBot-V5-Incroyable
)

cd trading_bot
echo.

:: Créer environnement virtuel
echo [3/5] Configuration de l'environnement...
if exist "venv" (
    echo   - Environnement virtuel trouvé
) else (
    echo   - Création de l'environnement virtuel...
    python -m venv venv
)
echo.

:: Activer venv et installer dépendances
echo [4/5] Installation des dépendances...
call venv\Scripts\activate.bat

pip install --upgrade pip >nul 2>&1
pip install MetaTrader5 requests python-dotenv >nul 2>&1
pip install pandas numpy >nul 2>&1

echo.
echo [5/5] Installation terminée!
echo.
echo ═══════════════════════════════════════════════════════════
echo.
echo   Installation réussie!
echo.
echo   Lancement du bot:
echo   ================
echo.
echo   Double-cliquez sur: DEMARRER_SafeTrendBot.bat
echo.
echo   Ou lancez manuellement:
echo   cd %USERPROFILE%\SafeTrendBot-V5-Incroyable\trading_bot
echo   venv\Scripts\activate
echo   python main.py
echo.
echo ═══════════════════════════════════════════════════════════
echo.

:: Créer le fichier de lancement
echo @echo off > "%USERPROFILE%\SafeTrendBot-V5-Incroyable\trading_bot\DEMARRER_SafeTrendBot.bat"
echo cd /d "%%USERPROFILE%%\SafeTrendBot-V5-Incroyable\trading_bot" >> "%USERPROFILE%\SafeTrendBot-V5-Incroyable\trading_bot\DEMARRER_SafeTrendBot.bat"
echo call venv\Scripts\activate.bat >> "%USERPROFILE%\SafeTrendBot-V5-Incroyable\trading_bot\DEMARRER_SafeTrendBot.bat"
echo python main.py >> "%USERPROFILE%\SafeTrendBot-V5-Incroyable\trading_bot\DEMARRER_SafeTrendBot.bat"
echo pause >> "%USERPROFILE%\SafeTrendBot-V5-Incroyable\trading_bot\DEMARRER_SafeTrendBot.bat"

echo.
echo Lancement du bot dans 3 secondes...
timeout /t 3 /nobreak >nul

:: Lancer le bot
call venv\Scripts\activate.bat
python main.py

pause