@echo off
chcp 65001 >nul
title SafeTrendBot V5 - Lancement

:: ═══════════════════════════════════════════════════════════════════
:: SafeTrendBot V5 — Lancement Rapide
:: Double-cliquez sur ce fichier pour démarrer le bot
:: ═══════════════════════════════════════════════════════════════════

cd /d "%~dp0"

:: Vérifier si venv existe
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo ERREUR: Environnement non configuré!
    echo.
    echo Lancez d'abord: INSTALLER_WINDOWS.bat
    echo.
    pause
    exit /b 1
)

:: Activer l'environnement
call venv\Scripts\activate.bat

:: Lancer le bot
python main.py

pause