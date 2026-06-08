@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title SafeTrendBot - Publication sur GitHub (privé)

color 0B
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║        Publication SafeTrendBot sur GitHub (privé)           ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM ===================================================================
REM  1. VÉRIFIER GIT
REM ===================================================================
echo [1/6] Vérification de Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo      Git n'est pas installé.
    echo      Téléchargement en cours...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe' -OutFile '%TEMP%\git_installer.exe'}"
    echo      Lancez l'installation qui va s'ouvrir, puis relancez ce script.
    start "" "%TEMP%\git_installer.exe"
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('git --version') do echo      ✓ %%v
echo.

REM ===================================================================
REM  2. VÉRIFIER GITHUB CLI (optionnel mais conseillé)
REM ===================================================================
echo [2/6] Vérification de GitHub CLI ^(gh^)...
gh --version >nul 2>&1
if errorlevel 1 (
    echo      GitHub CLI non détecté.
    echo.
    echo      Il facilite énormément la création du repo privé.
    echo      Télécharger : https://cli.github.com/
    echo.
    echo      Voulez-vous continuer SANS gh ? ^(procédure manuelle^)
    choice /c ON /m "   [O]ui, continuer sans  [N]on, installer gh d'abord"
    if errorlevel 2 (
        start https://cli.github.com/
        exit /b 0
    )
    set USE_GH=0
) else (
    for /f "tokens=*" %%v in ('gh --version ^| findstr /r "^gh"') do echo      ✓ %%v
    set USE_GH=1
)
echo.

REM ===================================================================
REM  3. NOM DU REPO
REM ===================================================================
echo [3/6] Configuration du repository...
set /p REPO_NAME="Nom du repo ^(ex: safetrendbot^) : "
if "!REPO_NAME!"=="" set REPO_NAME=safetrendbot

echo.
echo      Repo : !REPO_NAME! ^(privé^)
echo.

REM ===================================================================
REM  4. INITIALISATION GIT LOCAL
REM ===================================================================
echo [4/6] Initialisation du dépôt local...

if not exist ".git" (
    git init
    if errorlevel 1 (
        echo      ERREUR : Impossible d'initialiser le dépôt.
        pause
        exit /b 1
    )
    echo      ✓ git init OK
) else (
    echo      ✓ Dépôt déjà initialisé
)

REM Branche main par défaut
git symbolic-ref HEAD refs/heads/main >nul 2>&1

echo      Ajout des fichiers...
git add .
if errorlevel 1 (
    echo      ERREUR : git add a échoué
    pause
    exit /b 1
)

REM Vérifier qu'il y a des changements
git diff --cached --quiet
if not errorlevel 1 (
    echo      Aucun changement à commiter.
) else (
    echo      Création du commit initial...
    git -c user.email="local@safetrendbot.local" -c user.name="SafeTrendBot" commit -m "Initial commit - SafeTrendBot v1.0" >nul
    if errorlevel 1 (
        echo      Note : si git demande votre identité, configurez-la :
        echo        git config --global user.email "vous@example.com"
        echo        git config --global user.name "Votre Nom"
        echo      Puis relancez ce script.
        pause
        exit /b 1
    )
    echo      ✓ Commit créé
)
echo.

REM ===================================================================
REM  5. CRÉATION ET PUSH VERS GITHUB
REM ===================================================================
echo [5/6] Publication sur GitHub...

if "!USE_GH!"=="1" (
    REM Avec GitHub CLI : tout en une commande
    echo      Vérification de l'authentification gh...
    gh auth status >nul 2>&1
    if errorlevel 1 (
        echo      Vous devez vous connecter à GitHub d'abord.
        echo      Lancement de gh auth login...
        gh auth login
        if errorlevel 1 (
            echo      Authentification annulée.
            pause
            exit /b 1
        )
    )

    echo      Création du repo privé sur GitHub...
    gh repo create !REPO_NAME! --private --source=. --remote=origin --push
    if errorlevel 1 (
        echo      ERREUR : Création du repo échouée.
        echo      Le nom existe peut-être déjà. Essayez un autre nom.
        pause
        exit /b 1
    )
    echo      ✓ Repo privé créé et code poussé !
) else (
    REM Sans gh : instructions manuelles
    echo.
    echo      === ÉTAPES MANUELLES ===
    echo.
    echo      1. Allez sur : https://github.com/new
    echo      2. Remplissez :
    echo         - Repository name : !REPO_NAME!
    echo         - Visibility : PRIVATE ^(important !^)
    echo         - NE PAS cocher "Initialize with README"
    echo      3. Cliquez "Create repository"
    echo      4. Copiez l'URL HTTPS affichée ^(ex: https://github.com/vous/!REPO_NAME!.git^)
    echo.
    set /p REPO_URL="      Collez l'URL HTTPS ici : "
    if "!REPO_URL!"=="" (
        echo      URL vide. Abandon.
        pause
        exit /b 1
    )

    REM Vérifier si origin existe déjà
    git remote | findstr /x "origin" >nul
    if not errorlevel 1 (
        git remote remove origin
    )

    git remote add origin !REPO_URL!
    echo      ✓ Remote ajoutée
    echo.
    echo      Push en cours...
    echo      ^(GitHub va demander votre username et un TOKEN^)
    echo      ^(Token : https://github.com/settings/tokens → classic → "repo"^)
    echo.
    git push -u origin main
    if errorlevel 1 (
        echo      ERREUR : push échoué.
        echo      Vérifiez l'URL et vos identifiants.
        pause
        exit /b 1
    )
    echo      ✓ Code poussé sur GitHub
)
echo.

REM ===================================================================
REM  6. VÉRIFICATION
REM ===================================================================
echo [6/6] Vérifications finales...

REM Afficher les remotes
for /f "tokens=*" %%u in ('git remote get-url origin 2^>nul') do set ORIGIN_URL=%%u
echo      Remote : !ORIGIN_URL!
echo.

echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║  ✓ PROJET PUBLIÉ AVEC SUCCÈS                                 ║
echo ║                                                              ║
echo ║  Votre repo privé : !ORIGIN_URL!
echo ║                                                              ║
echo ║  Commandes utiles :                                          ║
echo ║    git status               - Voir les changements           ║
echo ║    git add .                - Ajouter les changements        ║
echo ║    git commit -m "message"  - Créer un commit                ║
echo ║    git push                 - Pousser sur GitHub             ║
echo ║    git pull                 - Récupérer les changements      ║
echo ║                                                              ║
echo ║  IMPORTANT :                                                 ║
echo ║    • Ne JAMAIS committer le fichier .env                     ║
echo ║    • Vérifier .gitignore avant chaque push                   ║
echo ║    • Pour collaborer : Settings → Collaborators → Add        ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
pause
exit /b 0
