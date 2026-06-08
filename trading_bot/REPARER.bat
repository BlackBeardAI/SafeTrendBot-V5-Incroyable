@echo off
chcp 65001 >nul 2>&1
title SafeTrendBot - Reparation

echo ============================================
echo   SafeTrendBot - Reparation de l'installation
echo ============================================
echo.

cd /d "%~dp0"
echo Dossier : %CD%
echo.

REM Supprimer l'ancien venv cassé
if exist "venv" (
    echo Suppression de l'ancien environnement...
    rmdir /s /q venv 2>nul
    echo OK - Ancien environnement supprime
) else (
    echo Aucun ancien environnement a supprimer
)
echo.

REM Trouver Python
echo Recherche de Python...
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo ERREUR : Python n'est pas installe ou pas dans le PATH.
        echo.
        echo Telechargez Python depuis : https://www.python.org/downloads/
        echo Cochez bien "Add Python to PATH" pendant l'installation.
        pause
        exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do set PY_VER=%%i
echo OK - %PY_VER%
echo.

REM Créer le nouveau venv
echo Creation du nouvel environnement virtuel...
%PYTHON% -m venv venv
if errorlevel 1 (
    echo ERREUR : Impossible de creer le venv.
    pause
    exit /b 1
)
echo OK - Environnement cree
echo.

REM Activer et installer
echo Installation des dependances...
call venv\Scripts\activate.bat

python -m pip install --upgrade pip --quiet
echo.

echo Installation PyQt6...
pip install PyQt6 --quiet
if errorlevel 1 (echo AVERTISSEMENT PyQt6 ) else echo OK PyQt6

echo Installation numpy pandas...
pip install numpy pandas --quiet
if errorlevel 1 (echo AVERTISSEMENT numpy/pandas) else echo OK numpy pandas

echo Installation yfinance...
pip install yfinance --quiet
if errorlevel 1 (echo AVERTISSEMENT yfinance) else echo OK yfinance

echo Installation requests reportlab...
pip install requests reportlab --quiet
if errorlevel 1 (echo AVERTISSEMENT requests/reportlab) else echo OK requests reportlab

echo Installation MetaTrader5...
pip install MetaTrader5 --quiet
if errorlevel 1 (echo AVERTISSEMENT MetaTrader5 - peut etre normal sur non-Windows) else echo OK MetaTrader5

echo Installation ccxt ib_insync...
pip install ccxt ib_insync --quiet
if errorlevel 1 (echo AVERTISSEMENT ccxt/ib_insync) else echo OK ccxt ib_insync

echo.
echo ============================================
echo   Verification finale...
echo ============================================
python -c "import PyQt6; print('PyQt6 OK')" 2>nul || echo ERREUR PyQt6
python -c "import numpy; print('numpy OK')" 2>nul || echo ERREUR numpy
python -c "import pandas; print('pandas OK')" 2>nul || echo ERREUR pandas
echo.

echo ============================================
echo   Reparation terminee !
echo ============================================
echo.
echo Lancez maintenant : LANCEZ_MOI.bat
echo.
pause
