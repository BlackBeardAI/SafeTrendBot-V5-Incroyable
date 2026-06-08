@echo off
REM ===================================================
REM  Script de démarrage SafeTrendBot - Windows
REM ===================================================

echo ======================================
echo   SafeTrendBot - Demarrage Windows
echo ======================================
echo.

REM Vérification de Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH
    echo Telecharger Python depuis https://www.python.org/
    pause
    exit /b 1
)

REM Création de l'environnement virtuel s'il n'existe pas
if not exist "venv\" (
    echo [INFO] Creation de l'environnement virtuel...
    python -m venv venv
)

REM Activation
call venv\Scripts\activate.bat

REM Installation des dépendances
echo [INFO] Installation des dependances...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet MetaTrader5

echo.
echo Que voulez-vous lancer ?
echo   1. Dashboard de surveillance (necessite MT5 lance)
echo   2. Backtest de la strategie
echo   3. Quitter
echo.
set /p choice="Votre choix (1-3): "

if "%choice%"=="1" (
    echo [INFO] Lancement du dashboard sur http://localhost:8501
    streamlit run dashboard/dashboard.py
) else if "%choice%"=="2" (
    echo [INFO] Lancement du backtest...
    python backtest/backtest.py --symbol EURUSD=X --start 2020-01-01 --end 2025-01-01 --plot
    pause
) else (
    echo Au revoir.
    exit /b 0
)
