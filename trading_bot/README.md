# SafeTrendBot V5 — Système de Distribution Commerciale

## 🎯 Présentation

Bot de trading automatisé avec système de vente intégré.

**Caractéristiques:**
- 🚀 Installation 100% automatique (1 clic)
- 🔐 Protection anti-piratage (HW-lock)
- 💰 Vente directe en crypto (BTC/ETH/USDT)
- 👥 Gestion des clients intégrée
- 📦 Multi-brokers (MT5, cTrader, XTB, Binance)

---

## 🏗️ Structure du Projet

```
SafeTrendBot-V5-Incroyable/
└── trading_bot/
    ├── build_generator.py        ← 🎯 Génère les .exe clients
    ├── client_manager.py         ← 👥 Base de données clients
    ├── main.py                   ← Interface graphique
    ├── headless.py               ← Mode serveur
    ├── SELF_INSTALL.bat          ← Installateur auto-extractible
    ├── AUTO_INSTALL.bat          ← Installation Python + Build
    ├── app/
    │   ├── core/
    │   │   ├── license_manager.py    # Anti-piratage
    │   │   └── trading_engine.py     # Moteur de trading
    │   └── brokers/                   # Adaptateurs broker
    ├── builder/                       # Outils de build
    ├── crypto_sales/                  # Serveur vente crypto
    └── requirements.txt
```

---

## 🚀 Démarrage Rapide

### 1. Sur TON PC (Développement)

```bash
cd SafeTrendBot-V5-Incroyable/trading_bot

# Installer les dépendances
pip install -r requirements.txt

# Lancer le générateur de builds
python build_generator.py

# Voir la base clients
python client_manager.py --gui
```

### 2. Générer un Build pour un Client

```bash
python build_generator.py
```

Interface GUI avec:
- Nom du client
- Clé de licence (bouton 🎲 pour générer)
- brokers à inclure
- Branding

→ Génère un .exe + enregistre automatiquement le client

### 3. Vendre

```
Client te paie en crypto (BTC/ETH/USDT)
        ↓
Tu confirmes la transaction sur blockchain
        ↓
Tu envoies le .exe + la clé de licence
        ↓
Client installe en 1 clic
        ↓
BOT FONCTIONNE!
```

---

## 🔐 Sécurité

| Protection | Description |
|------------|-------------|
| **HW-Lock** | 1 licence = 1 PC (CPU+MAC+UUID+Disk) |
| **Anti-VM** | Détecte VMware, VirtualBox, Docker |
| **Anti-Debug** | Bloque les débogueurs |
| **Auto-destruct** | Detruit les données si crack détecté |
| **Code compilé** | .exe obfuscé avec PyInstaller |

---

## 👥 Gestion des Clients

Base de données SQLite avec:

- **Infos client**: nom, email, téléphone, pays
- **Vente**: date, prix, méthode paiement, tx crypto
- **Licence**: clé, date émission, expiration
- **Activation**: HW-ID, compteur, première activation
- **Statut**: active / suspended / revoked

Lancer l'interface:
```bash
python client_manager.py --gui
```

---

## 💰 Vente Crypto

Wallets configurés:
- **BTC**: `bc1qxxzn05t7jvdmz47ncnxlglczhh9aet3gcpt5dx`
- **ETH/USDT**: `0xd1c2ef7f724635fa0ed327f4d626620a2adffd82`

Serveur de vente (optionnel):
```bash
cd crypto_sales
python crypto_sales_server.py
```

---

## 📋 Fichiers à Distribuer au Client

```
SafeTrendBot-Setup.bat   ← Installateur 1 clic
                           OU
VotreApp.exe            ← Build généré avec build_generator.py
```

Le client reçoit:
1. Le fichier .exe / .bat
2. Sa clé de licence: `STB5-XXXX-XXXX-XXXX`

---

## 🔧 Commandes Utiles

```bash
# Générer un build
python build_generator.py

# Interface client GUI
python client_manager.py --gui

# Liste des clients (CLI)
python client_manager.py --list

# Stats (CLI)
python client_manager.py --stats

# Tester le bot (nécessite MT5)
python main.py

# Mode serveur
python headless.py
```

---

## 📊 Workflow Complet

```
┌──────────────────────────────────────────────────────────┐
│                     TOI (DÉVELOPPEUR)                    │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. python build_generator.py                            │
│  2. Configure: nom client, génère clé 🎲               │
│  3. Build → .exe généré                              │
│  4. Client enregistré automatiquement                │
│                                                           │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                       CLIENT                             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. Reçoit le .exe                                      │
│  2. Double-clique → installation auto                   │
│  3. Entre sa clé de licence                             │
│  4. ✅ TRADING!                                         │
│                                                           │
│  Si copie sur autre PC → REFUSÉ (HW-lock)              │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 📞 Support

- **GitHub**: https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable
- **Logs**: `%USERPROFILE%\.safetrendbot\bot.log`
- **Licence**: `%USERPROFILE%\.safetrendbot\license_v5.json`

---

**Version**: 5.3.0  
**Dernière mise à jour**: 15 juin 2026