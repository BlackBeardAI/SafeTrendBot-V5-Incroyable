# Changelog — SafeTrendBot V5

## V5.4.0 (22 juin 2026)

### Breaking changes
- **Suppression du système de protection** (license_manager, anti_tamper, extreme_guard, encryption → stubs neutralisés)
- **Consolidation des 4 engines → 1** (TradingEngineV4 unique + bot_types.py)
- **Prix fixé à 10000€** en crypto (one-shot)

### Features ajoutées
- Mode démo par défaut (paper trading, pas live)
- Onboarding wizard PyQt6 (3 étapes: broker → risque → confirmation)
- Raccourcis clavier (Ctrl+S/X/P/B/D, F1)
- Backup config auto (max 5 backups)
- Système de licence simple (clé STB5-XXXX-XXXX-XXXX embedded, pas de serveur)
- build_exe.py: build .exe onefile avec injection de clé
- test_bot.py: 67 tests, 100% de réussite
- Page de vente HTML (index.html)
- Guide client (GUIDE_CLIENT.md)
- Guide développeur (GUIDE_DEV.md)
- Page de vente markdown (PAGE_VENTE.md)

### Bugs corrigés
- list_available_brokers manquant dans factory.py
- TradeDirection/TradeResult non importés dans xtb_adapter
- setValue(float) dans settings_view, telegram_view, strategy_params_view
- PinConfig.require_pin_for_trading manquant
- Import circulaire broker_factory → trading_engine
- dashboard_view: BotState importé depuis mauvais module

### Code mort supprimé (6 fichiers, ~1900 lignes)
- trading_engine_v2.py (777 lignes)
- trading_engine_v3.py (654 lignes)
- position_manager.py (200 lignes)
- watchlist.py (176 lignes)
- ib_adapter.py (497 lignes)
- mt5_bridge.py (263 lignes)

### Nettoyage (32 fichiers supprimés)
- Vieux .bat d'installation (12 fichiers)
- crypto_sales/, builder/, server/, admin_dashboard/
- Docs redondants (8 fichiers)
- build_generator.py, build_release.py, builder.py, etc.

### Chiffres
- 123 → 91 fichiers .py (-26%)
- 4 → 1 engine de trading
- 100% tests passent (66/66, 1 skip MT5)
- -3333 lignes supprimées