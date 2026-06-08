#!/bin/bash
# ===================================================
#  Publication SafeTrendBot sur GitHub (privé)
# ===================================================

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Publication SafeTrendBot sur GitHub (privé)           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ===================================================================
# 1. Vérifier git
# ===================================================================
echo "[1/6] Vérification de Git..."
if ! command -v git &> /dev/null; then
    echo "      Git non installé."
    echo "      Installer : sudo apt install git"
    exit 1
fi
echo "      ✓ $(git --version)"
echo ""

# ===================================================================
# 2. Vérifier GitHub CLI (optionnel)
# ===================================================================
echo "[2/6] Vérification de GitHub CLI (gh)..."
USE_GH=0
if command -v gh &> /dev/null; then
    echo "      ✓ $(gh --version | head -1)"
    USE_GH=1
else
    echo "      gh non installé (optionnel mais recommandé)"
    echo "      Installation : https://cli.github.com/"
    read -p "      Continuer sans gh ? [O/n] : " reply
    if [[ "$reply" == "n" || "$reply" == "N" ]]; then
        exit 0
    fi
fi
echo ""

# ===================================================================
# 3. Nom du repo
# ===================================================================
echo "[3/6] Configuration du repository..."
read -p "      Nom du repo (défaut: safetrendbot) : " REPO_NAME
REPO_NAME=${REPO_NAME:-safetrendbot}
echo "      Repo : $REPO_NAME (privé)"
echo ""

# ===================================================================
# 4. Init git local
# ===================================================================
echo "[4/6] Initialisation du dépôt local..."

if [ ! -d ".git" ]; then
    git init -b main
    echo "      ✓ git init OK"
else
    echo "      ✓ Dépôt déjà initialisé"
fi

git add .

if git diff --cached --quiet; then
    echo "      Aucun changement à commiter."
else
    git commit -m "Initial commit - SafeTrendBot v1.0" || {
        echo "      Configurez d'abord votre identité git :"
        echo "        git config --global user.email \"vous@example.com\""
        echo "        git config --global user.name \"Votre Nom\""
        exit 1
    }
    echo "      ✓ Commit créé"
fi
echo ""

# ===================================================================
# 5. Publication
# ===================================================================
echo "[5/6] Publication sur GitHub..."

if [ "$USE_GH" = "1" ]; then
    if ! gh auth status &> /dev/null; then
        echo "      Connexion à GitHub..."
        gh auth login
    fi

    echo "      Création du repo privé..."
    gh repo create "$REPO_NAME" --private --source=. --remote=origin --push
    echo "      ✓ Repo créé et code poussé"
else
    echo ""
    echo "      === ÉTAPES MANUELLES ==="
    echo ""
    echo "      1. Allez sur : https://github.com/new"
    echo "      2. Remplissez :"
    echo "         - Repository name : $REPO_NAME"
    echo "         - Visibility : PRIVATE"
    echo "         - NE PAS cocher \"Initialize with README\""
    echo "      3. Create repository"
    echo "      4. Copiez l'URL HTTPS"
    echo ""
    read -p "      Collez l'URL HTTPS : " REPO_URL

    git remote remove origin 2>/dev/null || true
    git remote add origin "$REPO_URL"
    git push -u origin main
    echo "      ✓ Code poussé"
fi
echo ""

# ===================================================================
# 6. Final
# ===================================================================
ORIGIN_URL=$(git remote get-url origin)

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✓ PROJET PUBLIÉ AVEC SUCCÈS                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Repo privé : $ORIGIN_URL"
echo ""
echo "Commandes git utiles :"
echo "  git status, git add ., git commit -m \"msg\", git push, git pull"
echo ""
echo "⚠️ IMPORTANT :"
echo "  • Ne JAMAIS committer .env"
echo "  • Vérifier .gitignore avant push"
echo ""
