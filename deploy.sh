#!/bin/bash
# SafeTrendBot — Deploy Script
# Usage: sudo bash deploy.sh

set -e

echo "🚀 SafeTrendBot Infrastructure Deploy"
echo "======================================"

# ─── CONFIG ───
DASHBOARD_DIR="/root/SafeTrendBot/admin_dashboard"
APP_DIR="/root/SafeTrendBot/trading_bot"
DOMAIN="${DOMAIN:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Saf3Tr3ndB0t!2026}"

# ─── 1. SYSTEM UPDATE ───
echo "[1/8] System update..."
apt-get update -y
apt-get upgrade -y
apt-get install -y curl wget git unzip ufw fail2ban nginx

# ─── 2. FIREWALL ───
echo "[2/8] Firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (nginx redirect)
ufw allow 443/tcp   # HTTPS
ufw allow 8443/tcp  # Dashboard
ufw --force enable
echo "   ✅ Firewall actif (22, 80, 443, 8443)"

# ─── 3. FAIL2BAN ───
echo "[3/8] Fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true
EOF
systemctl restart fail2ban
echo "   ✅ Fail2ban actif"

# ─── 4. NGINX REVERSE PROXY ───
echo "[4/8] Nginx..."
cat > /etc/nginx/sites-available/safetrendbot << EOF
server {
    listen 80;
    server_name _;
    
    # Redirect HTTP to HTTPS dashboard
    location / {
        proxy_pass https://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
ln -sf /etc/nginx/sites-available/safetrendbot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
echo "   ✅ Nginx reverse proxy"

# ─── 5. INSTALL DEPS ───
echo "[5/8] Python deps..."
pip3 install -q fastapi uvicorn python-jose[cryptography] passlib[bcrypt] cryptography pyinstaller cython qrcode pillow pyqt6 numpy requests 2>/dev/null || true
echo "   ✅ Python dependencies"

# ─── 6. CREATE SERVICE ───
echo "[6/8] Systemd service..."
cat > /etc/systemd/system/safetrendbot-dashboard.service << EOF
[Unit]
Description=SafeTrendBot Admin Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DASHBOARD_DIR
ExecStart=/usr/bin/python3 -c "from main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8443, ssl_keyfile='key.pem', ssl_certfile='cert.pem')"
Restart=always
RestartSec=10
Environment="STB_ADMIN_HASH=$(python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('$ADMIN_PASSWORD'))")"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable safetrendbot-dashboard
systemctl start safetrendbot-dashboard
echo "   ✅ Dashboard service actif"

# ─── 7. DIRS & PERMISSIONS ───
echo "[7/8] Directories..."
mkdir -p /root/SafeTrendBot/builds
mkdir -p /root/SafeTrendBot/backups
chmod 700 /root/SafeTrendBot
echo "   ✅ Dirs created"

# ─── 8. BACKUP SCRIPT ───
echo "[8/8] Backup cron..."
cat > /root/SafeTrendBot/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/root/SafeTrendBot/backups"
mkdir -p $BACKUP_DIR
tar -czf "$BACKUP_DIR/dashboard_$DATE.tar.gz" /root/SafeTrendBot/admin_dashboard 2>/dev/null
tar -czf "$BACKUP_DIR/licenses_$DATE.tar.gz" /root/SafeTrendBot/trading_bot/licenses.json 2>/dev/null
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
EOF
chmod +x /root/SafeTrendBot/backup.sh

# Cron: backup daily at 3AM
echo "0 3 * * * root /root/SafeTrendBot/backup.sh" > /etc/cron.d/safetrendbot-backup
echo "   ✅ Backup daily 3AM"

# ─── STATUS ───
echo ""
echo "========================================"
echo "🎉 SafeTrendBot déployé!"
echo "========================================"
echo ""
echo "Dashboard: https://$(curl -s https://api.ipify.org):8443"
echo "Login:    admin"
echo "Password: $ADMIN_PASSWORD"
echo ""
echo "Change password: export ADMIN_PASSWORD=... && bash deploy.sh"
echo ""
echo "Commands:"
echo "  systemctl status safetrendbot-dashboard"
echo "  journalctl -u safetrendbot-dashboard -f"
echo "  /root/SafeTrendBot/backup.sh"
echo ""
