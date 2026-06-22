# SafeTrendBot V5 — Guide Développeur

> **Usage interne — BlackBeardAI uniquement.**
> Ce document est destiné au développeur/vendeur. Il ne doit **pas** être distribué aux clients.
> Pour la documentation client, voir `GUIDE_CLIENT.md`.

Version du bot: **5.4.0**
Racine du projet: `/root/SafeTrendBot-V5-Incroyable/`

---

## 1. Architecture du projet

Le projet est organisé autour d'un package principal `trading_bot/` qui contient toute la logique applicative. Voici la structure détaillée:

```
SafeTrendBot-V5-Incroyable/
├── GUIDE_DEV.md             ← Ce fichier (interne)
├── GUIDE_CLIENT.md          ← Documentation client
├── INSTALL_WINDOWS.bat      ← Installation 1-clic (Windows)
├── README.md
├── build_msi.py             ← Build installateur .msi
└── trading_bot/             ← Package principal
    ├── build_exe.py         ← Build .exe standalone (PyInstaller)
    ├── main.py              ← Point d'entrée PyQt6 (interface graphique)
    ├── headless.py          ← Mode serveur/headless
    ├── test_bot.py          ← Suite de tests (67 tests)
    ├── requirements.txt     ← Dépendances Python
    ├── app/
    │   ├── core/            ← Moteur, stratégies, risk management
    │   ├── brokers/         ← Adapters broker
    │   └── ui/              ← Interface PyQt6
    ├── bot/                 ← Telegram, news, calendrier
    ├── backtest/            ← Backtesting
    ├── assets/              ← Icônes, ressources
    └── data/                ← Données, logs, config
```

### `trading_bot/app/core/` — Moteur et logique métier

Cœur du bot. Contient tous les modules de trading:

- **`trading_engine_v4.py`** — Moteur de trading unique (v4). Orchestre stratégies, risk management, exécution d'ordres. C'est la version active; les anciennes versions (`trading_engine.py`) sont conservées pour compatibilité.
- **`strategies.py`** — Framework de stratégies. Définit `BaseStrategy`, 4 stratégies concrètes (TrendFollowing, MeanReversion, Breakout, MACD), et `StrategyVoter` qui combine les signaux par vote.
- **`adaptive_strategies.py`** — Stratégies adaptatives (ajustement dynamique des paramètres).
- **`bot_types.py`** — Types partagés centralisés: `MarketRegime`, `TradeDirection`, `BrokerType`, `BotState`, `Signal`, `Position`, `TradeResult`, `BotStatus`, `RegimeDetector`.
- **`simple_license.py`** — Système de licence (voir section 3).
- **`__license_embed__.py`** — Fichier d'embedding de clé (placeholder `__EMBEDDED_KEY__`, remplacé au build).
- **`risk_off_manager.py`** — Mode risk-off (désactivation automatique en cas de drawdown).
- **`auto_hedge.py`** — Couverture automatique (hedging).
- **`portfolio_manager.py`** — Gestion de portefeuille multi-symboles.
- **`position_calculator.py`** — Calcul de taille de position (money management).
- **`market_filters.py`** — Filtres de marché (news, volatilité, heures).
- **`market_hours.py`** — Gestion des sessions de marché.
- **`regime_detector.py`** / **`ml_regime_detector.py`** — Détection de régime de marché (classique + ML).
- **`triple_screen.py`** — Système triple écran (Elder).
- **`paper_trading.py`** — Mode paper trading (simulation).
- **`config_manager.py`** — Gestion de la configuration (chargement/sauvegarde).
- **`performance_metrics.py`** — Métriques de performance (Sharpe, drawdown, etc.).
- **`decision_journal.py`** / **`trade_journal.py`** — Journalisation des décisions et trades.
- **`pdf_reports.py`** / **`csv_export.py`** — Génération de rapports PDF/CSV.
- **`auto_reporting.py`** — Rapports automatiques programmés.
- **`prop_firm.py`** — Mode prop firm (respect des règles challenge).
- **`broker_failover.py`** — Bascule automatique entre brokers.
- **`smart_order_routing.py`** — Routage intelligent d'ordres.
- **`multi_account.py`** — Gestion multi-comptes.
- **`recommendations.py`** — Recommandations automatiques.
- **`trading_profiles.py`** — Profils de trading prédéfinis.
- **`walk_forward.py`** — Walk-forward analysis (backtesting avancé).
- **`slippage_learner.py`** — Apprentissage du slippage.
- **`symbol_circuit_breaker.py`** — Disjoncteur par symbole.
- **`extreme_guard.py`** — Protection contre conditions extrêmes.
- **`pin_lock.py`** — Verrouillage par code PIN.
- **`encryption.py`** — Chiffrement des données sensibles.
- **`anti_tamper.py`** — Protection anti-altération.
- **`voice_alerts.py`** — Alertes vocales.
- **`web_dashboard.py`** — Dashboard web.
- **`system_tray_manager.py`** — Icône system tray.
- **`news_nlp.py`** — Analyse NLP des news.
- **`historical_data.py`** — Gestion données historiques.
- **`license_manager.py`** — Gestionnaire de licence (couche supérieure).

### `trading_bot/app/brokers/` — Adapters broker

Couche d'abstraction pour les brokers. Le moteur utilise **uniquement** l'interface `BrokerAdapter`.

- **`broker_adapter.py`** — Interface abstraite commune. Définit `BrokerAdapter` (ABC), `BrokerType`, `BrokerCapabilities`, `OrderType`, `OrderStatus`, `AccountInfo`, `SymbolInfo`, `Tick`, `Candle`, `Position`, `OrderResult`.
- **`mt5_adapter.py`** — MetaTrader 5 (🟢 supporté, Windows uniquement).
- **`ctrader_adapter.py`** — cTrader (🟢 supporté).
- **`xtb_adapter.py`** — XTB xStation (🟡 expérimental).
- **`crypto_adapter.py`** — Binance (🟢 supporté).
- **`factory.py`** — `BrokerFactory` qui crée le bon adapter selon le type. Import dynamique avec fallback gracieux si une librairie n'est pas installée.

> **Note**: `BrokerType` est défini à la fois dans `broker_adapter.py` (8 valeurs) et dans `bot_types.py` (6 valeurs). Les adapters utilisent celui de `broker_adapter.py`. Pour la cohérence, vérifier quel enum est importé dans chaque module.

### `trading_bot/app/ui/` — Interface PyQt6

Interface graphique complète (18+ vues):

- **`main_window.py`** — Fenêtre principale (navigation, menu, statut).
- **`theme.py`** — Thème dark/light.
- **`widgets.py`** / **`widgets_status.py`** — Widgets réutilisables.
- **`equity_chart.py`** — Graphique d'équité.
- **`signal_monitor.py`** — Moniteur de signaux temps réel.
- **`onboarding_wizard.py`** — Assistant de configuration initiale.
- **`pin_lock_dialog.py`** — Dialogue de déverrouillage PIN.
- **`views/`** — 18 vues spécialisées:
  - `dashboard_view.py` — Tableau de bord
  - `broker_view.py` — Connexion broker
  - `positions_view.py` — Positions ouvertes
  - `strategy_params_view.py` — Paramètres stratégies
  - `backtest_view.py` — Interface backtest
  - `analytics_view.py` — Analytiques
  - `logs_view.py` — Logs
  - `settings_view.py` — Paramètres
  - `news_view.py` — News économiques
  - `calendar_view.py` — Calendrier économique
  - `telegram_view.py` — Configuration Telegram
  - `paper_trading_view.py` — Paper trading
  - `profiles_view.py` — Profils de trading
  - `recommendations_view.py` — Recommandations
  - `market_hours_view.py` — Sessions de marché
  - `trend_analysis_view.py` — Analyse de tendance
  - `watchlist_view.py` — Watchlist
  - `tools_view.py` — Outils divers

### `trading_bot/bot/` — Telegram, news, calendrier

- **`telegram_alerts.py`** — Bot Telegram (notifications, commandes à distance).
- **`news_feed.py`** — Flux de news économiques.
- **`economic_calendar.py`** — Calendrier économique (événements, impact).
- **`SafeTrendBot.mq5`** — Expert Advisor MT5 (companion).

### `trading_bot/backtest/` — Backtesting

- **`backtest.py`** — Moteur de backtesting. Simule l'historique, calcule les métriques de performance.

### Fichiers racine clés

- **`bot_types.py`** → `trading_bot/app/core/bot_types.py` — Types partagés (`TradeDirection`, `BotState`, `BrokerType`, `MarketRegime`, `Signal`, `Position`, `TradeResult`, `BotStatus`, `RegimeDetector`).
- **`trading_engine_v4.py`** → `trading_bot/app/core/trading_engine_v4.py` — Moteur de trading unique (v4 actif).
- **`main.py`** — Point d'entrée de l'interface PyQt6. Vérifie la licence au démarrage (dialog si invalide).
- **`headless.py`** — Mode serveur/headless (sans GUI, pour VPS).

---

## 2. Build et distribution

### Build .exe standalone (recommandé pour clients)

Le build utilise **PyInstaller** en mode `--onefile --noconsole`. Le résultat est un exécutable Windows autonome avec la clé de licence intégrée.

```bash
cd trading_bot
python build_exe.py --generate --build
# → dist/SafeTrendBot.exe avec clé intégrée
```

**Options de `build_exe.py`:**

| Option | Description |
|--------|-------------|
| `--generate` | Génère une clé STB5 valide et l'affiche |
| `--key STB5-XXXX-XXXX-XXXX` | Utilise une clé spécifique (doit être valide) |
| `--build` | Lance PyInstaller pour produire le .exe |

**Comportements:**

- Sans `--build`: affiche seulement la clé générée (utile pour la noter).
- `--generate --build`: génère une clé + lance le build (one-shot).
- `--key STB5-... --build`: build avec une clé existante.
- Le .exe est **standalone** (`--onefile`), **sans console** (`--noconsole`).
- Si `assets/icon.ico` existe, il est inclus comme icône.
- Le fichier `__license_embed__.py` est modifié **temporairement** (injection de la clé) puis **restauré** automatiquement après le build (placeholder `__EMBEDDED_KEY__`). La clé n'est jamais committée dans git.
- Sur Linux, PyInstaller produit un binaire (pas `.exe`) — utile pour tests mais le build final doit se faire sur Windows.

**Sortie:**
- `dist/SafeTrendBot.exe` (Windows)
- `dist/SafeTrendBot` (Linux — binaire sans extension)

### Build .msi (avancé)

Pour produire un installateur Windows professionnel:

```bash
cd trading_bot
python build_msi.py
# → dist/SafeTrendBot-Setup-5.4.0.msi
```

**Prérequis:**
- **WiX Toolset 3.14** installé sur le système
- Le build `.exe` doit déjà avoir été généré (`build_exe.py` au préalable)

L'installateur `.msi` crée:
- Répertoire d'installation (`Program Files/SafeTrendBot`)
- Raccourci Bureau + Menu Démarrer
- Entrée dans "Ajout/Suppression de programmes"
- Association de fichiers (optionnel)

> **Note**: Le `.msi` est plus professionnel pour la distribution mais le `.exe` standalone fonctionne aussi. Le `.exe` est recommandé pour la majorité des clients (simplicité).

### Installation 1 clic

Le fichier **`INSTALL_WINDOWS.bat`** (à la racine du projet) automatise l'installation pour Windows:

1. Vérifie/installer Python 3.10+
2. Installe les dépendances: `pip install -r trading_bot/requirements.txt`
3. Crée un raccourci sur le Bureau
4. Optionnel: lance le bot

> Ce fichier est fourni aux clients qui préfèrent ne pas utiliser le `.exe` standalone (ex: si Python est déjà installé ou pour modifier le code).

---

## 3. Système de licence

Le système de licence est **autonome**: pas de serveur, pas de hardware lock, pas d'activation en ligne. La validation est 100% locale.

### Format de clé

```
STB5-XXXX-XXXX-XXXX
```

- 4 groupes de 4 caractères séparés par `-`
- Le premier groupe est toujours `STB5`
- Les 3 autres groupes sont alphanumériques (`A-Z`, `0-9`)
- **Checksum**: la somme des valeurs `ord()` de tous les caractères (hors `-`) modulo 97 doit valoir **1**

### Validation (`simple_license.py`)

La validation se fait en deux étapes:

1. **Regex**: `^STB5-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$`
2. **Checksum**: `sum(ord(c) for c in key if c != "-") % 97 == 1`

La classe `SimpleLicense` gère la validation:
```python
from app.core.simple_license import SimpleLicense, generate_key

# Générer une clé
key = generate_key()  # → "STB5-AB12-CD34-EF56" (exemple)

# Valider
lic = SimpleLicense("STB5-AB12-CD34-EF56")
if lic.validate():
    print("Licence valide!")

# En mode libre (placeholder)
lic = SimpleLicense()  # lit __license_embed__.py
lic.is_placeholder()   # → True si __EMBEDDED_KEY__ non remplacé
```

### Embedding dans le build

Le fichier `app/core/__license_embed__.py` contient:
```python
EMBEDDED_KEY = "__EMBEDDED_KEY__"  # placeholder
```

Le processus de build (`build_exe.py`):
1. **Avant build**: réécrit `__license_embed__.py` avec le placeholder propre
2. **Injection**: remplace `__EMBEDDED_KEY__` par la clé réelle
3. **Build PyInstaller**: compile le .exe avec la clé intégrée
4. **Après build** (dans un bloc `finally`): **restaure** le placeholder

> ⚠️ La clé n'est **jamais** committée dans git. Le fichier `__license_embed__.py` reste toujours avec `__EMBEDDED_KEY__` dans le dépôt.

### Vérification au démarrage

`main.py` vérifie la licence au démarrage:
- Si la clé est valide → lancement normal
- Si la clé est invalide ou placeholder → affichage d'un dialogue demandant la clé
- Le mode placeholder permet un usage libre (potentiel) mais affiche un avertissement

### Comment générer une clé pour un client

```bash
cd trading_bot

# Étape 1: Générer une clé
python build_exe.py --generate
# Output: STB5-AB12-CD34-EF56

# Étape 2: Noter la clé précieusement (elle est unique)

# Étape 3: Build le .exe avec cette clé
python build_exe.py --key STB5-AB12-CD34-EF56 --build
# → dist/SafeTrendBot.exe

# Étape 4: Vérifier que la clé a bien été restaurée
cat app/core/__license_embed__.py
# Doit afficher: EMBEDDED_KEY = "__EMBEDDED_KEY__"
```

> **Important**: Toujours vérifier que le placeholder a été restauré après le build. Si le build crash avant le bloc `finally`, le fichier peut rester avec la clé en clair. Dans ce cas, exécuter:
> ```python
> # Restauration manuelle
> from pathlib import Path
> Path("app/core/__license_embed__.py").write_text(
>     '"""Fichier d\'embedding de clé de licence."""\n\n'
>     'EMBEDDED_KEY = "__EMBEDDED_KEY__"\n'
> )
> ```

---

## 4. Workflow de vente

Le processus complet pour livrer le bot à un client:

1. **Client paie 5000€ en crypto** (USDT/USDC/BTC/ETH)
2. **Confirmer la transaction sur blockchain** — vérifier:
   - Le montant exact
   - L'adresse d'envoi
   - Le nombre de confirmations (≥ 3 recommandé)
3. **Générer une clé unique** pour ce client:
   ```bash
   cd trading_bot
   python build_exe.py --generate
   # → STB5-XXXX-XXXX-XXXX (noter cette clé!)
   ```
4. **Build le .exe** avec cette clé:
   ```bash
   python build_exe.py --key STB5-XXXX-XXXX-XXXX --build
   # → dist/SafeTrendBot.exe
   ```
5. **Préparer le package client**:
   - `SafeTrendBot.exe` (le binaire)
   - La clé de licence (`STB5-XXXX-XXXX-XXXX`)
   - `GUIDE_CLIENT.md` (documentation d'utilisation)
   - `INSTALL_WINDOWS.bat` (installation alternative)
6. **Envoyer au client** via le canal convenu (email, Telegram, lien de téléchargement)
7. **Support post-vente** par Telegram si besoin

### Suivi des clés

Il est recommandé de maintenir un fichier de suivi des clés générées (hors git):
```
# keys_log.txt (NE JAMAIS COMMITTER)
Date: 2026-06-22 | Client: XXX | Clé: STB5-AB12-CD34-EF56 | TX: 0x... | Montant: 5000 USDT
Date: 2026-06-25 | Client: YYY | Clé: STB5-GH78-IJ90-KL12 | TX: 0x... | Montant: 5000 USDT
```

---

## 5. Tests

```bash
cd trading_bot
QT_QPA_PLATFORM=offscreen python3 test_bot.py
# 67 tests, doit être 100%
```

Le fichier `test_bot.py` contient une suite de tests personnalisée (framework maison, pas pytest). Le runner `TestRunner` collecte et exécute les tests par catégorie.

### Catégories de tests

Le fichier organise les tests en 8+ catégories principales:

1. **Imports des modules** (`test_imports`) — Vérifie que tous les modules se chargent sans erreur. Sous-catégories:
   - `1-Imports-CORE` — Modules du cœur (`app/core/`)
   - `2-Imports-BROKERS` — Adapters broker (`app/brokers/`)
   - `3-Imports-BOT` — Telegram, news, calendrier (`bot/`)
   - `4-Imports-BACKTEST` — Backtesting (`backtest/`)

2. **Moteur de trading V4** (`test_trading_engine_v4`) — Vérifie que `TradingEngineV4` s'instancie, `get_status()` fonctionne, `set_mode('paper')` fonctionne. Catégorie `5-Engine-V4`.

3. **Brokers adapters** (`test_brokers`) — Vérifie `BrokerType` enum, `get_broker_capabilities()`, `BrokerFactory.list_available()`. Skip intelligent si MT5 non installé. Catégorie `6-Brokers`.

4. **UI main_window** (`test_ui`) — Vérifie que `main_window` peut être importée et instanciée (nécessite PyQt6 + offscreen). Catégorie `7-UI`.

5. **Config manager** (`test_config_manager`) — Vérifie le chargement/sauvegarde de la configuration. Catégorie `8-Config`.

6. **Paper trading** (`test_paper_trading`) — Vérifie le moteur de paper trading (simulation sans broker réel). Catégorie `9-PaperTrading`.

7. **Backtest** (`test_backtest`) — Vérifie le moteur de backtesting sur données historiques. Catégorie `10-Backtest`.

8. **Stratégies** (`test_strategies`) — Vérifie que les 4 stratégies génèrent des signaux corrects sur des données de test. Catégorie `11-Strategies`.

### Exécution

```bash
# Standard (Linux/dev)
QT_QPA_PLATFORM=offscreen python3 test_bot.py

# Sur Windows
python test_bot.py

# Le runner affiche:
# - Le nombre total de tests
# - Les succès/échecs par catégorie
# - Un résumé final: "67/67 tests réussis (100%)"
```

> ⚠️ Si un test échoue, **ne pas livrer**. Investiguer et corriger avant tout build.

---

## 6. Ajouter une stratégie

Les stratégies sont définies dans `app/core/strategies.py`. Le système utilise un pattern Strategy + Voter.

### Structure d'une stratégie

Toutes les stratégies héritent de `BaseStrategy` (ABC):

```python
class BaseStrategy(ABC):
    """Interface commune pour toutes les stratégies"""

    name: str = "BaseStrategy"
    min_bars_required: int = 50  # Minimum de bougies nécessaires

    @abstractmethod
    def analyze(self, data: MarketData) -> StrategySignal:
        """Analyse les données et retourne un signal"""
        pass

    def validate_data(self, data: MarketData) -> bool:
        if len(data.closes) < self.min_bars_required:
            return False
        return True
```

### Types clés

```python
class Signal(Enum):
    BUY = 1
    SELL = -1
    NONE = 0

@dataclass
class MarketData:
    symbol: str
    closes: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    opens: np.ndarray
    volumes: np.ndarray
    timeframe: str
    higher_tf_closes: Optional[np.ndarray] = None  # Multi-timeframe
    higher_tf_timeframe: Optional[str] = None

@dataclass
class StrategySignal:
    signal: Signal
    confidence: float       # 0.0 à 1.0
    strategy_name: str
    reason: str = ""
```

### Étapes pour ajouter une stratégie

**1. Créer la classe stratégie** dans `app/core/strategies.py`:

```python
class MyCustomStrategy(BaseStrategy):
    """Description de ma stratégie."""
    name = "My Custom Strategy"
    min_bars_required = 100

    def __init__(self, param1: int = 14, param2: float = 2.0):
        self.param1 = param1
        self.param2 = param2

    def analyze(self, data: MarketData) -> StrategySignal:
        if not self.validate_data(data):
            return StrategySignal(
                signal=Signal.NONE,
                confidence=0.0,
                strategy_name=self.name,
                reason="Données insuffisantes"
            )

        # Logique de la stratégie
        closes = data.closes
        my_indicator = sma(closes, self.param1)

        current_price = closes[-1]
        current_ind = my_indicator[-1]

        if current_price > current_ind * (1 + self.param2 / 100):
            return StrategySignal(
                signal=Signal.BUY,
                confidence=0.75,
                strategy_name=self.name,
                reason=f"Prix {current_price} > indicateur {current_ind:.2f}"
            )
        elif current_price < current_ind * (1 - self.param2 / 100):
            return StrategySignal(
                signal=Signal.SELL,
                confidence=0.75,
                strategy_name=self.name,
                reason=f"Prix {current_price} < indicateur {current_ind:.2f}"
            )

        return StrategySignal(
            signal=Signal.NONE,
            confidence=0.0,
            strategy_name=self.name,
            reason="Pas de signal"
        )
```

**2. Enregistrer dans la factory** — Modifier la fonction `create_default_voter()` à la fin de `strategies.py`:

```python
def create_default_voter(config) -> StrategyVoter:
    strategies = [
        TrendFollowingStrategy(...),
        MeanReversionStrategy(),
        BreakoutStrategy(),
        MACDStrategy(),
        MyCustomStrategy(),  # ← Ajouter ici
    ]
    return StrategyVoter(
        strategies,
        min_agreement=config.strategy.min_strategies_agreement,
        min_confidence=config.strategy.min_confidence,
    )
```

**3. Tester** avec `test_bot.py`:
```bash
QT_QPA_PLATFORM=offscreen python3 test_bot.py
# Vérifier que la catégorie "Stratégies" passe toujours à 100%
```

> **Note**: Le `StrategyVoter` combine les signaux de toutes les stratégies par vote. Un trade n'est pris que si `min_agreement` stratégies sont d'accord avec une confiance ≥ `min_confidence`. L'ajout d'une stratégie modifie donc la dynamique de vote — tester avec backtest avant de livrer.

### Indicateurs techniques disponibles

Le fichier `strategies.py` fournit déjà ces indicateurs réutilisables:
- `ema(data, period)` — Exponential Moving Average
- `sma(data, period)` — Simple Moving Average
- `rsi(data, period=14)` — Relative Strength Index
- (Bollinger Bands, MACD, ATR implémentés dans les stratégies existantes — voir le code pour référence)

---

## 7. Ajouter un broker

Les adapters broker sont dans `app/brokers/`. Tous implémentent l'interface `BrokerAdapter`.

### Interface `BrokerAdapter`

L'interface abstraite définit les méthodes obligatoires:

```python
class BrokerAdapter(ABC):
    broker_type: BrokerType = None
    capabilities: BrokerCapabilities = None

    # Connexion
    @abstractmethod
    def connect(self, **kwargs) -> bool: ...
    @abstractmethod
    def disconnect(self): ...
    @abstractmethod
    def is_connected(self) -> bool: ...
    @abstractmethod
    def get_last_error(self) -> str: ...

    # Compte
    @abstractmethod
    def get_account_info(self) -> Optional[AccountInfo]: ...

    # Symboles
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]: ...
    @abstractmethod
    def get_tick(self, symbol: str) -> Optional[Tick]: ...
    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, count: int) -> Optional[List[Candle]]: ...
    @abstractmethod
    def select_symbol(self, symbol: str) -> bool: ...
    @abstractmethod
    def list_available_symbols(self) -> List[str]: ...

    # Positions
    @abstractmethod
    def get_positions(self, symbol=None, magic=None) -> List[Position]: ...
    @abstractmethod
    def open_position(self, symbol, order_type, volume, stop_loss, take_profit, magic=0, comment="") -> OrderResult: ...
    @abstractmethod
    def close_position(self, ticket: int) -> OrderResult: ...
    @abstractmethod
    def modify_position(self, ticket, stop_loss=None, take_profit=None) -> OrderResult: ...

    # Helper (non-abstrait, surchargeable)
    def get_candles_arrays(self, symbol, timeframe, count) -> Optional[Dict[str, np.ndarray]]: ...
```

### Étapes pour ajouter un broker

**1. Créer le fichier adapter** dans `app/brokers/`:

```python
# app/brokers/mybroker_adapter.py
"""Adapter pour MyBroker."""

from typing import Optional, List
from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerCapabilities,
    BrokerSupportLevel, AccountInfo, SymbolInfo, Tick,
    Candle, Position, OrderResult, OrderType, OrderStatus,
    BrokerConnectionError, BrokerNotInstalledError,
)


class MyBrokerAdapter(BrokerAdapter):
    """Adapter pour MyBroker."""

    broker_type = BrokerType.MT5  # ou ajouter un nouveau type

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._connected = False
        self._last_error = ""
        self.capabilities = BrokerCapabilities(
            name="MyBroker",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=True,
            supports_cfd=True,
            supports_stocks=False,
            supports_crypto=False,
            supports_trailing_stop=True,
            supports_partial_close=False,
            supports_hedging=False,
            warnings=["Broker expérimental — tester en paper trading d'abord"],
        )

    def connect(self, **kwargs) -> bool:
        try:
            # Logique de connexion spécifique au broker
            self._connected = True
            return True
        except Exception as e:
            self._last_error = str(e)
            raise BrokerConnectionError(f"Connexion échouée: {e}")

    def disconnect(self):
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def get_last_error(self) -> str:
        return self._last_error

    def get_account_info(self) -> Optional[AccountInfo]:
        if not self._connected:
            return None
        # Retourner les infos du compte
        return AccountInfo(
            name="...", server="...", currency="USD",
            balance=0.0, equity=0.0, profit=0.0,
            margin=0.0, margin_free=0.0, margin_level=0.0,
        )

    # ... implémenter toutes les autres méthodes abstraites ...
```

> **Référence**: Voir `mt5_adapter.py` pour un exemple complet et testé.

**2. Ajouter le type de broker** dans `BrokerType` (`app/brokers/broker_adapter.py`):

```python
class BrokerType(Enum):
    MT5 = "mt5"
    XTB = "xtb"
    INTERACTIVE_BROKERS = "ib"
    CTRADER = "ctrader"
    BINANCE = "binance"
    BYBIT = "bybit"
    KRAKEN = "kraken"
    COINBASE = "coinbase"
    MYBROKER = "mybroker"  # ← Ajouter ici
```

Et également dans `app/core/bot_types.py` si l'enum local est utilisé:
```python
class BrokerType(Enum):
    MT5 = "mt5"
    CTRADER = "ctrader"
    XTB = "xtb"
    BINANCE = "binance"
    IC_MARKETS = "icmarkets"
    UNKNOWN = "unknown"
    MYBROKER = "mybroker"  # ← Ajouter ici aussi
```

**3. Ajouter les capacités** dans `get_broker_capabilities()` (`broker_adapter.py`):

```python
def get_broker_capabilities(broker_type: BrokerType) -> BrokerCapabilities:
    # ... cas existants ...
    elif broker_type == BrokerType.MYBROKER:
        return BrokerCapabilities(
            name="MyBroker",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=True,
            supports_cfd=True,
            supports_stocks=False,
            supports_crypto=False,
            supports_trailing_stop=True,
            supports_partial_close=False,
            supports_hedging=False,
            warnings=["Broker expérimental"],
        )
```

**4. Enregistrer dans la factory** (`app/brokers/factory.py`):

```python
def _import_adapters():
    adapters = {}
    # ... adapters existants ...

    # MyBroker
    try:
        from app.brokers.mybroker_adapter import MyBrokerAdapter
        adapters[BrokerType.MYBROKER] = MyBrokerAdapter
        logger.info("MyBroker adapter disponible")
    except ImportError as e:
        logger.warning(f"MyBroker adapter non disponible: {e}")

    return adapters
```

Et ajouter à l'auto-détection si pertinent:
```python
order = preferred or [
    BrokerType.MT5,
    BrokerType.CTRADER,
    BrokerType.XTB,
    BrokerType.BINANCE,
    BrokerType.MYBROKER,  # ← Ajouter
]
```

**5. Exporter dans `__init__.py`** (`app/brokers/__init__.py`):

```python
# Ajouter l'import si nécessaire
from app.brokers.mybroker_adapter import MyBrokerAdapter

# Ajouter à __all__
__all__ = [
    # ... existants ...
    'MyBrokerAdapter',
]
```

**6. Tester**:
```bash
QT_QPA_PLATFORM=offscreen python3 test_bot.py
# Vérifier que la catégorie "Brokers" passe
```

---

## 8. Dépannage développement

### Erreurs courantes

**"Module not found" / ImportError**
```bash
cd trading_bot
pip install -r requirements.txt
```
Vérifier que toutes les dépendances sont installées. Les modules principaux utilisent des imports conditionnels (try/except) pour gérer les librairies optionnelles.

**"PyQt6 not available"**
```bash
pip install PyQt6
```
PyQt6 est requis pour l'interface graphique. Sans PyQt6, seul le mode headless fonctionne.

**"MT5 not available"**
- MetaTrader5 (`MetaTrader5` package) n'est disponible **que sur Windows**
- Sur Linux/macOS, l'adapter MT5 est skip automatiquement (import conditionnel)
- Pour tester le code MT5 sur Linux, mocker le module ou utiliser le paper trading

**Tests en headless (sans display)**
```bash
QT_QPA_PLATFORM=offscreen python3 test_bot.py
```
La variable d'environnement `QT_QPA_PLATFORM=offscreen` permet à PyQt6 de s'exécuter sans serveur X. Essentiel pour CI/CD et tests sur VPS.

**Build PyInstaller échoue**
- Vérifier que PyInstaller est installé: `pip install pyinstaller`
- Vérifier que la clé de licence est valide avant le build
- Consulter le log PyInstaller dans `build/` pour les détails
- Si le build crash, vérifier que `__license_embed__.py` a été restauré (le bloc `finally` dans `build_exe.py` le fait normalement)

**Clé de licence invalide**
```bash
# Tester une clé
python -c "from app.core.simple_license import SimpleLicense; print(SimpleLicense('STB5-XXXX-XXXX-XXXX').validate())"
```
Si `False`, la clé ne respecte pas le format ou le checksum mod 97.

**"No broker available"**
- Aucun adapter broker n'a pu être importé
- Vérifier que les librairies broker sont installées (ex: `pip install MetaTrader5`)
- En paper trading, aucun broker réel n'est nécessaire

---

## 9. Commandes utiles

Toutes les commandes s'exécutent depuis `trading_bot/` sauf indication contraire.

### Développement

```bash
# Interface graphique (PyQt6)
python main.py

# Mode headless / serveur (sans GUI, pour VPS)
python main.py --headless
# ou
python headless.py

# Installer les dépendances
pip install -r requirements.txt
```

### Tests

```bash
# Suite complète (67 tests)
QT_QPA_PLATFORM=offscreen python3 test_bot.py

# Sur Windows
python test_bot.py
```

### Build et distribution

```bash
# Générer une clé de licence
python build_exe.py --generate

# Build .exe avec clé générée automatiquement
python build_exe.py --generate --build

# Build .exe avec clé spécifique
python build_exe.py --key STB5-XXXX-XXXX-XXXX --build

# Build .msi (avancé, nécessite WiX Toolset 3.14)
python build_msi.py
```

### Licence

```bash
# Tester le système de licence
python -c "from app.core.simple_license import generate_key, SimpleLicense; k=generate_key(); print(k, SimpleLicense(k).validate())"
```

### Broker factory

```bash
# Lister les brokers disponibles
python -c "from app.brokers.factory import list_brokers; print([b.value for b in list_brokers()])"
```

---

## 10. Checklist avant livraison client

Avant d'envoyer le bot à un client, vérifier chaque point:

- [ ] **Tests passent à 100%** — `QT_QPA_PLATFORM=offscreen python3 test_bot.py` → 67/67
- [ ] **.exe buildé avec clé unique** — `dist/SafeTrendBot.exe` généré avec `--key STB5-XXXX`
- [ ] **Clé notée dans un fichier** — garder une trace hors git (date, client, clé, TX hash)
- [ ] **Placeholder restauré** — `app/core/__license_embed__.py` contient bien `__EMBEDDED_KEY__`
- [ ] **GUIDE_CLIENT.md inclus** — documentation d'utilisation pour le client
- [ ] **INSTALL_WINDOWS.bat inclus** — installation alternative 1-clic
- [ ] **Transaction crypto confirmée** — ≥ 3 confirmations sur la blockchain
- [ ] **Package complet** — .exe + clé + GUIDE_CLIENT.md + INSTALL_WINDOWS.bat
- [ ] **Test du .exe** (optionnel mais recommandé) — lancer le .exe sur une machine Windows de test
- [ ] **Canal de support défini** — Telegram ou autre, communiqué au client

---

> **Rappel**: Ce guide est **strictement interne**. Ne jamais l'inclure dans le package client.
> Le client reçoit uniquement: `SafeTrendBot.exe` + clé de licence + `GUIDE_CLIENT.md` + `INSTALL_WINDOWS.bat`.