@echo off
REM Lance SafeTrendBot en mode debug avec console visible
title SafeTrendBot - Mode Debug

echo.
echo ==============================================================
echo   SafeTrendBot - Lancement en mode DEBUG
echo ==============================================================
echo.
echo Ce mode affiche toutes les erreurs eventuelles.
echo La console reste ouverte pour diagnostic.
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [ERREUR] Environnement virtuel introuvable.
    echo Lancez d'abord install.bat
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

if not exist "main.py" (
    echo [ERREUR] main.py introuvable.
    pause
    exit /b 1
)

echo Lancement de Python...
echo.
python main.py

echo.
echo ==============================================================
echo   Application fermee
echo ==============================================================
echo.
echo Si vous voyez des erreurs ci-dessus, copiez-les pour support.
echo.
pause
