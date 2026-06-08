# SafeTrendBot V5 — Incroyable

Bot de trading automatisé multi-broker avec intelligence adaptative.

> ⚠️ **Avertissement** : le trading comporte des risques de perte en capital.
> Toujours commencer par du **paper trading** avant tout usage en réel.

## 🚀 Ce qui est "incroyable" dans V5

### Intelligence Adaptative
- 🌊 **Régime de marché temps réel** : détecte Trending / Ranging / Volatile / Crash / Recovery
- 🧠 **Stratégies auto-ajustables** : pondère dynamiquement les 4 stratégies selon le régime
- 📉 **Risk Manager Kelly** : ajuste le sizing selon le Kelly Criterion
- 🎯 **Drawdown dynamique** : réduit le risque progressivement si le drawdown augmente

### Analyse Avancée
- 📊 **Sharpe / Sortino / Calmar** temps réel
- 🔥 **Heatmap des performances** par heure
- 📈 **Expectancy** et Win Rate dynamique
- 🏆 **Profit Factor** tracking

### Interface V5
- 🪟 **System Tray** avec mini dashboard rapide
- 🎨 **UI repensée** : titre SafeTrendBot V5
- ⚡ **Mode headless** : `python headless.py --paper` pour VPS/cloud

## Fonctionnalités complètes

| Domaine | Feature | V4 | V5 |
|---------|---------|----|----|
| Brokers | MT5, XTB, IB, cTrader, 4 cryptos | ✅ | ✅ |
| Stratégies | Trend, MeanRev, Breakout, MACD | ✅ | ✅✨ adaptatif |
| Risk | Circuit breaker, filtres vol/corr | ✅ | ✅✨ Kelly + DD dynamique |
| Régime | Détection de marché | ❌ | ✅ |
| Métriques | Sharpe, Sortino, Expectancy | ❌ | ✅ |
| Tray | Mini dashboard | ❌ | ✅ |
| Headless | Mode sans UI | ❌ | ✅ |
| Paper | Simulation complète | ✅ | ✅ |

## Installation rapide

```batch
1. Extraire le ZIP dans C:\trading_bot\
2. Lancer install.bat
3. Lancer LANCEZ_MOI.bat
```

## Mode Headless (VPS/Cloud)

```bash
python headless.py --paper --symbols EURUSD,GBPUSD
```

## Stack
- Python 3.10+, PyQt6, numpy, pandas
- MT5, ib_insync, ccxt, yfinance

## Architecture
Voir `ARCHITECTURE_V5.md`.

Projet personnel, utilisation à vos risques.
