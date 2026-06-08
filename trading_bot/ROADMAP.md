# SafeTrendBot — Roadmap pour reprise du projet

> Liste priorisée d'améliorations légitimes, avec contexte, difficulté estimée
> et pièges à éviter.

---

## 🚨 À LIRE AVANT TOUT

### Ce que cette application est
Un outil pour **automatiser des trades selon des règles fixes**, avec interface complète,
multi-broker, et toutes les sécurités habituelles (circuit breakers, filtres, etc.).

### Ce que cette application n'est PAS
- ❌ Une "machine à imprimer de l'argent"
- ❌ Un robot magique qui devine les marchés
- ❌ Un substitut au cerveau humain pour les décisions de trading

### Règle d'or pour toute IA reprenant le projet
> Si l'utilisateur demande de "rendre le bot plus agressif" ou "qu'il trade plus",
> la **bonne** réponse est presque toujours :
> 1. Lui demander pourquoi
> 2. Vérifier qu'il a fait du paper trading suffisant
> 3. L'orienter vers une analyse plutôt que vers des changements de paramètres
>
> Plus de trades = plus de frais + plus d'erreurs cumulées. Statistiquement,
> 70-90% des traders retail perdent leur argent (source: AMF/ESMA). Ne pas
> alimenter cette tendance.

---

## ✅ Tâches concrètes par priorité

### Priorité 1 — Solidité (à faire avant tout le reste)

#### 1.1 Tests unitaires
**Difficulté** : moyenne. **Temps estimé** : 1 jour.
- Couvrir au minimum :
  - `app/core/strategies.py` (calcul ATR, EMA, RSI, MACD)
  - `app/core/position_calculator.py` (taille de position)
  - `app/core/market_filters.py` (volatilité, corrélation)
  - `app/core/pin_lock.py` (hash + verify)
- Utiliser `pytest`. Cible : 60% de couverture sur le dossier `core/`.

#### 1.2 Logging structuré
**Difficulté** : facile. **Temps estimé** : 2 heures.
- Remplacer les `print()` épars par `logging.getLogger(__name__)`
- Niveau DEBUG/INFO/WARNING/ERROR
- Rotation des fichiers via `RotatingFileHandler`

#### 1.3 Backup config avant écriture
**Difficulté** : facile. **Temps estimé** : 30 min.
- Avant `config_manager.save()`, copier l'ancien fichier vers `config.json.bak`
- Si la sauvegarde nouvelle échoue, restaurer depuis `.bak`

### Priorité 2 — Confort utilisateur

#### 2.1 Internationalisation
**Difficulté** : moyenne. **Temps estimé** : 1 jour.
- Tout est en français hardcodé actuellement
- Utiliser `Qt Linguist` ou `gettext`
- Faire au moins FR + EN

#### 2.2 Mode replay
**Difficulté** : moyenne. **Temps estimé** : 1-2 jours.
- Rejouer historique sur N jours/mois pour voir trades qui auraient été pris
- Différent du backtest : utilise le moteur LIVE en mode "fake clock"
- Pédagogique : permet de voir POURQUOI le bot ne tradait pas

#### 2.3 Heatmap performances
**Difficulté** : moyenne. **Temps estimé** : 1 jour.
- Visualiser les heures/jours qui marchent le mieux
- Utiliser `matplotlib` ou Qt natif
- Aider à identifier les biais temporels

### Priorité 3 — Extensibilité

#### 3.1 Système de plugins pour stratégies
**Difficulté** : moyenne-élevée. **Temps estimé** : 2-3 jours.
- Permettre à l'utilisateur d'ajouter sa stratégie en Python
- Sans toucher au cœur du code
- Hot reload si possible
- Sandbox pour limiter les imports dangereux

#### 3.2 Webhook TradingView
**Difficulté** : moyenne. **Temps estimé** : 1 jour.
- Recevoir des alertes TradingView Pro via HTTP
- Le bot peut soit alerter (Telegram), soit trader (selon config)
- Lib : `Flask` ou `aiohttp`

#### 3.3 Mode multi-comptes
**Difficulté** : élevée. **Temps estimé** : 3-5 jours.
- Plusieurs `TradingEngine` en parallèle
- Un par compte broker
- UI : dropdown pour switcher de vue

### Priorité 4 — Polish

#### 4.1 Theme clair finalisé
**Difficulté** : moyenne. **Temps estimé** : 4-6 heures.
- Refactor TOUTES les vues pour utiliser `objectName` au lieu de `setStyleSheet` inline
- Voir `ARCHITECTURE.md` section 4.4 pour le pattern

#### 4.2 Notifications desktop
**Difficulté** : facile. **Temps estimé** : 2 heures.
- Lib : `plyer` ou `notify-py`
- Sons optionnels au déclenchement de trades

---

## 🚫 À NE PAS implémenter (pièges classiques)

### "Optimisation des hyper-paramètres"
**Pourquoi non** : c'est de l'overfitting. On trouve toujours une combinaison qui
maximise le profit sur l'historique. Sur le futur, c'est aléatoire (souvent négatif).

### "Stop loss intelligent flottant qui ne se déclenche pas"
**Pourquoi non** : un SL doit toujours se déclencher. Un SL conditionnel qui peut être
"désactivé" par le bot = un compte qui peut être anéanti par un mouvement nocturne.

### "Martingale améliorée" / "Anti-martingale"
**Pourquoi non** : mathématiquement perdant à long terme avec frais réels.
Les chercheurs académiques l'ont prouvé depuis 50 ans.

### "Reconnaissance de patterns chartistes par IA"
**Pourquoi non** : sauf à avoir 10 ans de tick data + un labo Renaissance Tech,
les "double bottoms" et "triangles" identifiés par IA ne battent pas le random.

### "Auto-trading sur signaux Twitter/Reddit/Telegram"
**Pourquoi non** : sentiment social = manipulation. WallStreetBets a montré que
suivre la foule retail = perdre.

### "Optimisation par algo génétique sur 100 paramètres"
**Pourquoi non** : optimisation noire = overfitting noir. Plus il y a de paramètres,
plus le résultat est aléatoire en out-of-sample.

### "Trading haute fréquence"
**Pourquoi non** : chez un broker retail, les latences (50-200ms) tuent toute stratégie
HFT. Et les frais cumulés vous ruinent en quelques heures.

---

## 📋 Checklist pour ajouter une fonctionnalité

Avant d'implémenter quoi que ce soit, demandez-vous :

1. **Est-ce que ça aide l'utilisateur à perdre moins d'argent ?**
   (Ou : à comprendre pourquoi il en perd actuellement ?)

2. **Est-ce que ça respecte les règles légales ?**
   (CGU des brokers, lois locales sur le trading auto)

3. **Est-ce que c'est testable ?**
   (Si on ne peut pas vérifier qu'un changement améliore vraiment, c'est inutile)

4. **Est-ce que ça simplifie ou ça complexifie ?**
   (Plus de boutons = plus de chances que l'utilisateur fasse une erreur)

5. **Est-ce que c'est demandé par RAISON ou par PEUR ?**
   ("J'ai pas tradé depuis 3h, ajoute X" est de la peur, pas une raison)

Si la réponse à au moins 2 de ces questions est NON, ne l'implémentez pas.

---

## 🎯 Le but ultime (rappel)

> SafeTrendBot doit aider Hawar (et d'autres utilisateurs comme lui) à trader
> de manière **disciplinée**, en respectant un risque mesuré, sur des règles
> fixes et testables.
>
> Si on lui apporte ça, on a réussi. Le reste (gains, profits) c'est entre
> ses mains et celles du marché.

Bonne continuation pour la prochaine IA / le prochain dev.
