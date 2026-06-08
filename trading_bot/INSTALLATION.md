# SafeTrendBot — Guide d'installation

Application desktop complète pour trading automatisé sur MetaTrader 5.

---

## Installation sur Windows (recommandé)

### Option A : Installation automatique (le plus simple)

1. **Télécharger** et extraire le ZIP du projet
2. **Double-cliquer sur `install.bat`**
3. Attendre la fin (5-15 min selon votre connexion)
4. Un raccourci "SafeTrendBot" apparaît sur le bureau

Le script fait tout automatiquement :
- Télécharge et installe Python 3.12 si absent
- Crée un environnement virtuel isolé
- Installe toutes les dépendances (PyQt6, MT5, etc.)
- Crée un raccourci sur le bureau
- Propose de lancer l'application

### Option B : Build d'un installeur .exe professionnel

Si vous voulez distribuer l'application ou avoir un vrai installeur Windows :

```batch
# Depuis le dossier du projet
python build_installer.py
```

Ce script :
1. Compile l'application en `.exe` avec PyInstaller
2. Génère un installeur avec Inno Setup (si installé)
3. Crée aussi un ZIP portable

**Prérequis optionnel** : [Inno Setup](https://jrsoftware.org/isdl.php) pour l'installeur pro.

Résultats dans le dossier `installer/` :
- `SafeTrendBot_Setup_v1.0.0.exe` — installeur Windows classique
- `SafeTrendBot_Portable_v1.0.0.zip` — version portable sans installation

### Option C : Lancement manuel (développeurs)

```batch
REM Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate

REM Installer les dépendances
pip install -r requirements.txt

REM Lancer
python main.py
```

---

## Installation sur Linux / Debian

```bash
# Prérequis système
sudo apt update
sudo apt install python3 python3-venv python3-pip \
    libxcb-cursor0 libxkbcommon-x11-0

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Lancement
python main.py
```

**Note MT5 sur Linux** : MetaTrader5 ne tourne pas nativement. Options :
- Utiliser Wine (`sudo apt install wine` puis installer MT5)
- Faire tourner MT5 sur un VPS Windows et se connecter à distance
- Utiliser uniquement les fonctions non-trading (backtest, news, calendrier)

---

## Configuration MetaTrader 5

Pour que le bot puisse exécuter des trades :

1. **Ouvrir MetaTrader 5**
2. **Se connecter à un compte démo** chez un broker régulé
3. **Menu Outils → Options → Expert Advisors** :
   - ✅ Autoriser le trading algorithmique
   - ✅ Autoriser les DLL
   - ✅ Autoriser les WebRequest pour les URL listées
4. **Laisser MT5 ouvert** pendant que le bot tourne

### Brokers régulés recommandés (compte démo gratuit)

- **Europe** : IC Markets, Pepperstone, XTB, Admiral Markets
- **Réglementations acceptables** : AMF (FR), BaFin (DE), FCA (UK), CySEC (CY)
- ⚠️ Éviter : brokers offshore non régulés

---

## Première utilisation

### 1. Lancer l'application

Double-clic sur le raccourci bureau ou `launch.bat`.

### 2. Configurer les paramètres

Onglet **Paramètres** → configurer :

**Stratégie** (démarrer avec valeurs par défaut conservatrices) :
- Risque par trade : 1% (ne pas dépasser 2%)
- Ratio R:R : 2.0
- Pertes consécutives max : 3
- Perte journalière max : 3%

**Symboles** : ajouter les paires à trader
- Par défaut : EURUSD en H4
- Recommandé débutant : EURUSD uniquement, H4 ou D1

**Connexion MT5** : laisser "Détection automatique" si MT5 est lancé.

**Alertes Telegram** (optionnel mais recommandé) :
- Suivre les instructions dans le tab pour obtenir le token
- Tester l'envoi

### 3. Valider la stratégie par backtest

Onglet **Backtest** :
- Symbole : EURUSD=X
- Période : 5 ans
- Lancer → attendre la fin
- **Critères de validation** :
  - Profit factor > 1.3
  - Drawdown < 20%
  - Minimum 50 trades

### 4. Tester sur compte démo

Onglet **Tableau de bord** → bouton "▶ Démarrer le bot".

**Laisser tourner au moins 1 mois en démo avant tout trading réel.**

### 5. Passer en réel (après validation)

- Changer les credentials MT5 pour un compte réel
- Commencer avec un capital limité (ce que vous acceptez de perdre)
- Surveiller quotidiennement les premières semaines

---

## Fonctionnalités de l'application

### 📊 Tableau de bord
Vue temps réel : balance, équité, P&L, positions, indicateurs de santé

### 📈 Positions
Positions ouvertes, historique, bouton "Fermer toutes les positions"

### 🧪 Backtest
Lancement de backtests sur données historiques Yahoo Finance
Validation automatique selon 5 critères

### 📅 Calendrier économique
Événements à fort impact (ForexFactory)
Le bot s'abstient automatiquement de trader autour

### 📰 Actualités
Flux RSS Reuters, FT, CNBC, MarketWatch (lecture humaine uniquement)
Recherche et filtrage par source

### 📋 Journaux
Tous les événements du bot, filtrage par niveau, export

### ⚙️ Paramètres
Configuration complète en 7 onglets :
- Stratégie, Symboles, MT5, Telegram, News, Interface, Profils

### 🔔 Alertes Telegram
Notifications push : drawdown, pertes consécutives, ouvertures/clôtures,
news à venir, rapport journalier

### 🖥️ System tray
L'app continue de tourner minimisée avec icône système

---

## Dépannage

| Problème | Solution |
|----------|----------|
| "Python is not recognized" | Relancer `install.bat` ou redémarrer le PC |
| "No module named PyQt6" | `pip install PyQt6` dans l'environnement virtuel |
| "MT5 initialize failed" | Ouvrir MT5, activer "trading algorithmique" |
| Bot ne prend aucun trade | Normal : 2-8 trades/semaine attendus |
| App ne se lance pas | Lancer `python main.py` dans la console pour voir l'erreur |
| Dépendance manquante | `pip install -r requirements.txt --upgrade` |

---

## Architecture technique

```
trading_bot/
├── main.py                      # Point d'entrée
├── install.bat                  # Installeur automatique Windows
├── build_installer.py           # Build de l'exe distribuable
├── requirements.txt
│
├── app/
│   ├── core/
│   │   ├── config_manager.py    # Configuration et profils
│   │   └── trading_engine.py    # Moteur de trading (thread)
│   └── ui/
│       ├── main_window.py       # Fenêtre principale
│       ├── theme.py             # Thème sombre/clair
│       ├── widgets.py           # Widgets réutilisables
│       └── views/               # 7 vues de l'application
│
├── bot/
│   ├── SafeTrendBot.mq5         # Ancien EA MT5 (optionnel)
│   ├── mt5_bridge.py            # Communication MT5
│   ├── economic_calendar.py     # Calendrier éco
│   ├── news_feed.py             # Flux RSS news
│   └── telegram_alerts.py       # Alertes Telegram
│
└── backtest/
    └── backtest.py              # Moteur de backtesting
```

**Technologies** :
- **Interface** : PyQt6 (Qt 6, natif Windows)
- **Trading** : API MetaTrader5 (Python)
- **Concurrence** : Threading + signaux Qt
- **Config** : JSON dans `%APPDATA%/SafeTrendBot/`
- **Build** : PyInstaller + Inno Setup
