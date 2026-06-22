# 🚀 SafeTrendBot V5 — Guide Client

> **Version 5.4.0** | Bot de trading automatisé multi-broker | Prix: 10000€
>
> Bienvenue dans SafeTrendBot V5, votre assistant de trading automatisé professionnel. Ce guide vous accompagne pas à pas, de l'installation jusqu'au trading en direct. Aucune compétence technique n'est requise — suivez simplement les étapes.

---

## 📋 Table des matières

1. [Installation](#1-installation-3-étapes)
2. [Premier lancement — Onboarding](#2-premier-lancement--onboarding)
3. [Configuration MetaTrader 5](#3-configuration-metatrader-5)
4. [Interface — Les 18 vues](#4-interface--les-18-vues)
5. [Raccourcis clavier](#5-raccourcis-clavier)
6. [Démarrer le trading](#6-démarrer-le-trading)
7. [Alertes Telegram](#7-alertes-telegram-optionnel)
8. [Sécurité et bon sens](#8-sécurité-et-bon-sens)
9. [Dépannage](#9-dépannage)
10. [Support](#10-support)
11. [Informations licence](#11-informations-licence)
12. [Paiement](#12-paiement)

---

## 1. Installation (3 étapes)

L'installation est conçue pour être la plus simple possible. Trois étapes suffisent.

### ✅ Étape 1 — Lancer l'installateur

1. Localisez le fichier `INSTALL_WINDOWS.bat` dans le dossier du bot.
2. **Clic droit** sur le fichier → **« Exécuter en tant qu'administrateur »**.

> ⚠️ **Important:** L'exécution en administrateur est nécessaire pour installer les dépendances Python et créer le raccourci sur le bureau.

### ✅ Étape 2 — Attendre l'installation des dépendances

- L'installateur télécharge et installe automatiquement:
  - Python (si non détecté)
  - PyQt6 (interface graphique)
  - MetaTrader5 (connexion broker)
  - Toutes les autres librairies requises
- **Ne fermez pas la fenêtre** pendant l'installation. Cela peut prendre 5 à 15 minutes selon votre connexion.

### ✅ Étape 3 — Lancer l'application

- Un raccourci **« SafeTrendBot V5 »** apparaît automatiquement sur votre bureau.
- **Double-cliquez** le raccourci pour démarrer le bot.

### 🔁 Alternative — Version .exe standalone

Si vous disposez de la version `.exe` (fournie après achat):

1. Double-cliquez sur `SafeTrendBot-V5.exe`.
2. Aucune installation de Python n'est nécessaire.
3. L'application se lance directement.

> 💡 **Astuce:** La version `.exe` est recommandée si vous n'êtes pas à l'aise avec Python. C'est la version la plus simple.

---

## 2. Premier lancement — Onboarding

Au premier lancement, un **assistant de configuration (wizard)** s'ouvre automatiquement. Il vous guide en 4 étapes.

### 🧙 Étape 1 — Choisir le broker

Sélectionnez votre broker parmi:

| Broker | Type | Recommandation |
|--------|------|----------------|
| **MetaTrader 5** | Forex, CFD | ✅ Recommandé pour débuter |
| **cTrader** | Forex, CFD | Alternative professionnelle |
| **Paper Trading** | Simulation | ✅ Idéal pour tester sans risque |

> 🟢 **Conseil:** Si vous débutez, choisissez **Paper Trading**. Vous pourrez basculer vers MT5 plus tard.

### 🧙 Étape 2 — Configurer le risque

- **Risque par trade:** 1% à 2% de votre capital (recommandé)
- **Positions simultanées maximum:** 3 (recommandé)
- **Stop-loss par défaut:** configurable

> 🔴 **Règle d'or:** Ne risquez jamais plus de 2% de votre capital sur un seul trade. La sécurité avant tout.

### 🧙 Étape 3 — Sélectionner les symboles

Choisissez les paires à surveiller. Recommandations pour débuter:

- **EURUSD** — la paire la plus liquide, idéale pour commencer
- **GBPUSD** — volatile, bonne pour le trend following
- **USDJPY** — comportement régulier, excellente pour les signaux

Vous pouvez ajouter d'autres symboles plus tard dans la vue **Watchlist**.

### 🧙 Étape 4 — Confirmer et démarrer

- Vérifiez le récapitulatif de votre configuration.
- Cliquez sur **« Confirmer et démarrer »**.
- L'interface principale s'ouvre. Vous êtes prêt !

---

## 3. Configuration MetaTrader 5

Si vous avez choisi MetaTrader 5 comme broker, voici la configuration détaillée.

### 📥 1. Télécharger MT5

- Rendez-vous sur **[metaquotes.net](https://www.metaquotes.net)** ou le site de votre broker.
- Téléchargez et installez **MetaTrader 5** (gratuit).

### 🏦 2. Ouvrir un compte

- **Compte démo (gratuit):** idéal pour tester sans risquer d'argent réel.
- **Compte réel:** nécessite un dépôt auprès d'un broker régulé.

### 📝 3. Noter vos identifiants

Notez précieusement les 3 informations suivantes:

- **Login** (numéro de compte)
- **Mot de passe**
- **Serveur** (ex: `ICMarkets-Demo`, `Pepperstone-Live01`)

> 🔐 **Sécurité:** Ces identifiants sont stockés localement sur votre PC uniquement. Ils ne sont jamais envoyés sur internet.

### 🔌 4. Connecter SafeTrendBot à MT5

1. Ouvrez SafeTrendBot V5.
2. Allez dans la vue **Broker** (menu latéral).
3. Sélectionnez l'onglet **MT5**.
4. Entrez votre **login**, **mot de passe** et **serveur**.
5. Cliquez sur **« Tester la connexion »**.

> ✅ Si le message **« Connexion réussie »** apparaît, vous êtes connecté. Sinon, vérifiez vos identifiants et que MT5 est bien ouvert.

---

## 4. Interface — Les 18 vues

SafeTrendBot V5 dispose d'une interface complète avec 18 vues spécialisées. Voici la description de chacune.

### 📊 Vues principales

| # | Vue | Description |
|---|-----|-------------|
| 1 | **Dashboard** | Vue d'ensemble: statut du bot, P&L du jour, positions ouvertes, signaux récents. C'est votre écran de contrôle. |
| 2 | **Positions** | Liste détaillée de toutes les positions ouvertes avec P&L en temps réel, stop-loss et take-profit. |
| 3 | **Backtest** | Testez vos stratégies sur des données historiques. Visualisez les performances avant de trader en réel. |
| 4 | **Paper Trading** | Mode simulation: tradez avec des données réelles mais de l'argent virtuel. Parfait pour s'entraîner. |
| 5 | **Analytics** | Métriques de performance: win rate, profit factor, drawdown, Sharpe ratio, etc. |

### 📅 Vues d'information

| # | Vue | Description |
|---|-----|-------------|
| 6 | **Calendar** | Calendrier économique: événements à impact (NFP, BCE, FED) avec importance et prévisions. |
| 7 | **News** | Actualités financières en temps réel, filtrées par symboles suivis. |
| 8 | **Broker** | Gestion des connexions brokers: MT5, cTrader, XTB, Binance. Configuration et test. |
| 9 | **Telegram** | Configuration des alertes Telegram (voir section 7). |
| 10 | **Market Hours** | Horaires d'ouverture des marchés (Forex, actions, crypto) avec indicateur de session active. |

### ⚙️ Vues de configuration

| # | Vue | Description |
|---|-----|-------------|
| 11 | **Profiles** | Créez et gérez plusieurs profils de trading (conservateur, agressif, scalping, etc.). |
| 12 | **Trend Analysis** | Analyse de tendance multi-timeframe: détecte la direction du marché sur différentes unités de temps. |
| 13 | **Watchlist** | Liste des symboles surveillés. Ajoutez ou retirez des paires en un clic. |
| 14 | **Recommendations** | Recommandations du bot: signaux d'achat/vente avec score de confiance et raisonnement. |
| 15 | **Strategy Params** | Paramètres de la stratégie: périodes d'indicateurs, seuils de signaux, filtres. |
| 16 | **Tools** | Outils utilitaires: calculateur de position, convertisseur de devises, etc. |
| 17 | **Logs** | Journaux d'événements du bot en temps réel. Utile pour le dépannage. |
| 18 | **Settings** | Paramètres généraux: langue, thème, notifications, licence, mises à jour. |

> 💡 **Astuce:** Le menu latéral gauche permet de naviguer entre les vues. Le Dashboard est toujours accessible en premier.

---

## 5. Raccourcis clavier

SafeTrendBot V5 propose des raccourcis clavier pour un contrôle rapide.

| Raccourci | Action |
|-----------|--------|
| **Ctrl+S** | ▶️ Démarrer le bot |
| **Ctrl+X** | ⏹️ Arrêter le bot |
| **Ctrl+P** | ⏸️ Pause / Reprendre |
| **Ctrl+B** | 🧪 Ouvrir le Backtest |
| **Ctrl+D** | 📊 Aller au Dashboard |
| **F1** | ❓ Aide contextuelle |

> ⌨️ **Pro tip:** Ctrl+S pour démarrer, Ctrl+X pour arrêter. C'est tout ce dont vous avez besoin au quotidien.

---

## 6. Démarrer le trading

### 🟢 Étapes pour trader

1. **Vérifiez votre connexion broker** dans la vue Broker.
2. **Choisissez le mode de trading:**
   - 📝 **Paper Trading (démo)** — RECOMMANDÉ pour commencer
   - 💰 **Live (réel)** — uniquement après validation en démo
3. **Démarrez le bot:**
   - Cliquez sur le bouton **« Démarrer le bot »** en haut à droite, OU
   - Utilisez le raccourci **Ctrl+S**
4. **Surveillez les positions** dans la vue **Positions**.
5. **Arrêtez le bot** avec **Ctrl+X** quand vous le souhaitez.

> 🟢 **Recommandation forte:** Commencez TOUJOURS en mode Paper Trading pendant au moins 1 semaine pour valider la configuration et comprendre le comportement du bot.

### 📈 Ce que fait le bot en autonomie

- Analyse les marchés en continu (24/5 sur le Forex)
- Détecte les signaux d'entrée selon la stratégie configurée
- Ouvre et ferme des positions automatiquement
- Applique le stop-loss et le take-profit configurés
- Envoie des alertes Telegram si configuré

---

## 7. Alertes Telegram (optionnel)

Recevez des notifications sur votre téléphone en temps réel.

### 📱 Configuration en 4 étapes

1. **Créer un bot Telegram:**
   - Ouvrez Telegram et cherchez **@BotFather**
   - Envoyez la commande `/newbot`
   - Donnez un nom et un username à votre bot
   - Récupérez le **token** (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

2. **Dans SafeTrendBot:**
   - Allez dans la vue **Telegram**
   - Entrez le **token** du bot
   - Cliquez sur **« Activer »**

3. **Démarrer la conversation:**
   - Ouvrez votre bot dans Telegram
   - Envoyez `/start` pour initialiser

4. **Choisir les alertes:**
   - ✅ **Signaux** — notification à chaque signal détecté
   - ✅ **Positions** — notification à chaque ouverture/fermeture de position
   - ✅ **P&L** — récapitulatif quotidien des gains/pertes

> 💡 **Astuce:** Les alertes Telegram sont particulièrement utiles pour surveiller le bot quand vous n'êtes pas devant votre PC.

---

## 8. Sécurité et bon sens

Le trading automatisé est puissant, mais nécessite de la prudence. Suivez ces règles.

> 🔴 **RÈGLES D'OR — À LIRE ABSOLUMENT**
>
> 1. **TOUJOURS tester en Paper Trading d'abord** — au moins 1 semaine avant de trader en réel.
> 2. **Ne pas risquer plus de 2% par trade** — c'est la règle de gestion du risque la plus importante.
> 3. **Surveiller les logs** en cas de comportement inattendu (vue Logs).
> 4. **Garder MT5 ouvert** en arrière-plan — le bot a besoin de MT5 pour fonctionner.
> 5. **Ne pas laisser le bot tourner sans surveillance** pendant de longues periods sans avoir testé.

### 🛡️ Bonnes pratiques

- **Diversifiez:** ne tradez pas une seule paire en réel.
- **Surveillez le drawdown:** si vous perdez 10% de votre capital, arrêtez et analysez.
- **Mettez à jour:** installez les mises à jour dès qu'elles sont disponibles.
- **Sauvegardez:** exportez régulièrement votre configuration (vue Settings → Export).

---

## 9. Dépannage

### Problèmes courants et solutions

> **❌ « MT5 non détecté »**
>
> ✅ Vérifiez que MetaTrader 5 est bien ouvert et que vous êtes connecté à votre compte. Le bot ne peut pas se connecter si MT5 est fermé.

---

> **❌ « Connexion refusée »**
>
> ✅ Vérifiez votre login, mot de passe et serveur dans la vue Broker → MT5. Assurez-vous d'avoir sélectionné le bon serveur (démo ou réel).

---

> **❌ « Pas de signaux générés »**
>
> ✅ Vérifiez que des symboles sont configurés dans la vue Watchlist. Vérifiez que les horaires de marché correspondent (vue Market Hours). Le Forex est fermé le week-end.

---

> **❌ « L'interface ne s'ouvre pas »**
>
> ✅ Ouvrez un terminal (Invite de commandes) et exécutez:
> ```
> pip install PyQt6
> ```
> Puis relancez l'application. Si le problème persiste, réinstallez avec `INSTALL_WINDOWS.bat`.

---

> **❌ « Où trouver les logs ? »**
>
> 📂 Les logs sont situés à:
> ```
> %USERPROFILE%/.safetrendbot/bot.log
> ```
> Soit généralement: `C:\Users\VotreNom\.safetrendbot\bot.log`
> Vous pouvez aussi consulter les logs en direct dans la vue **Logs** de l'interface.

---

> **❌ « Le bot s'arrête tout seul »**
>
> ✅ Vérifiez les logs pour identifier l'erreur. Causes fréquentes: MT5 fermé, connexion internet coupée, capital insuffisant pour ouvrir une position.

---

## 10. Support

### 📞 Canaux de support

| Canal | Utilisation |
|-------|-------------|
| **GitHub** | [github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable](https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable) — Documentation, issues, mises à jour |
| **Telegram (DM)** | Support direct pour les clients ayant acheté le bot |
| **Logs** | `%USERPROFILE%/.safetrendbot/bot.log` — à fournir en cas de bug |

> 📧 **Pour les clients premium:** le support par Telegram est prioritaire. Mentionnez votre clé de licence lors de la première prise de contact.

### 🐛 Signaler un bug

1. Récupérez le fichier de logs (`bot.log`).
2. Notez la version du bot (vue Settings → À propos).
3. Décrivez le problème et les étapes pour le reproduire.
4. Envoyez le tout via Telegram ou ouvrez une issue sur GitHub.

---

## 11. Informations licence

### 🔑 Votre clé de licence

- **Format:** `STB5-XXXX-XXXX-XXXX`
- **Fournie à l'achat** dans l'email de confirmation
- **Embedded dans le build** — aucune activation en ligne requise

### 📋 Conditions de licence

| Élément | Détail |
|---------|--------|
| **Nombre de PC** | 1 licence = 1 PC |
| **Verrouillage matériel** | ❌ Non (pas de HW-lock) |
| **Changement de PC** | ✅ Possible, contactez le support |
| **Mises à jour** | ✅ Gratuites à vie |
| **Support** | ✅ Inclus avec la licence |
| **Transfert** | ❌ Non transférable à un tiers |

> 💡 **Note:** La clé de licence est intégrée directement dans votre build `.exe`. Vous n'avez rien à activer. Le bot fonctionnera immédiatement après installation.

---

## 12. Paiement

### 💰 Tarification

| Élément | Détail |
|---------|--------|
| **Prix** | 10000€ |
| **Conversion** | Au cours du BTC au moment du paiement |
| **Modalité** | Paiement one-shot (pas d'abonnement) |
| **Livraison** | Réception du `.exe` + clé de licence après confirmation |

### 🪙 Adresses de paiement

**Bitcoin (BTC):**
```
bc1qxxzn05t7jvdmz47ncnxlglczhh9aet3gcpt5dx
```

**Ethereum (ETH) / USDT (ERC-20):**
```
0xd1c2ef7f724635fa0ed327f4d626620a2adffd82
```

> ⚠️ **ATTENTION — Vérifiez bien l'adresse avant d'envoyer:**
> - Copiez l'adresse complète, ne la recopiez pas manuellement.
> - Vérifiez les premiers et derniers caractères.
> - Envoyez uniquement sur le bon réseau (BTC → réseau Bitcoin, ETH/USDT → réseau Ethereum ERC-20).
> - Une transaction envoyée sur le mauvais réseau est **irréversible**.

### 📝 Procédure d'achat

1. **Contactez le vendeur** pour confirmer la disponibilité.
2. **Effectuez le paiement** à l'une des adresses ci-dessus.
3. **Envoyez la preuve de transaction** (hash TXID) au vendeur.
4. **Après confirmation** (1 à 3 blocs selon la blockchain):
   - Réception du fichier `SafeTrendBot-V5.exe`
   - Réception de votre clé de licence `STB5-XXXX-XXXX-XXXX`
   - Accès au support Telegram
5. **Installez et commencez à trader !**

> ✅ **Avantages du paiement one-shot:**
> - Aucun abonnement récurrent
> - Mises à jour gratuites à vie
> - Support inclus
> - Aucun coût caché

---

## 🏁 Conclusion

SafeTrendBot V5 est un outil professionnel de trading automatisé. En suivant ce guide, vous serez opérationnel en moins de 30 minutes.

**Rappelez-vous:**

> 🟢 Commencez en Paper Trading.
> 🟢 Risquez au maximum 2% par trade.
> 🟢 Surveillez les logs en cas de doute.
> 🟢 Le support est là pour vous aider.

**Bon trading, et que les tendances soient avec vous ! 📈**

---

*SafeTrendBot V5.4.0 — Guide Client | © 2026 BlackBeardAI | Tous droits réservés*