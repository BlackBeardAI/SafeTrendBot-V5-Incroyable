# SafeTrendBot V5 — Infrastructure Guide

## 🏗 Architecture en production

```
┌─────────────────────────────────────────┐
│           INTERNET                      │
│     (clients avec le bot .exe)          │
└──────────────┬──────────────────────────┘
               │ HTTPS
               ▼
┌─────────────────────────────────────────┐
│           VPS (ce serveur)              │
│                                         │
│  ┌─────────────┐     ┌────────────────┐ │
│  │  Nginx      │────►│  Dashboard     │ │
│  │  (80/443)   │     │  Admin         │ │
│  │             │     │  (port 8443)   │ │
│  └─────────────┘     └────────────────┘ │
│                                         │
│  ┌─────────────┐     ┌────────────────┐ │
│  │  UFW        │     │  Systemd       │ │
│  │  Firewall   │     │  Service       │ │
│  └─────────────┘     └────────────────┘ │
│                                         │
│  ┌─────────────┐     ┌────────────────┐ │
│  │  Fail2ban   │     │  Daily Backup  │ │
│  │  Brute-force│     │  (cron 3AM)    │ │
│  └─────────────┘     └────────────────┘ │
└─────────────────────────────────────────┘
```

---

## 🌐 Accès

| Service | URL | Port |
|---------|-----|------|
| Dashboard Admin | https://217.160.191.107:8443 | 8443 |
| Health Check | https://217.160.191.107:8443/api/health | 8443 |
| Nginx Redirect | http://217.160.191.107 | 80 |

**Login:** `admin` / `Saf3Tr3ndB0t!2026` *(change-le!)*

---

## 🚀 Déploiement

### Méthode 1: Script auto (recommandé)

```bash
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
cd SafeTrendBot-V5-Incroyable
sudo bash deploy.sh
```

### Méthode 2: Manuel

```bash
# 1. Dépendances
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] cryptography

# 2. Certificats SSL
cd admin_dashboard
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"

# 3. Lancer
cd admin_dashboard
python main.py
# → https://localhost:8443
```

---

## 🔐 Sécurité en place

| Couche | Implémentation |
|--------|---------------|
| **Firewall** | UFW — ports 22, 80, 443, 8443 uniquement |
| **Anti brute-force** | Fail2ban — ban après 5 tentatives |
| **Reverse proxy** | Nginx — cache + logs |
| **SSL/TLS** | Certificat auto-signé (remplace par Let's Encrypt pour prod) |
| **Rate limiting** | 10 req/min par IP dans le dashboard |
| **JWT** | Tokens avec expiration 30min |
| **Backup** | Auto quotidien 3AM, conservation 30j |

---

## 📋 Commandes utiles

### Dashboard

```bash
# Voir le statut
systemctl status safetrendbot-dashboard

# Logs en temps réel
journalctl -u safetrendbot-dashboard -f

# Redémarrer
systemctl restart safetrendbot-dashboard

# Désactiver
systemctl stop safetrendbot-dashboard
```

### Firewall

```bash
ufw status verbose          # Voir les règles
ufw allow 8443/tcp          # Ouvrir un port
ufw deny 8080/tcp           # Fermer un port
```

### Backup

```bash
# Backup manuel
/root/SafeTrendBot/backup.sh

# Voir les backups
ls -lh /root/SafeTrendBot/backups/
```

---

## ⚙️ Configuration avancée

### Changer le mot de passe admin

```bash
export ADMIN_PASSWORD="TonNouveauMotDePasseFort123!"
sudo bash deploy.sh
```

### Ajouter un domaine personnalisé

```bash
# DNS: CNAME ton-domaine.com → 217.160.191.107
# Puis édite /etc/nginx/sites-available/safetrendbot

server {
    listen 443 ssl;
    server_name ton-domaine.com;
    
    # Let's Encrypt (recommandé)
    ssl_certificate /etc/letsencrypt/live/ton-domaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ton-domaine.com/privkey.pem;
    
    location / {
        proxy_pass https://127.0.0.1:8443;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Certificat Let's Encrypt (gratuit)

```bash
apt-get install certbot python3-certbot-nginx
certbot --nginx -d ton-domaine.com
# Renouvellement auto
```

---

## 🔁 Mise à jour du serveur

```bash
# 1. Pull les changements
cd /root/SafeTrendBot
git pull

# 2. Redémarrer le service
systemctl restart safetrendbot-dashboard

# 3. Vérifier
systemctl status safetrendbot-dashboard
curl -k https://localhost:8443/api/health
```

---

## 📊 Monitoring

### Voir les connexions actives

```bash
ss -tlnp | grep 8443
```

### Voir les logs d'accès

```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/fail2ban.log
```

### Espace disque

```bash
df -h
du -sh /root/SafeTrendBot/builds/
```

---

## 🆘 Dépannage

| Problème | Solution |
|----------|----------|
| Dashboard ne répond pas | `systemctl restart safetrendbot-dashboard` |
| Port 8443 fermé | `ufw allow 8443/tcp` |
| Erreur SSL | `openssl req -x509 ...` dans admin_dashboard/ |
| Mot de passe oublié | `export ADMIN_PASSWORD=... && bash deploy.sh` |
| Bot ne se connecte pas au dashboard | Vérifie l'IP publique dans builder.py |

---

## 🎯 Checklist avant vente

- [ ] Dashboard accessible depuis l'extérieur
- [ ] Certificat SSL valide (ou auto-signé accepté)
- [ ] Firewall configuré
- [ ] Fail2ban actif
- [ ] Backup quotidien configuré
- [ ] Mot de passe admin changé
- [ ] URL admin injectée dans builder.py
- [ ] Test build généré et fonctionnel
- [ ] Premier client testé (activation + utilisation)

---

## 📞 Support

Email: contact@safetrendbot.com
Dashboard: https://217.160.191.107:8443

---

**SafeTrendBot V5 — Infrastructure prête pour le business.**
