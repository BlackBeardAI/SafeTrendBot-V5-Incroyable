#!/bin/bash
# Installateur shell pour SafeTrendBot V5 — Linux/macOS
# Usage: ./install.sh

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo ""
    echo "========================================"
    echo "  $1"
    echo "========================================"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 non trouvé${NC}"
        exit 1
    fi
    VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✅ Python $VERSION${NC}"
}

install_deps() {
    print_header "Installation dépendances"
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
}

create_dirs() {
    print_header "Répertoires de données"
    mkdir -p ~/.safetrendbot/{data,logs,profiles,reports}
    echo -e "${GREEN}✅ Répertoires créés dans ~/.safetrendbot/${NC}"
}

setup_systemd() {
    print_header "Service systemd (optionnel)"
    read -p "Créer le service systemd ? [y/N] " reply
    if [[ "$reply" =~ ^[Yy]$ ]]; then
        BOT_DIR=$(pwd)
        cat > ~/.config/systemd/user/safetrendbot.service <<EOF
[Unit]
Description=SafeTrendBot V5
After=network.target

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=/usr/bin/python3 $BOT_DIR/headless.py --paper
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
        systemctl --user daemon-reload
        echo -e "${GREEN}✅ Service créé${NC}"
        echo "   Démarrer: systemctl --user start safetrendbot"
        echo "   Activer:  systemctl --user enable safetrendbot"
    fi
}

# MAIN
print_header "SafeTrendBot V5 — Installateur Shell"
check_python
install_deps
create_dirs
setup_systemd

print_header "Installation terminée"
echo "Lancer:"
echo "  python3 main.py           → UI Desktop"
echo "  python3 headless.py       → Mode headless"
