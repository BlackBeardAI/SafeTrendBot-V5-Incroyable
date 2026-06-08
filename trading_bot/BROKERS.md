# SafeTrendBot v3.0 — Support Multi-Broker

Cette version ajoute le support de plusieurs brokers via une couche d'abstraction. Le code du moteur ne connaît pas le broker utilisé — il parle à une interface commune `BrokerAdapter`.

---

## 🎯 Brokers supportés

| Broker | Statut | Protocole | Installation |
|--------|--------|-----------|--------------|
| **MetaTrader 5** | 🟢 Supporté | Bibliothèque officielle Python | `pip install MetaTrader5` (Windows) |
| **XTB xStation** | 🟡 Expérimental | xAPI (JSON/WebSocket) | Inclus (socket pur) |
| **Interactive Brokers** | 🟡 Expérimental | TWS API via ib_insync | `pip install ib_insync` |

**Tous les brokers sont installés par défaut** via `install.bat`.

---

## 🟢 MetaTrader 5 (recommandé)

**Pourquoi c'est le choix par défaut :**
- Bibliothèque Python officielle, maintenue par MetaQuotes
- Disponible chez 100+ brokers (IC Markets, Pepperstone, XM, Admiral, RoboForex, FBS, FXCM, etc.)
- Support complet : forex, CFD, actions, crypto, indices, matières premières
- Hedging supporté (plusieurs positions par symbole)
- Trailing stop serveur
- Stable et testé

**Prérequis :**
- Windows uniquement
- Terminal MT5 installé et lancé
- Compte chez n'importe quel broker MT5

**Configuration :**
- Mode auto-detect (par défaut) : utilise le terminal MT5 déjà connecté
- Mode manuel : renseigner login + mot de passe + serveur

**Limitations :** aucune connue pour le scope de ce bot.

---

## 🟡 XTB xStation

**Avertissements critiques :**

> ⚠️ **XTB peut bloquer les comptes qui utilisent du trading automatisé non autorisé.**
> Contactez le support XTB pour autoriser l'API sur votre compte avant toute utilisation.

> ⚠️ **xAPI est non-officielle.** Bien que XTB la documente, elle n'est pas garantie stable dans le temps.

**Pourquoi c'est inclus quand même :**
- Accès à un broker européen régulé (KNF Pologne, FCA UK, BaFin Allemagne)
- Pas besoin d'installer MT5 ou TWS
- Bon pour utilisateurs qui ont déjà un compte XTB

**Prérequis :**
- Compte XTB xStation5
- API activée par le support XTB
- Numéro de compte + mot de passe

**Limitations techniques :**
- **Pas de hedging** : une seule position par symbole
- **Pas de trailing stop côté serveur** : géré côté client uniquement
- Commandes en temps réel moins précises (pas de streaming dans cet adapter)
- Pas de magic number (les positions ne peuvent pas être filtrées par bot)

**Configuration :**
1. Onglet Broker → sélectionner "XTB xStation"
2. User ID : votre numéro de compte XTB (ex: 12345678)
3. Password : votre mot de passe de trading
4. Démo activé par défaut (**fortement recommandé**)

**Commencez IMPÉRATIVEMENT en démo.** XTB fournit un compte démo gratuit sur leur site.

---

## 🟡 Interactive Brokers

**Avantages :**
- Courtier américain majeur, très réputé
- Accès à tous les marchés mondiaux (forex, actions US/EU/Asie, futures, options, obligations)
- Commissions compétitives pour gros volumes
- API officielle et robuste

**Inconvénients :**
- Complexe à configurer
- Dépôt minimum non négligeable (souvent 10 000 USD pour certains marchés/data)
- Frais de market data live séparés
- Pas de hedging (comptes US, imposé par la réglementation)

**Prérequis :**

1. **Compte Interactive Brokers actif**
2. **TWS (Trader Workstation) ou IB Gateway installé et lancé**
   - TWS : interface complète de trading
   - IB Gateway : version minimaliste, recommandée pour les bots
3. **API activée dans TWS :**
   - Menu `Configure` > `API` > `Settings`
   - ✅ Cocher **"Enable ActiveX and Socket Clients"**
   - ❌ **DÉCOCHER** "Read-Only API" (sinon pas de trading possible)
   - Ajouter `127.0.0.1` aux "Trusted IPs"
   - Définir le "Master API client ID" à 0 (ou ce que vous voulez, mais reproduire dans le bot)
4. **Permissions de trading** activées sur les instruments visés (demander au support IB si besoin)

**Ports standards :**

| Application | Mode | Port |
|-------------|------|------|
| TWS | Démo (paper trading) | 7497 |
| TWS | Live | 7496 |
| IB Gateway | Démo | 4002 |
| IB Gateway | Live | 4001 |

**Mapping des symboles (différent de MT5) :**

| Instrument | Syntaxe MT5 | Syntaxe IB |
|-----------|-------------|------------|
| Forex EUR/USD | `EURUSD` | `EURUSD` (sans slash) |
| Action Apple | n/a | `AAPL` |
| Action Tesla | n/a | `TSLA` |
| CFD DAX | `GER40` | `CFD:DAX` ou à configurer manuellement |

L'adapter essaie de détecter automatiquement le type de contrat, mais pour les CFD/indices vous devrez peut-être adapter. Pour 95% des cas forex, ça fonctionne directement.

**Configuration dans le bot :**
1. Onglet Broker → sélectionner "Interactive Brokers"
2. Host : `127.0.0.1` (par défaut)
3. Port : `7497` pour TWS démo
4. Client ID : `1` (ou ce que vous voulez, à condition qu'il soit unique)
5. Lancer TWS ou Gateway AVANT de démarrer le bot

---

## 🏗️ Architecture technique

```
app/brokers/
├── __init__.py                 # Exports publics
├── broker_adapter.py           # Interface abstraite BrokerAdapter
├── mt5_adapter.py              # Implémentation MT5
├── xtb_adapter.py              # Implémentation XTB (xAPI)
├── ib_adapter.py               # Implémentation IB (ib_insync)
└── factory.py                  # create_broker_adapter()
```

### Interface `BrokerAdapter`

Toutes les méthodes sont normalisées :

```python
class BrokerAdapter:
    # Connexion
    connect(**kwargs) -> bool
    disconnect()
    is_connected() -> bool
    get_last_error() -> str

    # Compte
    get_account_info() -> AccountInfo

    # Symboles
    get_symbol_info(symbol) -> SymbolInfo
    get_tick(symbol) -> Tick
    get_candles(symbol, timeframe, count) -> List[Candle]
    get_candles_arrays(...) -> Dict[str, np.ndarray]  # optimisé

    # Positions
    get_positions(symbol, magic) -> List[Position]
    open_position(...) -> OrderResult
    close_position(ticket) -> OrderResult
    modify_position(ticket, sl, tp) -> OrderResult
```

Le moteur V3 n'utilise QUE cette interface. Ajouter un nouveau broker = créer une nouvelle classe `BrokerAdapter`.

### Structures normalisées

Toutes les données (comptes, positions, bougies, ticks) sont converties en classes uniformes, indépendamment du broker :

- `AccountInfo`
- `SymbolInfo`
- `Position`
- `Tick`
- `Candle`
- `OrderResult`
- `BrokerCapabilities`

---

## ➕ Ajouter un autre broker

Pour ajouter un nouveau broker (ex: cTrader, Binance) :

1. Créer `app/brokers/mon_broker_adapter.py` qui implémente `BrokerAdapter`
2. Ajouter dans `factory.py` :
   ```python
   elif broker_type == BrokerType.MON_BROKER:
       from app.brokers.mon_broker_adapter import MonBrokerAdapter
       return MonBrokerAdapter()
   ```
3. Ajouter le type dans `BrokerType` enum et `get_broker_capabilities()`
4. Ajouter le panneau de config dans `BrokerView`

Le moteur V3 n'a pas besoin d'être modifié.

---

## ⚠️ Brokers que je n'ai PAS ajoutés (et pourquoi)

### Pas d'API publique
- **eToro** : pas d'API trading pour comptes retail
- **Trading 212** : pas d'API publique
- **Robinhood** : API fermée depuis 2021
- **Boursorama, Bourse Direct, Degiro** (retail FR) : aucune API

### API crypto (hors scope)
- **Binance, Bybit, Kraken, Coinbase** : APIs excellentes mais crypto, pas forex/CFD. Si vous voulez trader du crypto, c'est un autre projet.

### Technique pas adaptée
- **cTrader** : a une Open API mais peu de brokers la supportent, protocole FIX complexe. Possible à ajouter sur demande.
- **MetaTrader 4** : pas d'API Python officielle, seulement MQL4 compilé. Obsolète.

---

## 🎯 Recommandation

**Si vous débutez :** MetaTrader 5 avec un broker régulé européen (IC Markets CySEC, Pepperstone FCA, Admiral BaFin). C'est le chemin testé.

**Si vous avez déjà un compte XTB :** testez l'adapter XTB en démo d'abord. Si ça fonctionne bien pour vos besoins et que XTB autorise votre compte, tant mieux.

**Si vous êtes pro / gros volume :** Interactive Brokers via IB Gateway est l'option la plus professionnelle. Commissions moindres, accès à tous les marchés, API stable.

**Dans tous les cas :** commencez en mode paper trading ou sur un compte démo pendant 2-4 semaines minimum avant de passer au réel.
