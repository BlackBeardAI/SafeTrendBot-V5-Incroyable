# SafeTrendBot V5 — Documentation Complète
## Système de Trading Sécurisé avec Protection Anti-Piratage

---

## Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Installation Rapide](#2-installation-rapide)
3. [Architecture du Système](#3-architecture-du-système)
4. [Système de Licence Anti-Piratage](#4-système-de-licence-anti-piratage)
5. [Guide d'Utilisation du Builder](#5-guide-dutilisation-du-builder)
6. [Serveur d'Activation (Optionnel)](#6-serveur-dactivation-optionnel)
7. [Configuration des Brokers](#7-configuration-des-brokers)
8. [API et Endpoints](#8-api-et-endpoints)
9. [Sécurité Avancée](#9-sécurité-avancée)
10. [Guide de Déploiement](#10-guide-de-déploiement)
11. [FAQ](#11-faq)

---

## 1. Vue d'Ensemble

SafeTrendBot V5 est un système de trading algorithmique professionnel conçu pour la distribution commerciale. Il combine:

- **Moteur de trading intelligent** avec détection de régime de marché
- **Multi-broker** (MT5, cTrader, XTB, Binance)
- **Protection anti-piratage multicouche** (hardware lock, anti-VM, obfuscation)
- **Outil de génération de builds protégés** pour distribution
- **Serveur d'activation optionnel** pour gestion centralisée

### Caractéristiques Clés

| Fonctionnalité | Description |
|----------------|-------------|
| Hardware Lock | Lie la licence au hardware (CPU, MAC, UUID, Disk) |
| Anti-VM | Détecte VMware, VirtualBox, Docker |
| Anti-Debug | Bloque les débogueurs |
| One-Time Activation | 1 clé = 1 PC, impossible à cloner |
| Kelly Criterion | Sizing adaptatif selon win rate |
| Regime Detection | ADX + Bollinger Bands + ATR |
| Multi-Broker | MT5, cTrader, XTB, Binance |
| Obfuscation | Cython + PyArmor |

---

## 2. Installation Rapide

### 2.1 Prérequis

```bash
# Python 3.9+
python --version

# Git
git --version
```

### 2.2 Installation

```bash
# Cloner le repo
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
cd SafeTrendBot-V5-Incroyable/trading_bot

# Créer environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer dépendances
pip install -r requirements.txt
```

### 2.3 Dépendances Optionnelles

```bash
# GUI Moderne (PyQt6)
pip install PyQt6

# Pour builder en binaire
pip install pyinstaller pyarmor cython

# Serveur d'activation
pip install flask flask-cors gunicorn
```

---

## 3. Architecture du Système

### 3.1 Structure des Fichiers

```
SafeTrendBot-V5/
├── app/
│   ├── core/                      # Modules critiques
│   │   ├── license_manager.py     # Système de licence
│   │   ├── trading_engine.py     # Moteur de trading
│   │   ├── anti_tamper.py         # Anti-debug/VM
│   │   └── ...
│   ├── brokers/                   # Adaptateurs broker
│   │   ├── factory.py             # Fabrique d'adapters
│   │   ├── mt5_adapter.py         # MetaTrader 5
│   │   ├── ctrader_adapter.py     # cTrader
│   │   ├── xtb_adapter.py         # XTB
│   │   └── crypto_adapter.py      # Binance
│   └── ui/                        # Interface graphique
├── builder/                       # OUTIL DE BUILD
│   ├── license_builder.py         # CLI du builder
│   └── builder_gui.py             # GUI du builder
├── server/                        # SERVEUR D'ACTIVATION
│   ├── activation_server.py       # API Flask
│   └── requirements.txt
├── main.py                        # Point d'entrée GUI
├── headless.py                    # Point d'entrée serveur
└── requirements.txt
```

### 3.2 Flux de Données

```
┌─────────────────────────────────────────────────────────────────┐
│                         BUILDER (VOUS)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Modifier le code source                                     │
│  2. python builder/builder_gui.py                               │
│  3. Générer une clé STB5-XXXX-XXXX-XXXX                        │
│  4. Compiler avec PyInstaller/PyArmor                          │
│  5. Produire un fichier .exe protégé                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT (UTILISATEUR)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Télécharge le .exe                                          │
│  2. Lance l'application                                         │
│  3. Auto-activation (clé embarquée)                            │
│  4. Vérification hardware lock                                  │
│  5. Bot trading actif!                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    (optionnel) │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SERVEUR D'ACTIVATION (VPS)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  - Track les activations                                        │
│  - Révocation à distance                                        │
│  - Heartbeats clients                                          │
│  - Statistiques                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Système de Licence Anti-Piratage

### 4.1 Protection Multi-Couche

#### Couche 1: Hardware Lock

La licence est liée à l'identifiant unique du PC:

| Composant | Détail |
|----------|--------|
| CPU ID | ProcessorId (Windows) |
| MAC Address | UUID réseau |
| Machine UUID | Windows SID / Linux machine-id |
| Disk Serial | Numéro de série du disque |

**Formule:**
```
HWID = SHA3-512(CPU_ID + MAC + UUID + Disk_Serial)
```

#### Couche 2: Anti-Virtualization

Détecte les environnements virtuels:

```python
# Détecte:
- VMware / VirtualBox / QEMU / KVM
- Docker / LXC containers
- Microsoft Hyper-V
- Parallels
- Timing anomalies (VMs lentes)
```

#### Couche 3: Anti-Debug

```python
# Windows
kernel32.IsDebuggerPresent()

# Linux
/proc/self/status → TracerPid: [non-zero]
```

#### Couche 4: One-Time Activation

```
1. Clé: STB5-XXXX-XXXX-XXXX
2. Signée avec HMAC-SHA3-512
3. Injectée dans le binaire
4. Au premier lancement: vérifie HWID
5. Stocke license.json + hardware.lock
6. Clé liée à ce PC uniquement
```

### 4.2 Format des Clés

```
STB5-XXXX-XXXX-XXXX
     │    │    │
     │    │    └── Partie 3 (4 caractères)
     │    └── Partie 2 (4 caractères)
     └── Partie 1 (4 caractères)

Règles:
- Préfixe: STB5 (SafeTrendBot v5)
- Caractères: A-Z, 0-9 (sans O, I, L pour éviter confusion)
- Hachée et signée pour intégrité
```

### 4.3 Exemple d'Activation

```python
from app.core.license_manager import LicenseManager, LicenseStatus

lm = LicenseManager()
status = lm.check_license()

if status == LicenseStatus.VALID:
    print("✅ Licence valide — Bot prêt")
elif status == LicenseStatus.NOT_ACTIVATED:
    success, msg = lm.activate()
    print(msg)
else:
    print(f"❌ Erreur: {status.name}")
```

### 4.4 Fichiers Générés

| Fichier | Emplacement | Contenu |
|---------|-------------|---------|
| `license.json` | `~/.safetrendbot/` | Clé, HWID, expiration |
| `hardware.lock` | `~/.safetrendbot/` | Token hardware signé |

---

## 5. Guide d'Utilisation du Builder

### 5.1 Interface Graphique (Recommandé)

```bash
python builder/builder_gui.py
```

#### Onglet "Générer Build"

1. **Clé de licence**: Laissez vide pour génération auto ou entrez une clé existante
2. **Email client**: Email du client (optionnel)
3. **Expiration**: Activez et définissez le nombre de jours
4. **Plateforme**: Windows, Linux ou macOS
5. **Options**:
   - ☑️ Obfuscation PyArmor
   - ☑️ Compilation Cython
   - ☑️ PyInstaller (exe)
6. Cliquez **🚀 GÉNÉRER LE BUILD**

#### Onglet "Batch (Multi)"

Pour générer plusieurs builds:

1. Définissez le nombre (max 100)
2. Préfixe email (ex: `client` → `client1@ex.com`, `client2@ex.com`)
3. Jours d'expiration (0 = illimité)
4. Plateforme
5. Cliquez **📦 GÉNÉRER BATCH**

#### Onglet "Licences"

- Affiche toutes les licences générées
- Actions: Rafraîchir, Exporter CSV, Révoquer, Copier clé
- Statistiques: Total, actives, révoquées

#### Onglet "Serveur Activation"

- Informations sur le serveur d'activation
- Bouton pour ouvrir le dossier `server/`
- Bouton pour démarrer le serveur en local

#### Onglet "Configuration"

- Versions installées
- Chemins des fichiers
- Génération d'une nouvelle Master Key (⚠️ sécurité)

### 5.2 Ligne de Commande

```bash
# Générer une clé unique
python builder/license_builder.py generate-key

# Générer 5 clés
python builder/license_builder.py generate-key -n 5

# Créer un build protégé
python builder/license_builder.py build \
    --email client@example.com \
    --days 30 \
    --platform windows

# Batch de 10 builds
python builder/license_builder.py batch -n 10 \
    --email-prefix client \
    --days 30 \
    --platform windows

# Lister toutes les licences
python builder/license_builder.py list

# Révoquer une licence
python builder/license_builder.py revoke STB5-XXXX-XXXX-XXXX

# Exporter les licences en CSV (via GUI uniquement)
```

### 5.3 Processus de Build

```
1. VALIDATION
   - Vérifie format de clé
   - Génère clé si nécessaire
   - Signe avec Master Key

2. PRÉPARATION
   - Copie les sources dans /tmp
   - Injecte la clé dans license_manager.py
   - Remplace __LICENSE_SIG__ par la vraie clé

3. OBFUSCATION (si demandé)
   - PyArmor: bytecode encryption
   - Cython: .py → .c → .so compilation

4. COMPILATION
   - PyInstaller: création du .exe
   - Inclusion des ressources
   - Configuration du spec file

5. OUTPUT
   - builds/SafeTrendBot-v5.X.X-windows-x64.exe
   - Fichier prêt à distribuer
```

---

## 6. Serveur d'Activation (Optionnel)

### 6.1 Pourquoi un Serveur?

Le système fonctionne **sans serveur** (hardware lock local). Mais un serveur permet:

| Fonction | Sans Serveur | Avec Serveur |
|----------|--------------|--------------|
| Activation | ✅ Locale | ✅ Locale + Remote |
| Révocation | ❌ Impossible | ✅ Instantanée |
| Track | ❌ Impossible | ✅ Complet |
| Heartbeat | ❌ Impossible | ✅ Temps réel |
| Stats | ❌ Impossible | ✅ Dashboard |

### 6.2 Installation

```bash
cd server
pip install -r requirements.txt
python activation_server.py
```

### 6.3 Configuration Environment

```bash
# Variables d'environnement
export SAFETRENDBOT_SECRET="votre_secret_ultra_complexe_256bits"
export SAFETRENDBOT_ADMIN_TOKEN="token_admin_very_long"
export SAFETRENDBOT_DB="licenses.db"
export PORT=5000
export DEBUG=False
```

### 6.4 Endpoints API

#### Public (Clients)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/activate` | Active une licence |
| POST | `/api/heartbeat` | Ping périodique |
| POST | `/api/check` | Vérifie validité |
| POST | `/api/revoke-self` | Auto-révocation |

#### Admin (Vous)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/admin/stats` | Statistiques globales |
| GET | `/api/admin/licenses` | Liste toutes les licences |
| GET | `/api/admin/license/<key>` | Détail d'une licence |
| POST | `/api/admin/create` | Crée une licence |
| POST | `/api/admin/revoke/<key>` | Révoque une licence |
| DELETE | `/api/admin/delete/<key>` | Supprime une licence |

### 6.5 Exemple d'Activation Client

```python
import requests

# Activation
response = requests.post("https://votre-serveur.com/api/activate", json={
    "license_key": "STB5-XXXX-XXXX-XXXX",
    "email": "client@example.com",
    "hw_token": "sha3_hash_du_hardware",
    "hw_fingerprint": "cpu+mac+uuid+disk",
    "machine_name": "PC-JEAN",
    "os_info": "Windows 11",
    "version": "5.3.0"
})

if response.json()["success"]:
    token = response.json()["token"]
    print("✅ Activation réussie!")
```

### 6.6 Déploiement Production

```bash
# Avec Gunicorn (4 workers)
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 activation_server:APP

# Avec Docker
docker build -t safetrendbot-server .
docker run -d -p 5000:5000 -e SAFETRENDBOT_SECRET="..." safetrendbot-server
```

---

## 7. Configuration des Brokers

### 7.1 MetaTrader 5

```json
{
    "broker": "mt5",
    "login": 12345678,
    "password": "motdepasse_mt5",
    "server": "Broker-Demo"
}
```

```python
from app.brokers.factory import BrokerFactory

config = {"login": 12345678, "password": "xxx", "server": "Demo"}
broker = BrokerFactory.create("mt5", config)
broker.connect()
```

### 7.2 cTrader

```json
{
    "broker": "ctrader",
    "account_id": "CTraderID123",
    "password": "motdepasse_ctrader",
    "host": "demo.ctraderapi.com",
    "app_id": "1002"
}
```

```python
config = {
    "account_id": "ID123",
    "password": "xxx",
    "host": "demo.ctraderapi.com"
}
broker = BrokerFactory.create("ctrader", config)
```

### 7.3 XTB

```json
{
    "broker": "xtb",
    "account_id": "12345678",
    "password": "motdepasse_xtb",
    "demo": true
}
```

```python
config = {
    "account_id": "12345678",
    "password": "xxx",
    "demo": True
}
broker = BrokerFactory.create("xtb", config)
```

### 7.4 Binance

```json
{
    "broker": "binance",
    "api_key": "votre_api_key",
    "api_secret": "votre_api_secret",
    "mode": "spot",
    "testnet": true
}
```

```python
config = {
    "api_key": "xxx",
    "api_secret": "xxx",
    "mode": "spot",
    "testnet": True
}
broker = BrokerFactory.create("binance", config)
```

### 7.5 Auto-Détection

```python
from app.brokers.factory import BrokerFactory, create_broker

# Méthode 1: Auto-détection
broker = BrokerFactory.auto_detect()

# Méthode 2: Par nom
broker = create_broker("mt5")

# Méthode 3: Par type
broker = BrokerFactory.create(BrokerType.MT5, config)
```

---

## 8. API et Endpoints

### 8.1 Trading Engine

```python
from app.core.trading_engine import TradingEngine, MarketRegime

engine = TradingEngine(config)
engine.start()

# Configuration par défaut
config = {
    "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
    "timeframe": "H1",
    "max_positions": 3,
    "risk_percent": 2.0,
    "kelly_fraction": 0.25,
    "adx_threshold": 25,
    "stop_loss_pips": 50,
    "take_profit_pips": 100,
    "trailing_stop": True
}
```

### 8.2 Position Manager

```python
positions = broker.get_positions()

for pos in positions:
    print(f"{pos.symbol}: {pos.direction.name} {pos.volume} lots")
    print(f"  Entry: {pos.entry_price} Current: {pos.current_price}")
    print(f"  PnL: {pos.unrealized_pnl}")
```

### 8.3 Ordres

```python
from app.core.trading_engine import TradeDirection

# Envoyer un ordre
result = broker.send_order(
    symbol="EURUSD",
    direction=TradeDirection.LONG,
    volume=0.1,  # Lots
    stop_loss=1.0800,
    take_profit=1.0900
)

if result.success:
    print(f"Ordre exécuté: #{result.ticket}")
else:
    print(f"Erreur: {result.error}")

# Fermer une position
broker.close_position(ticket=12345)
```

### 8.4 Chandeliers

```python
candles = broker.get_candles("EURUSD", timeframe="H1", count=100)

for c in candles[-5:]:
    print(f"{c['time']}: O={c['open']} H={c['high']} L={c['low']} C={c['close']}")
```

---

## 9. Sécurité Avancée

### 9.1 Anti-Tampering

```python
from app.core.anti_tamper import AntiTamper

# Vérification au démarrage
at = AntiTamper()
if not at.check_all():
    print("⚠️ Environnement suspect détecté")
    # sys.exit(1) en production
```

### 9.2liste des Protections

| Protection | Cible | Méthode |
|------------|-------|---------|
| IsDebuggerPresent | Win32 Debug | API Windows |
| TracerPid | Linux Debug | /proc/self/status |
| VM Manufacturer | VM Detection | WMIC |
| Docker CGroup | Container | /proc/self/cgroup |
| Timing Check | VM lente | perf_counter delta |
| Code Integrity | Modification | Hash verification |

### 9.3 Configuration Production

```python
# Dans license_manager.py
DEBUG_BLOCK_VM = True  # Bloque VMs (False = warning only)
DEBUG_BLOCK_DEBUG = True  # Bloque debuggers
```

---

## 10. Guide de Déploiement

### 10.1 Build pour Distribution

```bash
# 1. Préparer le build
python builder/builder_gui.py

# 2. Sélectionner les options:
#    ☑️ Obfuscation PyArmor
#    ☑️ Compilation Cython
#    ☑️ PyInstaller

# 3. Générer

# 4. Tester localement
./builds/SafeTrendBot-v5.3.0-windows-x64.exe

# 5. Distribuer
```

### 10.2 Serveur VPS Recommandé

| Provider | Specs | Prix/mois |
|----------|-------|-----------|
| DigitalOcean | 2 vCPU, 4GB RAM | ~$24 |
| Hetzner | 2 vCPU, 4GB RAM | ~€5 |
| Linode | 2 vCPU, 4GB RAM | ~$24 |
| AWS EC2 | t3.medium | ~$30 |

### 10.3 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY server/ /app/server/

RUN pip install --no-cache-dir -r server/requirements.txt

ENV SAFETRENDBOT_SECRET="CHANGE_ME"
ENV SAFETRENDBOT_ADMIN_TOKEN="CHANGE_ME"
ENV PORT=5000

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "server.activation_server:APP"]
```

---

## 11. FAQ

### Q: Le bot fonctionne-t-il sans connexion internet?

**R:** Oui, une fois activé. L'activation et les vérifications sont locales. Le serveur d'activation est optionnel.

### Q: Comment transférer une licence sur un nouveau PC?

**R:** Ce n'est PAS possible intentionnellement. C'est une protection anti-piratage. Le client doit acheter une nouvelle licence.

### Q: Peut-on désactiver les protections VM?

**R:** Oui, dans license_manager.py: `DEBUG_BLOCK_VM = False`

### Q: Comment vendre le bot?

**R:** 
1. Générer un build avec expiration (ex: 30 jours)
2. Envoyer le .exe au client
3. Le client paie (PayPal, Stripe, etc.)
4. Le client lance → auto-activation
5. Renouveler en générant un nouveau build

### Q: Quelle plateforme de paiement utiliser?

**R:** Recommandé:
- **PayPal** (facile, instantané)
- **Stripe** (professional, frais bas)
- **Gumroad** (simple pour digital products)
- **LemonSqueezy** (spécialisé digital)

### Q: Comment protéger le code source?

**R:** 
1. Utiliser PyArmor (obfuscation bytecode)
2. Compiler avec Cython (.py → .so)
3. Ne JAMAIS distribuer le dossier `builder/`
4. Garder la Master Key secrète

### Q: Le serveur d'activation est-il obligatoire?

**R:** Non. Le système fonctionne P2P (peer-to-peer) avec hardware lock local. Le serveur est uniquement pour:
- Révocation à distance
- Tracking centralisé
- Dashboard admin

---

## Support

- **GitHub Issues**: https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable/issues
- **Logs Bot**: `~/.safetrendbot/bot.log`
- **Logs Licence**: `~/.safetrendbot/v5/license.json`

---

*Document généré le 15 juin 2026 — SafeTrendBot V5.3.0*