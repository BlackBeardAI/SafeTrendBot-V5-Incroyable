@echo off
REM Script de diagnostic - identifie les problemes courants
title SafeTrendBot - Diagnostic

echo.
echo ==============================================================
echo   SafeTrendBot - Diagnostic systeme
echo ==============================================================
echo.
echo Ce script va verifier votre systeme et afficher les problemes.
echo.
pause
echo.

echo ---------- 1. VERSION DE WINDOWS ----------
ver
echo.

echo ---------- 2. ARCHITECTURE ----------
echo Architecture : %PROCESSOR_ARCHITECTURE%
if "%PROCESSOR_ARCHITECTURE%"=="x86" (
    echo [PROBLEME] Windows 32-bit detecte. Python 3.12 requiert 64-bit.
)
echo.

echo ---------- 3. DOSSIER COURANT ----------
echo Dossier actuel : %CD%
echo Script lance depuis : %~dp0
echo.
echo Verification des caracteres speciaux dans le chemin...
echo %~dp0 | findstr /C:" " >nul
if not errorlevel 1 (
    echo [AVERTISSEMENT] Le chemin contient des ESPACES.
    echo Cela peut poser probleme. Deplacez le dossier dans C:\SafeTrendBot par exemple.
)
echo.

echo ---------- 4. PYTHON ----------
python --version 2>&1
if errorlevel 1 (
    echo [PROBLEME] Python n'est pas installe ou pas dans le PATH.
    echo Solution : Telecharger Python 3.12 sur https://www.python.org
    echo IMPORTANT : cocher "Add Python to PATH" lors de l'installation.
) else (
    echo Python OK
    where python
)
echo.

echo ---------- 5. PIP ----------
python -m pip --version 2>&1
if errorlevel 1 (
    echo [PROBLEME] pip ne fonctionne pas.
) else (
    echo pip OK
)
echo.

echo ---------- 6. POWERSHELL ----------
powershell -Command "Write-Host 'PowerShell OK'" 2>&1
if errorlevel 1 (
    echo [PROBLEME] PowerShell indisponible ou bloque.
)
echo.

echo ---------- 7. CONNEXION INTERNET ----------
ping -n 1 www.python.org >nul 2>&1
if errorlevel 1 (
    echo [PROBLEME] Pas de connexion internet ou DNS bloque.
) else (
    echo Connexion internet OK
)
echo.

echo ---------- 8. ANTIVIRUS / DEFENDER ----------
echo Si Windows Defender bloque les scripts :
echo Click droit sur install.bat ^> Proprietes ^> Debloquer ^> OK
echo.

echo ---------- 9. DROITS ECRITURE ----------
echo test > "%~dp0test_write.tmp" 2>nul
if exist "%~dp0test_write.tmp" (
    echo Droits d'ecriture OK
    del "%~dp0test_write.tmp"
) else (
    echo [PROBLEME] Pas de droits d'ecriture dans ce dossier.
    echo Deplacez le projet dans votre dossier Documents ou Bureau.
)
echo.

echo ---------- 10. FICHIERS DU PROJET ----------
if exist "%~dp0main.py" (echo main.py OK) else (echo [PROBLEME] main.py manquant)
if exist "%~dp0requirements.txt" (echo requirements.txt OK) else (echo [PROBLEME] requirements.txt manquant)
if exist "%~dp0app" (echo dossier app/ OK) else (echo [PROBLEME] dossier app/ manquant)
echo.

echo ==============================================================
echo   FIN DU DIAGNOSTIC
echo ==============================================================
echo.
echo Envoyez-moi le resultat complet de cette fenetre pour aide.
echo (Clic droit dans la fenetre ^> Selectionner tout ^> Copier)
echo.
pause
