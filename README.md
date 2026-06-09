# SafeTrendBot V5 — Trading Bot Impiratable

> 🤖 Bot de trading automatisé multi-broker avec **licence à usage unique**, **chiffrement AES-256**, et **protection anti-tamper**.
>
> 🔒 Chaque build est lié à **un seul PC** — impossible de partager.

---

## 🎯 Ce que c'est

SafeTrendBot V5 est un **système complet** pour vendre un bot de trading sous licence :

| Composant | Description |
|-----------|-------------|
| **🤖 Bot de trading** | 4 modes (Safe/Normal/Aggressive/EXTREME), risk management, UI PyQt6 |
| **🔨 Builder** | Génère des `.exe` uniques avec licence injectée automatiquement |
| **🎛️ Dashboard Admin** | Gère licences, clients, paiements, messages — accessible depuis n'importe où |
| **🛡️ Sécurité** | 7 couches : licence unique, hardware lock, chiffrement, obfuscation, watermark, anti-tamper, auto-destruct |

---

## 🚀 Démarrage rapide

### Pour toi (vendeur/admin)

```bash
# 1. Clone
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
cd SafeTrendBot-V5-Incroyable

# 2. Déploie le serveur (1 commande)
sudo bash deploy.sh
# → Dashboard prêt en 2 minutes

# 3. Lance le Builder GUI
pip install PyQt6 qrcode[pil]
cd trading_bot
python run_builder.py
# → Génère un build, envoie au client
```

**Dashboard :** https://217.160.191.107:8443  
**Login :** `admin` / `Saf3Tr3ndB0t!2026` *(change-le!)*

### Pour le client (acheteur)

```
1. Reçoit un ZIP contenant SafeTrendBot.exe
2. Double-clique → activation automatique sur SON PC
3. Le fichier d'install se supprime
4. Le bot ne fonctionne que sur cet ordinateur
```

---

## 📦 Ce que contient le repo

```
SafeTrendBot-V5-Incroyable/
├── 📁 trading_bot/              ← Le bot + le builder
│   ├── main.py                   ← Point d'entrée du bot client
│   ├── builder.py                ← Générateur de builds (.exe)
│   ├── builder_gui.py            ← Interface graphique du builder
│   ├── run_builder.py            ← Lanceur rapide
│   ├── license_generator.py      ← Génère des licences uniques
│   ├── crypto_payment.py         ← Gestion paiements crypto
│   ├── remote_admin.py           ← Bot Telegram admin
│   ├── build_release.py          ← CI/CD cross-platform
│   ├── headless.py               ← Mode serveur sans UI
│   └── app/
│       ├── core/
│       │   ├── license_manager_v2.py   ← Licence 1 PC = 1 build
│       │   ├── trading_engine_v4.py    ← Moteur de trading
│       │   ├── trading_profiles.py     ← 4 modes + EXTREME
│       │   ├── extreme_guard.py       ← Sécurités mode EXTREME
│       │   ├── encryption.py          ← AES-256-GCM
│       │   ├── watermark.py           ← Traçage invisible
│       │   ├── auto_updater.py        ← Mise à jour auto
│       │   ├── broadcast_client.py    ← Messages admin
│       │   └── anti_tamper.py         ← Détection intrusion
│       ├── ui/                       ← Interface PyQt6
│       └── brokers/                  ← MT5, IB, crypto
│
├── 📁 admin_dashboard/            ← Dashboard web de gestion
│   ├── main.py                   ← API FastAPI (JWT, rate limit)
│   └── static/index.html         ← UI dark mode
│
├── 📁 server/                     ← Ancien serveur d'activation (legacy)
│
├── 📁 .github/workflows/          ← CI/CD GitHub Actions
│
├── 📄 deploy.sh                   ← Déploiement automatique VPS
├── 📄 INFRASTRUCTURE.md           ← Guide admin serveur
├── 📄 README.md                   ← Ce fichier
└── 📄 BUILD_GUIDE.md             ← Guide compilation .exe
```

---

## 🔐 Sécurité — 7 Couches

| # | Couche | Fichier | Protection |
|---|--------|---------|------------|
| 1 | **Licence unique** | `license_manager_v2.py` | Chaque build contient une licence différente |
| 2 | **Hardware lock** | `license_manager_v2.py` | Liée au CPU+MAC+disk (impossible de partager) |
| 3 | **Auto-destruct** | `license_manager_v2.py` | Fichier d'install supprimé après activation |
| 4 | **Chiffrement** | `encryption.py` | AES-256-GCM pour toutes les données |
| 5 | **Obfuscation** | `builder.py` | Cython compile le code en binaire illisible |
| 6 | **Watermark** | `watermark.py` | Traçage invisible (zero-width chars) dans les résultats |
| 7 | **Anti-tamper** | `anti_tamper.py` | Détecte debuggers, VMs, modifications |

---

## 💰 Tarifs & Tiers

| Tier | Prix | Description |
|------|------|-------------|
| 🛡️ **Basic** | $99 | Safe + Normal modes, 3 positions max, 1% risque |
| ⚖️ **Pro** | $199 | Tous les modes, 5 positions, 2% risque |
| 🔥🔥 **EXTREME** | $349 | Mode EXTREME (5% risque, SL 0.8×ATR, TP 4:1), 8 positions |

**Paiement :** Crypto uniquement (BTC, ETH, USDT-TRC20)

---

## 🛠 Workflow A-Z

### 1. Vente
```
Client te contacte
    ↓
Tu ouvres le Builder GUI: python run_builder.py
    ↓
Tu choisis le tier, rentres l'email
    ↓
Le Builder génère un ZIP unique avec licence injectée
```

### 2. Livraison
```
Tu envoies le ZIP au client (Telegram, WeTransfer, email)
    ↓
Client télécharge → double-clique SafeTrendBot.exe
```

### 3. Activation (automatique)
```
Bot démarre
    ↓
LicenseManagerV2 lit la licence pré-injectée
    ↓
Vérification hardware fingerprint
    ↓
Activation → sauvegarde hardware_id
    ↓
Auto-suppression du fichier d'install
    ↓
Chiffrement AES-256 des données
    ↓
✅ Bot prêt!
```

### 4. Contrôle à distance
```
Tu te connectes au Dashboard
    ↓
Tu peux:
    • Voir les licences actives
    • Révoquer un client (bloque son bot)
    • Envoyer un message à tous les bots
    • Pousser une mise à jour
```

---

## 🎛 Modes de Trading

| Mode | Risque | Positions | R:R | SL | TP |
|------|--------|-----------|-----|----|----|
| 🛡️ Safe | 0.5% | 2 | 2.5:1 | 2.0×ATR | 5.0×ATR |
| ⚖️ Normal | 1.0% | 3 | 2.0:1 | 1.5×ATR | 3.0×ATR |
| 🔥 Aggressive | 2.0% | 5 | 1.5:1 | 1.2×ATR | 1.8×ATR |
| 🔥🔥 EXTREME | 5.0% | 8 | 4.0:1 | 0.8×ATR | 3.2×ATR |

**EXTREME** : arrêt auto à 3 pertes consécutives, -8% daily, -30% drawdown, 48h max.

---

## 🌐 Dashboard Admin

| Page | Fonction |
|------|----------|
| 📊 **Vue d'ensemble** | Stats temps réel (licences, revenus) |
| 🔑 **Licences** | Générer, révoquer, réactiver |
| 💰 **Paiements** | Créer demande, vérifier, confirmer |
| 📢 **Messages** | Broadcast à tous les bots clients |
| 📋 **Activité** | Journal complet (IP, date, action) |

**Accès :** `https://217.160.191.107:8443`  
**Auth :** JWT 30min + rate limiting 10 req/min

---

## 🚀 Infrastructure

Le VPS est déjà configuré avec :

| Service | Statut |
|---------|--------|
| Dashboard | ✅ Actif (port 8443, HTTPS auto-signé) |
| Nginx | ✅ Reverse proxy (80→8443) |
| UFW Firewall | ✅ Ports 22,80,443,8443 |
| Fail2ban | ✅ Anti brute-force |
| Backup | ✅ Quotidien 3AM, rétention 30j |
| Systemd | ✅ Auto-démarrage au boot |

**Guide complet :** `INFRASTRUCTURE.md`

---

## 🔧 Commandes

### Builder
```bash
cd trading_bot
python run_builder.py              # GUI
python builder.py --tier extreme --email client@ex.com  # CLI
```

### Dashboard
```bash
cd admin_dashboard
python main.py                     # Local
# OU service systemd:
systemctl status safetrendbot-dashboard
journalctl -u safetrendbot-dashboard -f
```

### Paiement crypto
```bash
python crypto_payment.py new --email client@ex.com --tier extreme
python crypto_payment.py check --id ABCD1234
python crypto_payment.py confirm --id ABCD1234 --license XXXX-XXXX
```

### Bot (mode paper)
```bash
python headless.py --paper --symbols EURUSD,GBPUSD
```

---

## ⚠️ Avertissements

1. **Trading = risque.** Aucune stratégie ne garantit un gain.
2. **Paper trade 30 jours** minimum avant capital réel.
3. **Mode EXTREME** peut perdre jusqu'à 30% du capital.
4. **Build lié à un PC.** Nouvelle machine = nouvelle licence.
5. **Conserve la licence.** Sans elle, réinstallation impossible.

---

## 📞 Support

- **Dashboard :** https://217.160.191.107:8443
- **Email :** contact@safetrendbot.com

---

**SafeTrendBot V5 — Built for traders, secured for business.**
