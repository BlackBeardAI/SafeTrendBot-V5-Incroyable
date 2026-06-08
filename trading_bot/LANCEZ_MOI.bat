@echo off
chcp 65001 >nul 2>&1
title SafeTrendBot

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Environnement non trouve - lancement de la reparation...
    echo.
    call REPARER.bat
)

venv\Scripts\python.exe main.py
if errorlevel 1 (
    echo.
    echo Erreur au lancement. Consultez les logs ci-dessus.
    echo Si l'erreur persiste, lancez REPARER.bat
    pause
)
