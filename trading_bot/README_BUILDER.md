# SafeTrendBot V5 — Système de Distribution Sécurisé

## 🏗️ Architecture Unifiée

```
SafeTrendBot-V5/
├── app/
│   ├── core/
│   │   ├── license_manager.py    # Système anti-piratage
│   │   ├── trading_engine.py     # Moteur de trading
│   │   └── anti_tamper.py        # Protections anti-debug/VM
│   ├── brokers/
│   │   ├── factory.py            # Fabrique d'adapters
│   │   ├── mt5_adapter.py        # MetaTrader 5
│   │   ├── ctrader_adapter.py    # cTrader (Spotware)
│   │   ├── xtb_adapter.py        # XTB (xStation)
│   │   └── crypto_adapter.py      # Binance (Spot/Futures)
│   └── ui/
│       └── main_window.py
├── builder/
│   ├── license_builder.py        # Générateur de builds
│   └── builder_gui.py           # Interface graphique
├── server/
│   ├── activation_server.py       # Serveur d'activation en ligne
│   └── requirements.txt
├── main.py
├── headless.py
└── requirements.txt
```

---

## 🔐 Système Anti-Piratage

### Protection multi-couche:

| Protection | Description |
|------------|-------------|
| **Hardware Lock** | CPU + MAC + UUID + Disk → SHA3-512 |
| **Anti-VM** | VMware, VirtualBox, Docker, timing check |
| **Anti-Debug** | IsDebuggerPresent, TracerPid |
| **One-time** | 1 clé = 1 PC, auto-destruction |
| **Obfuscation** | PyArmor + Cython |

---

## 📦 Brokers Supportés

| Broker | Status | API |
|--------|--------|-----|
| **MT5** | ✅ Prêt | MetaTrader5 Python |
| **cTrader** | ✅ Prêt | WebSocket IDN |
| **XTB** | ✅ Prêt | WebSocket xAPI |
| **Binance** | ✅ Prêt | REST + WebSocket |

---

## 🛠️ Installation

```bash
# Cloner le repo
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
cd SafeTrendBot-V5-Incroyable/trading_bot

# Installer dépendances
pip install -r requirements.txt

# Optionnel: GUI moderne
pip install PyQt6
```

---

## 🚀 Utilisation du Builder

### Interface Graphique (Recommandé)

```bash
python builder/builder_gui.py
```

Interface avec 5 onglets:
- **Générer Build** — Crée un build protégé unique
- **Batch** — Génère plusieurs builds d'un coup
- **Licences** — Gère les clés (révoquer, exporter)
- **Serveur** — Lance le serveur d'activation
- **Configuration** — Paramètres globaux

### Ligne de Commande

```bash
# Générer une clé
python builder/license_builder.py generate-key -n 5

# Créer un build
python builder/license_builder.py build \
    --email client@exemple.com \
    --days 30 \
    --platform windows

# Batch de 10 builds
python builder/license_builder.py batch -n 10 \
    --email-prefix client \
    --days 30

# Lister les licences
python builder/license_builder.py list

# Révoquer
python builder/license_builder.py revoke STB5-XXXX-XXXX-XXXX
```

---

## 🖥️ Serveur d'Activation (Optionnel)

Le serveur d'activation permet une gestion centralisée des licences.

```bash
cd server
pip install -r requirements.txt
python activation_server.py
```

### Endpoints API:

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/activate` | Active une licence |
| POST | `/api/heartbeat` | Ping de vie |
| POST | `/api/check` | Vérifie validité |
| GET | `/api/admin/stats` | Statistiques |
| POST | `/api/admin/create` | Crée une clé |
| POST | `/api/admin/revoke/<key>` | Révoque |

### Configuration (Variables d'environnement):

```bash
export SAFETRENDBOT_SECRET="votre_secret_ultra_complexe"
export SAFETRENDBOT_ADMIN_TOKEN="votre_token_admin"
export SAFETRENDBOT_DB="licenses.db"
export PORT=5000
export DEBUG=False
```

### Déploiement Production:

```bash
# Avec Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 activation_server:APP
```

---

## 🔧 Configuration Broker

### MT5
```json
{
    "broker": "mt5",
    "login": 12345678,
    "password": "motdepasse",
    "server": "Broker-Server"
}
```

### cTrader
```json
{
    "broker": "ctrader",
    "account_id": "CTraderID",
    "password": "motdepasse",
    "host": "demo.ctraderapi.com"
}
```

### XTB
```json
{
    "broker": "xtb",
    "account_id": "12345678",
    "password": "motdepasse",
    "demo": true
}
```

### Binance
```json
{
    "broker": "binance",
    "api_key": "votre_cle",
    "api_secret": "votre_secret",
    "mode": "spot",
    "testnet": false
}
```

---

## ⚙️ Configuration Trading

```json
{
    "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
    "timeframe": "H1",
    "max_positions": 3,
    "risk_percent": 2.0,
    "kelly_fraction": 0.25,
    "adx_threshold": 25,
    "stop_loss_pips": 50,
    "take_profit_pips": 100,
    "trailing_stop": true
}
```

---

## 📋 Format des Clés

```
STB5-XXXX-XXXX-XXXX
```

- **STB5-** : Préfixe SafeTrendBot v5
- Caractères exclues: O, I, L (éviter confusion)
- Hachées et signées avec HMAC-SHA3

---

## ⚠️ Notes Importantes

1. **Ne jamais distribuer le dossier `builder/`** aux clients
2. **Changer la MASTER_KEY** dans `license_builder.py` en prod
3. **Backup régulier** de `licenses_generated.json`
4. Compiler avec Cython pour une protection maximale

---

## 🔄 Workflow de Distribution

```
┌─────────────────────────────────────────────────────┐
│                    VOUS (Développeur)               │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. Modifier le code source                        │
│                                                      │
│  2. Builder GUI: python builder/builder_gui.py     │
│                                                      │
│  3. Générer build protégé avec clé embarquée       │
│                                                      │
│  4. Envoyer le .exe au client                       │
│                                                      │
│  5. Client lance → Auto-activation → Prêt!         │
│                                                      │
│  Option: Serveur d'activation pour révocation       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 🆘 Support

- Logs bot: `~/.safetrendbot/bot.log`
- Logs licence: `~/.safetrendbot/v5/license.json`
- Serveur: `python builder/license_builder.py list`