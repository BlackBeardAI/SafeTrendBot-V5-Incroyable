# SafeTrendBot V5 — Système de Distribution Sécurisé

## 🏗️ Architecture Unifiée

```
SafeTrendBot-V5/
├── app/
│   ├── core/
│   │   ├── license_manager.py    # Système anti-piratage (hardware lock)
│   │   ├── trading_engine.py    # Moteur de trading unifié
│   │   └── anti_tamper.py       # Protections anti-debug/VM
│   ├── brokers/
│   │   └── factory.py           # Abstraction multi-brokers
│   └── ui/
│       └── main_window.py       # Interface graphique
├── builder/
│   ├── license_builder.py       # Générateur de builds protégés
│   └── builder_gui.py           # Interface graphique du builder
├── main.py                      # Point d'entrée (GUI)
├── headless.py                  # Mode serveur (sans GUI)
└── requirements.txt
```

---

## 🔐 Système Anti-Piratage

### Protection multi-couche:

1. **Hardware Lock** — La licence est liée à:
   - CPU ID (ProcessorId Windows)
   - MAC Address
   - Machine UUID / /etc/machine-id
   - Disque serial
   - Combinés via SHA3-512 + PBKDF2

2. **Anti-VM** — Détecte:
   - VMware, VirtualBox, QEMU, KVM
   - Docker, LXC containers
   - Timing anomalies (VMs lentes)
   - Manufacturer markers

3. **Anti-Debug** — Bloque:
   - WinDbg, x64dbg, OllyDbg
   - `IsDebuggerPresent` (Windows)
   - `TracerPid` (Linux)

4. **One-Time Activation** — 1 clé = 1 PC
   - Impossible de transférer
   - Détecte changement de matériel

5. **Obfuscation** — Code compilable:
   - Cython (.pyc → .c → .so)
   - PyArmor ( bytecode encryption)

---

## 🛠️ Utilisation du Builder

### Installation des dépendances

```bash
cd SafeTrendBot-V5-Incroyable/trading_bot
pip install -r requirements.txt

# Dépendances optionnelles pour obfuscation
pip install pyinstaller pyarmor cython
```

### Interface Graphique (GUI)

```bash
python builder/builder_gui.py
```

Interface avec 4 onglets:
- **Générer Build** — Crée un build protégé unique
- **Batch** — Génère plusieurs builds d'un coup
- **Licences** — Gère les clés (révoquer, exporter)
- **Settings** — Configuration

### Ligne de Commande

```bash
# Générer une clé seule
python builder/license_builder.py generate-key

# Générer une clé avec expiration
python builder/license_builder.py generate-key -n 5

# Créer un build protégé
python builder/license_builder.py build \
    --email client@example.com \
    --days 30 \
    --platform windows

# Générer 10 builds d'un coup
python builder/license_builder.py batch -n 10 \
    --email-prefix client \
    --days 30 \
    --platform windows

# Lister les licences
python builder/license_builder.py list

# Révoquer une licence
python builder/license_builder.py revoke STB5-XXXX-XXXX-XXXX
```

---

## 📦 Format des Clés

```
STB5-XXXX-XXXX-XXXX
     │    │    │
     │    │    └── partie 3
     │    └── partie 2
     └── préfixe v5
```

- **STB5-** : Préfixe SafeTrendBot v5
- Caractères exclues: O, I, L (pour éviter confusion)
- Chaque partie: 4 caractères alphanumériques

---

## 🔧 Génération d'un Build Protégé

Le processus:

1. **Génère une clé unique** (ex: `STB5-A7K9-B2M4-X8P1`)
2. **Signe la clé** avec HMAC-SHA3-512
3. **Prépare les sources** dans un répertoire temporaire
4. **Injecte la clé** dans `license_manager.py` (remplace `__LICENSE_SIG__`)
5. **Obfusque** avec PyArmor / Cython (si demandé)
6. **Compile** avec PyInstaller en binaire Windows/Linux/macOS
7. **Pack** le résultat avec métadonnées

Le binaire généré contient la clé embarquée. Au premier lancement:
- Vérifie le hardware fingerprint
- Active la licence automatiquement
- Stocke le hardware lock

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

## 📋 Dépendances

```
# Core
MetaTrader5==5.0.45

# UI
tkinter (stdlib)

# Build & Obfuscation
pyinstaller>=5.0
pyarmor>=7.0
cython>=3.0

# Utils
requests>=2.28
```

---

## 🚀 Démarrage

```bash
# Mode GUI
python main.py

# Mode Headless (serveur)
python headless.py

# Mode Headless (CLI)
python main.py --headless

# Info licence
python main.py --license-info

# Activation manuelle
python main.py --activate STB5-XXXX-XXXX-XXXX
```

---

## ⚠️ Notes Importantes

1. **Ne jamais distribuer le dossier `builder/`** aux clients
2. **Garder `MASTER_KEY`** secret dans `license_builder.py`
3. **Backup régulier** du fichier `licenses_generated.json`
4. En production, **compiler avec Cython** pour une protection maximale

---

## 🔄 Workflow de Distribution

```
┌─────────────────────────────────────────────────────┐
│                    VOUS (Développeur)                │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. Modifier le code source (trading_engine.py)    │
│                                                      │
│  2. Lancer le Builder:                               │
│     python builder/builder_gui.py                    │
│                                                      │
│  3. Générer un build protégé avec clé embarquée     │
│                                                      │
│  4. Envoyer le .exe au client                        │
│                                                      │
│  5. Client lance → Auto-activation → Prêt à trader  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 📞 Support

- Vérifier les licences: `python builder/license_builder.py list`
- Logs bot: `~/.safetrendbot/bot.log`
- Logs licence: `~/.safetrendbot/v5/license.json`