# SafeTrendBot V5 — Documentation Complète

## 🎯 Vue d'ensemble

SafeTrendBot V5 est un bot de trading automatisé avec un système de **licence à usage unique**, **chiffrement AES-256**, et une **protection anti-tamper**.

Ce repository contient :
- **Le bot de trading** (stratégies, risk management, UI)
- **Le générateur de builds** (crée des .exe uniques pour chaque client)
- **Le dashboard admin** (gestion à distance via web)
- **Les outils de sécurité** (chiffrement, watermark, auto-update)

---

## 🚀 Démarrage rapide — Pour l'administrateur (TOI)

### 1. Clone le repo

```bash
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
cd SafeTrendBot-V5-Incroyable/trading_bot
pip install -r requirements.txt
```

### 2. Lance le Builder GUI

```bash
python run_builder.py
```

L'interface s'ouvre :
1. Sélectionne le tier (Basic $99 / Pro $199 / EXTREME $349)
2. Rentre l'email du client
3. Clique **"GÉNÉRER LE BUILD"**
4. Envoie le ZIP dans `builds/` au client

### 3. Gère les clients via le Dashboard

```bash
cd ../admin_dashboard
python main.py
```

Accède à `https://localhost:8443` :
- Login : `admin` / `safetrendbot2026`
- Voir les licences actives
- Révoquer une licence
- Envoyer un message broadcast à tous les bots
- Confirmer un paiement crypto

---

## 🔐 Système de Sécurité — 7 Couches

| Couche | Fichier | Protection |
|--------|---------|------------|
| **1. Licence unique** | `license_manager_v2.py` | Chaque build contient une licence unique à usage unique |
| **2. Hardware lock** | `license_manager_v2.py` | La licence est liée au CPU+MAC+disk du PC client |
| **3. Auto-destruct** | `license_manager_v2.py` | Le fichier d'installation se supprime après activation |
| **4. Chiffrement** | `encryption.py` | AES-256-GCM pour config, journal, données paper |
| **5. Obfuscation** | `builder.py` | Cython compile les modules critiques en binaire |
| **6. Watermark** | `watermark.py` | Traçage invisible (zero-width chars) dans les résultats |
| **7. Anti-tamper** | `anti_tamper.py` | Détecte debuggers, VMs, modifications de fichiers |

---

## 📦 Workflow Complet — De la vente au client

### Phase 1: Vente

```
Client te contacte (Telegram/email)
    ↓
Tu ouvres le Builder GUI: python run_builder.py
    ↓
Tu sélectionnes le tier et rentre l'email client
    ↓
Le Builder génère:
    - Une licence unique (XXXX-XXXX-XXXX-XXXX)
    - Un .exe avec la licence injectée
    - Un ZIP prêt à envoyer
```

### Phase 2: Livraison

```
Tu envoies le ZIP au client (WeTransfer, Telegram, email)
    ↓
Le client télécharge et double-clique SafeTrendBot.exe
```

### Phase 3: Activation (Automatique)

```
Le bot démarre
    ↓
LicenseManagerV2 lit la licence pré-injectée
    ↓
Vérification hardware fingerprint (CPU + MAC + disk)
    ↓
Première activation → sauvegarde du hardware_id
    ↓
Le fichier d'installation s'auto-supprime
    ↓
Les données sont chiffrées (AES-256-GCM)
    ↓
✅ Bot prêt à trader!
```

### Phase 4: Utilisation & Contrôle

```
Le client utilise le bot normalement
    ↓
Tu peux:
    - Voir les stats dans le Dashboard
    - Envoyer un message broadcast (s'affiche au prochain démarrage)
    - Révoquer la licence (bloque le bot)
    - Pousser une mise à jour
```

---

## 🛠 Architecture

```
SafeTrendBot-V5-Incroyable/
├── trading_bot/
│   ├── main.py                          ← Point d'entrée du bot
│   ├── builder.py                       ← Générateur de builds (.exe)
│   ├── builder_gui.py                   ← Interface graphique du builder
│   ├── run_builder.py                   ← Lanceur rapide du builder
│   ├── license_generator.py             ← Générateur de licences
│   ├── crypto_payment.py                ← Gestion des paiements crypto
│   ├── remote_admin.py                  ← Bot Telegram pour l'admin
│   ├── build_release.py                 ← Build cross-platform (CI)
│   ├── headless.py                      ← Mode serveur sans UI
│   ├── app/
│   │   ├── core/
│   │   │   ├── license_manager_v2.py    ← Licence V2 (usage unique)
│   │   │   ├── license_stub.py          ← Placeholder pour injection
│   │   │   ├── trading_engine_v4.py     ← Moteur de trading
│   │   │   ├── trading_profiles.py      ← 4 modes + EXTREME
│   │   │   ├── extreme_guard.py         ← Sécurités mode EXTREME
│   │   │   ├── encryption.py            ← AES-256-GCM
│   │   │   ├── watermark.py             ← Traçage invisible
│   │   │   ├── auto_updater.py          ← Mise à jour auto
│   │   │   ├── broadcast_client.py      ← Messages admin
│   │   │   ├── anti_tamper.py           ← Détection intrusion
│   │   │   ├── license_manager.py       ← Ancienne version (serveur)
│   │   │   └── ...
│   │   ├── ui/                          ← Interface PyQt6
│   │   └── brokers/                     ← Adaptateurs MT5/IB/etc
│   └── bot/                             ← Telegram alerts, news
├── admin_dashboard/
│   ├── main.py                          ← API FastAPI sécurisée
│   └── static/
│       └── index.html                   ← Interface web admin
├── server/
│   └── activation_server.py            ← Serveur de licence (legacy)
└── .github/workflows/
    └── build-release.yml               ← CI/CD GitHub Actions
```

---

## 🎛 Modes de Trading

| Mode | Risque/trade | Positions | R:R | Pour qui |
|------|-------------|-----------|-----|----------|
| 🛡️ Safe | 0.5% | 2 | 2.5:1 | Débutants, capital important |
| ⚖️ Normal | 1% | 3 | 2:1 | Utilisateurs standards |
| 🔥 Aggressive | 2% | 5 | 1.5:1 | Traders expérimentés |
| 🔥🔥 EXTREME | 5% | 8 | 4:1 | Recherche rendement max |

**EXTREME** inclut :
- SL ultra-serré (0.8×ATR), TP très loin (4:1)
- Max 3 pertes consécutives → auto-lock
- Max 15 trades/jour, cooldown 5min
- Arrêt à -8% journalier / -30% drawdown
- Désactivation auto après 48h (recharge PIN requise)

---

## 💰 Tarifs

| Tier | Prix | Description |
|------|------|-------------|
| Basic | $99 | 3 positions max, modes Safe/Normal |
| Pro | $199 | 5 positions max, tous les modes |
| EXTREME | $349 | 8 positions, mode EXTREME débloqué |

**Paiement :** Crypto uniquement (BTC, ETH, USDT-TRC20)

---

## 🔧 Commandes Utiles

### Générer un build (CLI)

```bash
python builder.py --tier extreme --email client@ex.com
```

### Générer des licences seules

```bash
python license_generator.py generate 50
```

### Vérifier un paiement crypto

```bash
python crypto_payment.py check --id ABCD1234
```

### Confirmer un paiement + générer build

```bash
python crypto_payment.py confirm --id ABCD1234 --license XXXX-XXXX
```

### Lancer le dashboard admin

```bash
cd admin_dashboard
python main.py
# → https://localhost:8443
```

### Lancer le bot en mode paper

```bash
python headless.py --paper --symbols EURUSD,GBPUSD
```

---

## 🌐 Dashboard Admin

Le dashboard permet de gérer tous les aspects commerciaux :

| Page | Fonction |
|------|----------|
| **📊 Vue d'ensemble** | Stats licences, paiements, revenus |
| **🔑 Licences** | Voir, révoquer, réactiver, générer |
| **💰 Paiements** | Créer, vérifier, confirmer |
| **📢 Messages** | Broadcast à tous les bots clients |
| **📋 Activité** | Journal des actions (IP, date) |

**Accès :** `https://VOTRE_IP:8443`

---

## 🔄 Mise à jour Auto

Les bots clients vérifient automatiquement les mises à jour au démarrage.

**Pour publier une mise à jour :**
1. Modifie le code
2. Génère un patch ZIP
3. Upload sur le serveur admin
4. Mets à jour `version.json`
5. Les bots clients téléchargent et appliquent automatiquement

---

## 🛡 Sécurité Avancée

### Chiffrement des données

```python
from app.core.encryption import encrypt_sensitive_data
encrypt_sensitive_data()  # Chiffre tout ~/.safetrendbot/
```

### Watermark invisible

```python
from app.core.watermark import WatermarkManager
wm = WatermarkManager("XXXX-XXXX", "John Doe", "extreme")
report = wm.stamp_report("Profits: +5%")  # Ajoute watermark invisible
```

### Révocation à distance

```bash
# Via dashboard
POST /api/licenses/XXXX-XXXX/revoke

# Via Telegram admin
/revoke XXXX-XXXX
```

---

## 🚀 Hébergement du Dashboard

### Sur le VPS (recommandé)

```bash
# Le dashboard est déjà prêt
export STB_ADMIN_HASH=$(python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('TON_MDP'))")
cd admin_dashboard
nohup python main.py &

# Accès: https://217.160.191.107:8443
# Change l'IP par ton IP publique
```

### Avec Docker (optionnel)

```dockerfile
FROM python:3.11
WORKDIR /app
COPY admin_dashboard/ .
RUN pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] cryptography
EXPOSE 8443
CMD ["python", "main.py"]
```

---

## 📞 Support

- **Email :** contact@safetrendbot.com
- **Telegram :** @safetrendbot_support
- **Dashboard :** https://217.160.191.107:8443

---

## ⚠️ Avertissements

1. **Le trading comporte des risques.** Aucune stratégie ne garantit un gain.
2. **Testez en paper trading** avant tout capital réel.
3. **Le mode EXTREME** peut entraîner des pertes importantes (jusqu'à 30%).
4. **Chaque build est lié à un PC.** En cas de changement de machine, une nouvelle licence est requise.
5. **Conservez vos licences.** Sans la licence, le bot ne peut pas être réinstallé.

---

## 📜 Licence Projet

Propriétaire — Tous droits réservés.
Distribution commerciale interdite sans autorisation.

---

**SafeTrendBot V5 — Built for traders, secured for business.**
