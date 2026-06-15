# SafeTrendBot V5 — Système de Vente Crypto Directe

## 🎯 Concept

**Paiement unique = Licence permanente** — Pas d'abonnement, pas de renouvelable.

Le client paie une fois en crypto (BTC/ETH/USDT) et reçoit une licence qu'il peut utiliser indéfiniment sur son PC.

---

## 💰 Comment Ça Marche

```
1. Client visite /buy
2. Entre son email + choisit crypto (BTC/ETH/USDT)
3. Reçoit l'adresse wallet + montant exact
4. Effectue le transfert depuis son portefeuille
5. Admin confirme le paiement (ou automatique si configuré)
6. Client reçoit sa licence + lien téléchargement
7. Client télécharge le bot + active avec sa clé
```

---

## 🚀 Installation Rapide

```bash
cd /root/SafeTrendBot-V5-Incroyable/trading_bot/crypto_sales

# Installer dépendances
pip install flask requests

# Configurer vos wallets
export BTC_WALLET="votre_adresse_btc"
export ETH_WALLET="votre_adresse_eth"  
export USDT_TRC20_WALLET="votre_adresse_usdt_tron"

# Lancer le serveur
python crypto_sales_server.py
```

---

## ⚙️ Configuration

### Variables d'Environnement

| Variable | Description | Exemple |
|----------|-------------|---------|
| `BTC_WALLET` | Adresse Bitcoin | `bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh` |
| `ETH_WALLET` | Adresse Ethereum | `0x71C7656EC7ab88b098defB751B7401B5f6d8976F` |
| `USDT_ERC20_WALLET` | Adresse USDT (ERC20) | `0x71C7656EC7ab88b098defB751B7401B5f6d8976F` |
| `USDT_TRC20_WALLET` | Adresse USDT (TRC20) | `TDtd5bLSo7tN2FbKqN8K2M1rXK6M2N5B7j` |
| `ADMIN_USER` | Identifiant admin | `admin` |
| `ADMIN_PASS_HASH` | Hash du mot de passe | (généré automatiquement) |
| `PORT` | Port du serveur | `5001` |
| `SECRET_KEY` | Clé secrète session | `quelque-chose-de-long` |

### Modifier le Prix

```bash
# Via l'interface admin
curl -X POST http://localhost:5001/api/set_price -d "price=397"
```

Ou directement dans la DB:
```sql
UPDATE settings SET value = '397' WHERE key = 'price_usd';
```

---

## 📂 Structure des Fichiers

```
crypto_sales/
├── crypto_payment.py         # Module de paiement (core)
├── crypto_sales_server.py    # Serveur Flask
├── payments.db              # Base de données SQLite
├── static/                  # CSS, images (à venir)
└── templates/               # Templates HTML (à venir)
```

---

## 🌐 Endpoints

### Public

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | Landing page |
| `/buy` | GET/POST | Page d'achat |
| `/payment/<id>` | GET | Suivi du paiement |
| `/download/<key>` | GET | Téléchargement |
| `/api/stats` | GET | Stats publiques |

### Admin

| Route | Méthode | Description |
|-------|---------|-------------|
| `/admin/login` | GET/POST | Connexion admin |
| `/admin` | GET | Dashboard |
| `/admin/confirm/<id>` | GET | Confirmer un paiement |
| `/admin/license/<key>` | GET | Détail licence |

---

## 🔐 Sécurité

### Checklist avant mise en production

- [ ] **Changer les wallets** par vos vraies adresses
- [ ] **Changer le mot de passe admin** (`ADMIN_USER` / `ADMIN_PASS_HASH`)
- [ ] **Activer HTTPS** (via nginx/Caddy + let's encrypt)
- [ ] **Générer SECRET_KEY** (clé longue et aléatoire)
- [ ] **Firewall**: n'ouvrir que le port 443 (HTTPS)
- [ ] **Backup régulier** de `payments.db`

### Générer un nouveau hash de mot de passe

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash('votre_nouveau_mot_de_passe'))
```

---

## 📊 Dashboard Admin

Accessible via `/admin/login`

Fonctionnalités:
- Vue d'ensemble des ventes (total, revenus, en attente)
- Liste des paiements avec filtres (pending/completed/expired)
- Confirmation manuelle des paiements
- Détail des licences vendues

---

## 🔄 Workflow de Confirmation

### Méthode 1: Manuelle (Recommandé pour commencer)

1. Client effectue le paiement
2. Vous vérifiez sur blockchain.info / etherscan.io
3. Vous allez sur `/admin`
4. Cliquez "✓ Confirmer" pour le paiement
5. Licence générée automatiquement

### Méthode 2: Semi-automatique

Ajoutez un webhook depuis votre wallet provider:
```bash
# Quand un paiement est reçu, votre wallet notifie votre serveur
curl -X POST http://votre-serveur.com/api/webhook/payment \
  -d '{"tx_hash": "xxx", "amount": 0.0045, "currency": "BTC"}'
```

### Méthode 3: Pleinement automatique

Utilisez une API comme:
- [Blockstream API](https://blockstream.info/api/) (BTC gratuit)
- [Etherscan API](https://etherscan.io/apis) (ETH/USDT)

Configurez dans `crypto_payment.py` la fonction `verify_btc_payment()` et `verify_eth_payment()`.

---

## 🚢 Déploiement Production

### Option 1: VPS Simple

```bash
# Installer ufw, nginx, certbot
sudo apt install nginx certbot python3-pip
pip install flask gunicorn

# Créer service systemd
sudo nano /etc/systemd/system/safetrendbot-sales.service
```

```ini
[Unit]
Description=SafeTrendBot Sales Server
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/trading_bot/crypto_sales
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5001 crypto_sales_server:APP
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 2: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY crypto_sales/ /app/
RUN pip install flask gunicorn requests
EXPOSE 5001
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "crypto_sales_server:APP"]
```

---

## 💡 Tips

### Prix en crypto dynamiques

Le système récupère automatiquement les prix depuis CoinGecko et calcule le montant en crypto correspondant au prix USD.

### Recevoir des notifications

Ajoutez un bot Telegram pour être notifié des ventes:

```python
def notify_sale(payment):
    import requests
    token = "VOTRE_BOT_TOKEN"
    chat_id = "VOTRE_CHAT_ID"
    msg = f"🎉 Nouvelle vente!\n\n{payment['crypto']}: {payment['amount_crypto']}\nEmail: {payment['email']}\nPrix: ${payment['amount_usd']}"
    requests.post(f"https://api.telegram.org/{token}/sendMessage",
                  json={"chat_id": chat_id, "text": msg})
```

### Intégrer un chatbot de confirmation

Après le paiement, le client peut vérifier le statut via:
- Un bot Telegram
- Un email automatique
- La page `/payment/<id>`

---

## 📈 Estimation de Revenus

| Ventes/mois | Panier Moyen | Revenus |
|-------------|--------------|---------|
| 5 | $297 | $1,485 |
| 10 | $297 | $2,970 |
| 20 | $297 | $5,940 |
| 50 | $297 | $14,850 |

**Sans abonnement**, vous devez constamment acquérir de nouveaux clients, mais chaque vente = profit pur.

---

## 🆘 Support

- Logs: stdout du serveur
- DB: `payments.db` (SQLite)
- Vérifier les payments: `/admin`

---

*Document mis à jour le 15 juin 2026 — SafeTrendBot V5.3.0*