# Changelog SafeTrendBot

## v4.3 — Avril 2026 (cette version)

### Nouveau
- 🛠️ Onglet "Outils" avec calculator de position, export CSV, mode lecture seule
- 📋 Watchlist (module créé, UI à brancher)
- 📐 Position calculator : calcul automatique de la taille de position selon le risque
- 📤 Export CSV de l'historique des trades (séparateur ";" pour Excel français)
- 👁️ Mode lecture seule : le bot analyse mais n'ouvre aucune position (pour observation)
- 📚 Documentation complète : `ARCHITECTURE.md` et `ROADMAP.md` pour reprise du projet

### Amélioré
- Audit qualité du code : 0 TODO bloquant, 1 commentaire mineur
- Configuration version 2.1.0 (ajout `read_only_mode`, `security` PIN, `active_profile`)

## v4.2 — Avril 2026

### Nouveau
- 🔐 Système de PIN complet (PBKDF2-SHA256, pavé numérique, verrouillage démarrage et trading)
- 🎯 Onglet "Profils trading" : 3 modes Safe / Normal / Aggressive + 3 stratégies pures
- 📉 Onglet "Tendances 5 ans" : analyse via yfinance avec Sharpe ratio, drawdown, volatilité
- 📚 3 stratégies pures documentées (Tortues, Bollinger/Wilder, Edwards & Magee)

## v4.1 — Avril 2026

### Nouveau
- 🕐 Onglet "Horaires marchés" : statut temps réel des sessions forex et bourses actions

## v4.0 — Avril 2026

### Nouveau
- 🏦 Support de 8 plateformes : MT5, XTB, IB, cTrader, Binance, Bybit, Kraken, Coinbase
- Adapter unifié `crypto_adapter.py` via ccxt

## v3.10 — Avril 2026

### Corrigé
- Bug du thème clair : refactoring complet via objectName + stylesheet global

## v3.9 — Avril 2026

### Refactor
- Architecture des thèmes : tous les widgets utilisent objectName au lieu de stylesheets inline

## v3.7 — Avril 2026

### Modifié
- Mode sombre par défaut, désactivation temporaire du mode clair

## v3.4 — Avril 2026

### Corrigé
- KeyError 'surface_variant' au démarrage
- Interface broker simplifiée pour MT5

## v3.0 — Avril 2026

### Nouveau
- Multi-stratégies avec système de vote (4 stratégies)
- Filtres : volatilité, corrélation, circuit breaker
- Trailing stop + break-even auto
- Paper trading avec données réelles
- Trade journal + analyses (5 dimensions)
- Rapports PDF hebdomadaires
- Filtre news via ForexFactory RSS

## v2.0 — Avril 2026

### Nouveau
- Refonte UI complète en PyQt6
- Multi-broker (MT5 + abstraction layer)

## v1.0 — Avril 2026

### Initial
- EA MQL5 SafeTrendBot.mq5 (référence)
- Bot Python basique avec MT5
