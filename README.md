# SafeTrendBot V5 — Trading Bot Automatisé

Bot de trading automatisé multi-broker avec interface desktop PyQt6.

## ✨ Fonctionnalités

- 🖥️ **Interface desktop moderne** (PyQt6, thème sombre/clair)
- 📊 **Multi-broker** : MetaTrader 5, cTrader, XTB, Binance, Interactive Brokers
- 📈 **Stratégies adaptatives** : détection de régime de marché, triple-screen
- 🧪 **Paper trading** intégré (sans argent réel)
- 📉 **Backtesting** complet avec walk-forward analysis
- 📅 **Calendrier économique** et filtre de news
- 📱 **Alertes Telegram** en temps réel
- 📋 **Journal de trading** automatique
- 📊 **Analytics** : performance, drawdown, Sharpe ratio
- 🎯 **Watchlist** et recommandations
- ⚙️ **Profils de trading** : Safe, Normal, Aggressive, Extreme
- 🛡️ **Risk management** : circuit breakers, gestion de portefeuille

## 🚀 Installation

### Windows (1 clic)

1. Téléchargez le fichier `INSTALL_WINDOWS.bat`
2. **Clic droit → Exécuter en tant qu'administrateur**
3. L'installation se fait automatiquement (Python + dépendances + raccourci)

### Installation manuelle

```bash
# Prérequis: Python 3.11+
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
cd SafeTrendBot-V5-Incroyable/trading_bot
pip install -r requirements.txt
python main.py
```

### Créer un installateur .msi

```bash
# Prérequis: WiX Toolset 3.14 (https://wixtoolset.org/releases/)
python build_msi.py
# → dist/SafeTrendBot-Setup-5.4.0.msi
```

## 📁 Structure

```
SafeTrendBot-V5-Incroyable/
├── INSTALL_WINDOWS.bat          ← Installation 1 clic
├── build_msi.py                 ← Créateur d'installateur .msi
├── trading_bot/
│   ├── main.py                  ← Point d'entrée (interface PyQt6)
│   ├── headless.py              ← Mode serveur sans GUI
│   ├── app/
│   │   ├── core/                ← Moteur de trading, stratégies, risk
│   │   ├── brokers/             ← Adaptateurs broker (MT5, cTrader, etc.)
│   │   └── ui/                  ← Interface PyQt6 + 18 vues
│   ├── bot/                     ← Telegram, news, calendrier
│   └── backtest/                ← Backtesting engine
└── dist/                        ← Build output (.exe, .msi)
```

## 🎯 Utilisation

### Interface graphique

```bash
python main.py
```

### Mode headless (serveur)

```bash
python main.py --headless
```

## ⚙️ Configuration

- Fichier config : `%APPDATA%/SafeTrendBot/config.json` (Windows)
- Logs : `%USERPROFILE%/.safetrendbot/bot.log`

## 🔧 Broker supportés

| Broker | Type | Statut |
|--------|------|--------|
| MetaTrader 5 | Forex/CFD | ✅ |
| cTrader | Forex/CFD | ✅ |
| XTB | Forex/CFD | ✅ |
| Binance | Crypto | ✅ |
| Interactive Brokers | Multi-asset | ✅ |

## 📊 Vues de l'interface

1. **Dashboard** — Vue d'ensemble (équity, positions, P&L)
2. **Positions** — Positions ouvertes et historique
3. **Backtest** — Tester les stratégies sur données historiques
4. **Paper Trading** — Trading simulé
5. **Analytics** — Métriques de performance
6. **Calendar** — Calendrier économique
7. **News** — Actualités financières
8. **Broker** — Connexion et paramètres broker
9. **Telegram** — Configuration des alertes
10. **Market Hours** — Horaires de marché
11. **Profiles** — Profils de trading
12. **Trend Analysis** — Analyse de tendances
13. **Watchlist** — Liste de surveillance
14. **Recommendations** — Recommandations de trading
15. **Strategy Params** — Paramètres de stratégie
16. **Tools** — Outils utilitaires
17. **Logs** — Logs en temps réel
18. **Settings** — Paramètres de l'application

## 💰 Tarif

**Prix unique: 10000€** (payable en crypto au cours du BTC)

- Paiement one-shot en BTC/ETH/USDT
- Pas d'abonnement, pas de frais récurrents
- Mises à jour gratuites à vie
- Support par Telegram

Wallets:
- **BTC**: `bc1qxxzn05t7jvdmz47ncnxlglczhh9aet3gcpt5dx`
- **ETH/USDT**: `0xd1c2ef7f724635fa0ed327f4d626620a2adffd82`

## 📜 License

Projet commercial — © 2026 BlackBeardAI

## 📞 Support

- **GitHub** : https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable

---

**Version** : 5.4.0 — Mode Libre