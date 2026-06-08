# SafeTrendBot v2.0 — Nouvelles fonctionnalités

Cette version ajoute 10 fonctionnalités avancées qui transforment le bot d'un simple exécuteur de stratégie en un système professionnel.

---

## 🥇 Priorité haute

### 1. Trailing stop dynamique
Une fois qu'un trade atteint +2R de profit, le stop loss commence à suivre le prix à distance de 1R. Les profits sont verrouillés progressivement et le trade ne peut plus redevenir perdant.

**Fichier :** `app/core/position_manager.py`
**Visible dans :** le dashboard montre les positions "en trailing"

### 2. Break-even automatique
Dès que le trade atteint +1R (risque initial), le stop loss est déplacé au prix d'entrée + une petite marge (couvrant spread/commission). Le trade devient "sans risque".

**Comment ça marche ?** Le position_manager surveille chaque position et modifie le SL automatiquement via `mt5.order_send(TRADE_ACTION_SLTP)`.

### 3. Filtre de volatilité (ATR)
Le bot compare la volatilité actuelle (ATR sur 14 périodes) à la médiane des 200 dernières bougies :

- **< 0.5x** : marché mort → pas de trade (signaux faux)
- **0.5-0.75x** : volatilité basse mais tradable
- **0.75-1.5x** : normal
- **1.5-3x** : volatilité élevée
- **> 3x** : extrême → pas de trade (chaos, spreads explosés)

**Fichier :** `app/core/market_filters.py` → `VolatilityFilter`

### 4. Rapports PDF hebdomadaires
Génération automatique chaque dimanche à 20h (et à la demande). Contient :

- Page de garde avec résumé
- Statistiques détaillées (win rate, profit factor, avg win/loss...)
- Courbe d'équité graphique
- Analyse par stratégie
- Liste des trades de la semaine

**Fichier :** `app/core/pdf_reports.py`
**Accès UI :** Onglet Analyses → bouton "Générer rapport PDF"

### 5. Mode paper trading
Bascule entre mode LIVE (vrai compte) et PAPER (simulation). Le mode paper utilise les vraies données de marché en temps réel mais n'envoie aucun ordre au broker.

**Parfait pour :**
- Tester de nouveaux paramètres sans risque
- Valider une stratégie avant le live
- S'entraîner

**Fichier :** `app/core/paper_trading.py`
**Accès UI :** Onglet Paper Trading

---

## 🥈 Priorité moyenne

### 6. Multi-stratégies avec vote
Au lieu d'une seule stratégie, 4 stratégies indépendantes analysent en parallèle :

1. **Trend Following** (EMA + RSI) — la stratégie originale
2. **Mean Reversion** (Bollinger Bands + RSI) — trades contre la tendance
3. **Breakout** (Donchian Channels) — cassures de range
4. **MACD Momentum** — croisements MACD

Un trade n'est pris que si **au moins 2 stratégies sont d'accord** sur la direction. Réduit massivement les faux signaux.

**Fichier :** `app/core/strategies.py`

### 7. Analyse multi-timeframes
Le signal principal est calculé sur le timeframe du symbole (ex: H4). Mais le bot récupère aussi le timeframe supérieur (ex: D1) pour confirmer la tendance de fond. Un long sur H4 n'est pris que si le D1 confirme.

**Implémentation :** `MarketData.higher_tf_closes`

### 8. Filtre de corrélation
Empêche d'ouvrir des positions fortement corrélées dans la même direction. Exemple : si vous avez déjà EURUSD long, et qu'un signal d'achat apparaît sur GBPUSD (corrélation ~85%), le trade est bloqué — sinon vous doublez le risque sans diversifier.

**Fichier :** `app/core/market_filters.py` → `CorrelationFilter`

### 9. Journal de trading automatique
Chaque trade est enregistré avec son contexte complet :

- Prix d'entrée, SL, TP, volume
- Score de confiance
- Stratégies qui ont voté pour
- Régime de volatilité
- ATR au moment de l'entrée
- Prix/heure de sortie, raison, profit

**Analyses disponibles :**
- Performance par stratégie (quelle stratégie gagne le plus ?)
- Performance par symbole
- Performance par heure de la journée
- Performance par régime de volatilité
- Performance par niveau de confiance

**Fichier :** `app/core/trade_journal.py`
**Accès UI :** Onglet Analyses

### 10. Circuit breaker intelligent
Coupe automatiquement le trading si l'une de ces conditions est atteinte :

- **Drawdown > 15%** depuis le pic d'équité
- **5 pertes consécutives**
- **Perte horaire > 2%** (P&L instable)
- **10 erreurs dans la dernière heure** (problèmes techniques)

Deux niveaux : WARNING (alerte) et HALT (arrêt complet). Reset manuel requis après un HALT.

**Fichier :** `app/core/market_filters.py` → `CircuitBreaker`

---

## 🏗️ Architecture mise à jour

```
app/core/
├── config_manager.py          # Configuration (inchangé)
├── trading_engine.py          # Ancien moteur (conservé pour référence)
├── trading_engine_v2.py       # NOUVEAU : moteur intégrant tout
├── strategies.py              # NOUVEAU : framework multi-stratégies
├── position_manager.py        # NOUVEAU : trailing stop + break-even
├── market_filters.py          # NOUVEAU : volatilité + corrélation + CB
├── paper_trading.py           # NOUVEAU : mode simulation
├── trade_journal.py           # NOUVEAU : journal automatique
└── pdf_reports.py             # NOUVEAU : rapports PDF

app/ui/views/
├── dashboard_view.py
├── positions_view.py
├── backtest_view.py
├── calendar_view.py
├── news_view.py
├── logs_view.py
├── settings_view.py
├── analytics_view.py          # NOUVEAU : analyses détaillées
└── paper_trading_view.py      # NOUVEAU : gestion mode paper
```

**9 vues** dans la sidebar maintenant :
Dashboard · Positions · **Analyses** · Backtest · **Paper Trading** · Calendrier éco · Actualités · Journaux · Paramètres

---

## 🎯 Workflow recommandé avec v2.0

### 1. Phase d'apprentissage (2 semaines)
- Mode **Paper Trading**
- Observer comment les stratégies votent
- Consulter régulièrement l'onglet **Analyses**
- Identifier quelle stratégie fonctionne le mieux sur votre instrument

### 2. Phase de tuning (2 semaines)
- Toujours en paper
- Ajuster les paramètres selon les analyses
- Vérifier que le circuit breaker n'est pas déclenché
- Générer des rapports PDF hebdo

### 3. Phase de test réel (2-3 mois)
- Compte **démo** chez un broker régulé
- Mode LIVE
- Très petit capital
- Continuer les rapports PDF, les analyses

### 4. Production
- Compte réel, uniquement après toutes les phases précédentes
- Capital limité
- Surveillance hebdomadaire via les rapports PDF

---

## 📊 Exemples d'analyses utiles

### "Quelle stratégie dois-je désactiver ?"
Onglet Analyses → Par stratégie
→ Celle avec le win rate le plus bas ET profit négatif

### "À quelles heures le bot performe-t-il le mieux ?"
Onglet Analyses → Par heure
→ Ajuster `start_hour` et `end_hour` dans les paramètres

### "Les trades à haute confiance sont-ils plus rentables ?"
Onglet Analyses → Par confiance
→ Si oui : augmenter `min_confidence` dans le voter
→ Si non : le score de confiance ne sert à rien, à revoir

### "Le bot perd-il en haute volatilité ?"
Onglet Analyses → Par volatilité
→ Si EXTREME perd toujours : `extreme_ratio` du filtre à baisser

---

## 🔧 Configuration avancée du voter

Par défaut : 4 stratégies, minimum 2 d'accord, confiance min 0.4.

Pour ajuster dans le code (`app/core/strategies.py` → `create_default_voter`) :

```python
return StrategyVoter(
    strategies,
    min_agreement=3,        # Plus strict : 3/4 requis
    min_confidence=0.6,     # Plus strict : 60% de confiance min
)
```

Plus strict = moins de trades mais meilleure qualité.

---

## 📝 Notes de migration depuis v1

Si vous utilisiez la v1.0 :

1. **Configuration** : compatible, sera lue automatiquement
2. **Profils sauvegardés** : compatibles
3. **Journal de trading** : se construit automatiquement à partir de maintenant
4. **Moteur V1 (trading_engine.py)** : conservé mais non utilisé
5. **Installation** : `pip install reportlab` en plus

---

## 💡 Ce qui n'a PAS été ajouté (volontairement)

Voir la discussion initiale. En résumé :
- Pas de connexion Twitter/X ou Telegram signals (statistiquement perdant)
- Pas de ML/deep learning (overfitting quasi-garanti)
- Pas de grid/martingale (explosent toujours)
- Pas de scalping HFT (impossible contre les pros avec 50ms+ de latence)

Ce qui est dans v2.0 représente ce que font réellement les trading desks pros — et **rien de plus**.
