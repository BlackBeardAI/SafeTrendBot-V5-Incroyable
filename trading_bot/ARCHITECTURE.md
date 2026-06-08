# SafeTrendBot — Documentation technique pour reprise du projet

> Document destiné à un développeur ou IA reprenant le projet.
> Version v4.3 — Avril 2026

---

## 1. Vue d'ensemble

**SafeTrendBot** est un bot de trading multi-broker avec interface graphique PyQt6.

**Caractéristiques principales :**
- Multi-broker : 8 plateformes supportées (MT5, XTB, IB, cTrader, Binance, Bybit, Kraken, Coinbase)
- Multi-stratégies : 4 stratégies parallèles avec système de vote
- Modes de risque : Safe / Normal / Aggressive + 3 stratégies pures
- Interface complète : 15 onglets (dashboard, positions, analyses, backtest, paper trading, outils, etc.)
- Sécurité : verrouillage par PIN avec hash PBKDF2-SHA256
- Notifications Telegram intégrées
- Rapports PDF hebdomadaires
- Analyse de tendance 5 ans via yfinance

**Stats du projet :** ~17 000 lignes Python, ~60 fichiers

---

## 2. Stack technique

| Domaine | Choix | Justification |
|---------|-------|---------------|
| Langage | Python 3.10+ | Mature, écosystème trading riche |
| UI | PyQt6 | Desktop natif, robuste, multi-plateforme |
| Data | numpy, pandas | Standards de l'industrie |
| Broker MT5 | `MetaTrader5` (officiel) | Seule lib officielle |
| Broker IB | `ib_insync` | Plus simple que `ibapi` officiel |
| Broker crypto | `ccxt` | Couvre 100+ exchanges avec API unifiée |
| Backtest | `yfinance` | Données gratuites, fiables |
| Reports | `reportlab` | Génération PDF |
| Telegram | API HTTP directe (`requests`) | Pas besoin de lib lourde |

---

## 3. Architecture du code

```
trading_bot/
├── main.py                          # Point d'entrée (applique thème + PIN puis lance MainWindow)
├── SafeTrendBot.py                  # Launcher Python multiplateforme
├── LANCEZ_MOI.bat                   # Launcher Windows
├── install.bat                      # Installation Windows
├── requirements.txt                 # Dépendances pip
│
├── app/
│   ├── core/                        # Logique métier (sans UI)
│   │   ├── config_manager.py        # Singleton de config (JSON persisté)
│   │   ├── trading_engine_v3.py     # Moteur principal
│   │   ├── strategies.py            # 4 stratégies + voter
│   │   ├── market_filters.py        # Volatility, Correlation, Circuit Breaker
│   │   ├── paper_trading.py         # Mode simulation
│   │   ├── trade_journal.py         # Historique des trades
│   │   ├── pdf_reports.py           # Rapports PDF hebdo
│   │   ├── market_hours.py          # Sessions forex/bourses
│   │   ├── trading_profiles.py      # Profils Safe/Normal/Aggressive
│   │   ├── pin_lock.py              # Système PIN (hash PBKDF2)
│   │   ├── historical_data.py       # Données 5 ans via yfinance
│   │   ├── watchlist.py             # Surveillance prix
│   │   ├── position_calculator.py   # Calcul taille position
│   │   └── csv_export.py            # Export CSV
│   │
│   ├── brokers/                     # Adapters par broker
│   │   ├── broker_adapter.py        # Interface abstraite + types
│   │   ├── mt5_adapter.py           # 🟢 Testé, fonctionnel
│   │   ├── xtb_adapter.py           # 🟡 Expérimental
│   │   ├── ib_adapter.py            # 🟡 Nécessite TWS
│   │   ├── ctrader_adapter.py       # 🟡 Squelette (OAuth2 à finaliser)
│   │   ├── crypto_adapter.py        # 🟡 Binance/Bybit/Kraken/Coinbase via ccxt
│   │   └── factory.py               # Création des adapters
│   │
│   └── ui/                          # Interface graphique
│       ├── main_window.py           # Fenêtre principale + sidebar
│       ├── theme.py                 # Thèmes dark/light + stylesheets globaux
│       ├── widgets.py               # Widgets réutilisables (Card, KPICard, PageHeader)
│       ├── widgets_status.py        # Indicateur broker + diagnostic bot
│       ├── pin_lock_dialog.py       # Dialog PIN + setup
│       └── views/                   # Une vue par onglet
│           ├── dashboard_view.py
│           ├── positions_view.py
│           ├── analytics_view.py
│           ├── profiles_view.py
│           ├── trend_analysis_view.py
│           ├── backtest_view.py
│           ├── paper_trading_view.py
│           ├── tools_view.py
│           ├── broker_view.py
│           ├── telegram_view.py
│           ├── market_hours_view.py
│           ├── calendar_view.py
│           ├── news_view.py
│           ├── logs_view.py
│           └── settings_view.py
│
├── bot/                             # Modules Telegram & news (legacy)
│   ├── SafeTrendBot.mq5             # Ancien EA MQL5 (référence)
│   ├── mt5_bridge.py
│   ├── economic_calendar.py
│   ├── news_feed.py
│   └── telegram_alerts.py
│
└── backtest/
    └── backtest.py
```

---

## 4. Patterns clés

### 4.1 Configuration : singleton avec persistance JSON

```python
from app.core.config_manager import config_manager

# Lecture
risk = config_manager.config.strategy.risk_per_trade

# Écriture
config_manager.config.strategy.risk_per_trade = 0.5
config_manager.save()  # Persiste dans data/config.json
```

Toutes les dataclasses sont sérialisables via `asdict()`. Le chargement utilise `_dict_to_config()` qui gère la rétrocompatibilité.

### 4.2 BrokerAdapter : interface unifiée

Tous les brokers implémentent la même interface `BrokerAdapter` :

```python
class BrokerAdapter(ABC):
    def connect(**kwargs) -> bool
    def disconnect()
    def is_connected() -> bool
    def get_account_info() -> AccountInfo
    def get_symbol_info(symbol) -> SymbolInfo
    def get_tick(symbol) -> Tick
    def get_candles(symbol, timeframe, count) -> List[Candle]
    def get_positions() -> List[Position]
    def open_position(...) -> OrderResult
    def close_position(ticket) -> OrderResult
    def modify_position(ticket, sl, tp) -> OrderResult
```

Pour ajouter un broker, créer `app/brokers/<broker>_adapter.py` qui hérite de `BrokerAdapter`, puis l'enregistrer dans `factory.py`.

### 4.3 Stratégies : système de vote

Chaque stratégie hérite de `Strategy` et implémente `analyze(data) -> Signal` qui retourne :
- `direction`: 1 (buy), -1 (sell), 0 (neutre)
- `confidence`: 0.0 à 1.0
- `reason`: explication textuelle

Le `StrategyVoter` agrège les votes : il faut N stratégies d'accord (config) ET confidence moyenne ≥ seuil.

### 4.4 Theme : stylesheet global via objectName

⚠️ **Important** : NE PAS utiliser `setStyleSheet(f"color: {COLORS['xxx']};")` sur les widgets, car les couleurs sont **figées au moment de la construction**.

Au lieu de cela : utiliser `objectName` et le stylesheet global :

```python
# OUI ✅
label.setObjectName("PageTitle")
# Et dans theme.py : "QLabel#PageTitle { color: ... }"

# NON ❌ (casse au changement de thème)
label.setStyleSheet(f"color: {COLORS['text_primary']};")
```

### 4.5 Vues UI : injection du moteur

Les vues qui ont besoin du moteur le reçoivent par constructeur :

```python
class DashboardView(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
```

Communication via signaux Qt (pas de polling brutal).

---

## 5. Workflow utilisateur typique

1. **Premier lancement** : config par défaut créée, profil "Normal"
2. **Configurer broker** : onglet Broker → MT5 par défaut
3. **Configurer Telegram** (optionnel) : onglet Telegram
4. **Choisir profil** : onglet Profils → Safe / Normal / Aggressive
5. **Tester** : onglet Paper Trading → activer mode PAPER
6. **Démarrer** : bouton "▶ Démarrer le bot" dans la sidebar
   - Si PIN activé, demande le PIN avant trading
7. **Monitorer** : Dashboard + Diagnostic + Indicateur broker en bas de sidebar
8. **Analyser** : onglet Analyses (par symbole/heure/stratégie)
9. **Reporter** : onglet Outils → Export CSV

---

## 6. Ce qui marche / ce qui est expérimental

### ✅ Pleinement fonctionnel
- Interface complète (15 onglets, dark theme)
- MT5 (testé chez l'utilisateur Hawar)
- Stratégies (TrendFollowing, MeanReversion, Breakout, MACD)
- Filtres (volatilité, corrélation, circuit breaker)
- Paper trading
- Journal des trades + analyses
- Rapports PDF
- Système PIN
- Profils Safe/Normal/Aggressive
- Calculator de position
- Watchlist
- Mode lecture seule
- Export CSV
- Horaires marchés
- Analyse tendance 5 ans

### 🟡 Expérimental (à tester en démo)
- XTB adapter (peut bloquer le compte selon CGU)
- Interactive Brokers (nécessite TWS lancé)
- Crypto via ccxt (connexion OK, fermeture position imparfaite)

### ⚠️ Squelette (à finaliser)
- cTrader (flow OAuth2 + Protobuf à implémenter)
- Light theme (retiré, code conservé)

### ❌ Volontairement absent (refusé)
- Scraping eToro / T212 / Robinhood (CGU + sécurité)
- Trading "nerveux" / mode très agressif sans avertissements
- ML / réseaux de neurones (overfitting)
- Grid trading / martingale (destructeur de comptes)
- Auto-trading sur signaux sociaux/Twitter/Telegram-groups

---

## 7. Améliorations légitimes possibles (priorisées)

### Priorité haute
1. **Tests unitaires** — actuellement aucun. Au minimum couvrir les calculs (ATR, position size, stratégies).
2. **Backup automatique de config** avant écriture (éviter corruption JSON)
3. **Logging structuré** — passer du `print` au `logging` Python avec niveaux
4. **Internationalisation** — actuellement tout en français hardcodé
5. **Optimisation backtest** — actuellement single-thread, pourrait être parallélisé

### Priorité moyenne
6. **Système de plugins** pour stratégies utilisateur (sans toucher au cœur)
7. **Editor de stratégies visuelles** (drag & drop d'indicateurs)
8. **Connecteur webhook** pour signaux externes (TradingView Alerts)
9. **Mode multi-comptes** (un bot, plusieurs comptes en parallèle)
10. **Replay mode** — rejouer un mois d'historique pour voir comment le bot aurait réagi
11. **Heatmap des performances** par heure/jour de la semaine

### Priorité basse
12. **Theme clair finalisé** (réécrire chaque vue avec objectName, ~6h de travail)
13. **Sons/notifications desktop** au déclenchement de trades
14. **Mode mobile companion** (lecture seule via API REST)
15. **OCR sur captures TradingView** pour importer des annotations

### À ne PAS implémenter (pièges classiques)
- ❌ Optimisation hyper-paramètres → overfitting garanti
- ❌ "Stop loss flottant intelligent" qui ne stop jamais → catastrophe
- ❌ Martingale "améliorée" → mathématiquement perdante
- ❌ Trading basé sur "patterns chartistes IA" sans backtest 10+ ans

---

## 8. Pièges connus à ne pas répéter

### 8.1 Bug du thème clair (réglé v3.10)

**Cause** : couleurs capturées dans des f-strings au moment de la construction des widgets.
**Fix** : utiliser `objectName` + stylesheet global (voir section 4.4).

### 8.2 KeyError sur clés COLORS (réglé v3.4)

**Cause** : utilisation de clés inexistantes (`surface_variant`, `primary`, etc.) dans certaines vues.
**Fix** : COLORS_DARK et COLORS_LIGHT ont strictement les mêmes clés (validé par script).

### 8.3 Imports circulaires (potentiel)

Si vous ajoutez des features, attention :
- `core/` ne doit JAMAIS importer depuis `ui/`
- `brokers/` ne doit JAMAIS importer depuis `core/trading_engine_v3.py`
- `ui/views/` peut importer `core/` et `brokers/`

### 8.4 MT5 sur Linux ARM

**Demande fréquente** : faire tourner sur Raspberry Pi.
**Réalité** : MT5 n'est pas ARM. Wine n'émule pas x86 vers ARM utilisablement. Il faut un PC x86 ou un VPS Windows.

### 8.5 Limites de l'API Telegram

L'API Telegram exige que l'utilisateur démarre une conversation avec le bot AVANT que le bot puisse lui envoyer un message. Le `chat_id` est l'ID numérique de l'utilisateur, récupérable via `@userinfobot`.

---

## 9. Variables d'environnement / fichiers à créer

L'application crée automatiquement :
- `data/config.json` — configuration utilisateur
- `data/journal.db` — base SQLite des trades
- `data/profiles/` — profils nommés
- `logs/` — logs de l'app

**Aucune variable d'environnement requise.** Toutes les credentials passent par la config.

---

## 10. Tests rapides à faire après modification

```bash
# 1. Validation syntaxique
python -c "import ast, os
for r,_,fs in os.walk('app'):
    for f in fs:
        if f.endswith('.py'):
            ast.parse(open(f'{r}/{f}').read())
print('OK')"

# 2. Import du moteur
python -c "from app.core.trading_engine_v3 import TradingEngine; print('OK')"

# 3. Lancer l'UI (sans broker)
python main.py
```

---

## 11. Contact / contexte utilisateur

L'utilisateur Hawar a :
- Un compte MT5 fonctionnel
- Aucune expérience en programmation (suit les instructions)
- Préfère le mode clair (tendance à demander des fonctionnalités sans toujours mesurer les implications)
- A déjà testé l'app — elle se lance, MT5 se connecte, mais le bot ne trade pas pendant longtemps
  (c'est NORMAL avec les seuils par défaut, pas un bug)

**Conseils pour l'IA suivante** :
- Toujours pousser vers le **paper trading** avant le réel
- Ne JAMAIS rendre le bot "plus agressif" sur simple demande sans explication
- Ne JAMAIS implémenter de scraping de sites de trading
- Toujours valider syntaxiquement après modification
- Le code est en **français** (variables, commentaires, UI), maintenir cette cohérence
