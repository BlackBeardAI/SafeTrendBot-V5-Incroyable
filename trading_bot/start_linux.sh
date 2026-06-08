#!/bin/bash
# ===================================================
#  Script de démarrage SafeTrendBot - Linux/Debian
# ===================================================

set -e

echo "======================================"
echo "  SafeTrendBot - Démarrage Linux"
echo "======================================"
echo ""

# Vérification de Python
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python 3 n'est pas installé"
    echo "Installation : sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# Création de l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "[INFO] Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activation
source venv/bin/activate

# Installation des dépendances
echo "[INFO] Installation des dépendances..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo ""
echo "Que voulez-vous lancer ?"
echo "  1. Dashboard de surveillance (mode fichier JSON)"
echo "  2. Backtest de la stratégie"
echo "  3. Quitter"
echo ""
read -p "Votre choix (1-3): " choice

case $choice in
    1)
        echo "[INFO] Lancement du dashboard sur http://localhost:8501"
        echo "[INFO] Pour accès distant : --server.address 0.0.0.0"
        streamlit run dashboard/dashboard.py
        ;;
    2)
        echo "[INFO] Lancement du backtest..."
        python backtest/backtest.py --symbol EURUSD=X --start 2020-01-01 --end 2025-01-01 --plot
        ;;
    3)
        echo "Au revoir."
        exit 0
        ;;
    *)
        echo "Choix invalide"
        exit 1
        ;;
esac
