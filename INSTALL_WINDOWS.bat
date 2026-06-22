@echo off
title SafeTrendBot V5 Installation
echo.
echo ============================================
echo   SafeTrendBot V5 - Installation
echo ============================================
echo.

echo [1/3] Verification de Python...
where python
if errorlevel 1 (
    echo.
    echo ERREUR: Python n'est pas installe.
    echo Telechargez Python 3.11+ sur https://python.org/downloads
    echo IMPORTANT: Cochez "Add Python to PATH" pendant l'installation
    echo.
    pause
    exit /b 1
)
python --version
echo.

echo [2/3] Installation des dependances...
cd /d "%~dp0trading_bot"
echo Dossier: %CD%
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.

echo [3/3] Creation du raccourci bureau...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%USERPROFILE%\Desktop\SafeTrendBot V5.lnk'); $sc.TargetPath = 'pythonw.exe'; $sc.Arguments = '\"%CD%\main.py\"'; $sc.WorkingDirectory = '%CD%'; $sc.Description = 'SafeTrendBot V5'; $sc.Save()"
echo Raccourci cree.
echo.

echo ============================================
echo   INSTALLATION TERMINEE
echo ============================================
echo.
echo Pour lancer SafeTrendBot:
echo   - Double-cliquez le raccourci sur le bureau
echo   - Ou tapez: python "%CD%\main.py"
echo.
pause