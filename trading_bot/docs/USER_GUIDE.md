# Guide Utilisateur SafeTrendBot V5

**Version 5.0 Ultra — Mode Opératoire Complet**

> ⚠️ **AVERTISSEMENT RISQUE** : Le trading comporte des risques de perte en capital. Ce bot est un outil d'aide à la décision, pas une garantie de gain. Vous pouvez perdre la totalité de votre capital. Ne tradez jamais avec de l'argent que vous ne pouvez pas perdre.

---

## Sommaire

1. [Installation](#1-installation)
2. [Premier lancement](#2-premier-lancement)
3. [Licence et activation](#3-licence-et-activation)
4. [Configuration du broker](#4-configuration-du-broker)
5. [Sélection des paires de trading](#5-sélection-des-paires)
6. [Choix du mode de risque](#6-mode-de-risque)
7. [Paper Trading (test)](#7-paper-trading)
8. [Lancement en live](#8-lancement-live)
9. [Dashboard et monitoring](#9-dashboard)
10. [Web Dashboard (accès mobile)](#10-web-dashboard)
11. [Alertes Telegram](#11-alertes-telegram)
12. [Mode Prop Firm](#12-mode-prop-firm)
13. [Journal et rapports](#13-journal)
14. [Dépannage](#14-dépannage)
15. [Sécurité et anti-tamper](#15-sécurité)
16. [Glossaire](#16-glossaire)

---

## 1. Installation

### Windows (méthode recommandée)

1. Téléchargez le fichier `SafeTrendBot_v5.zip`
2. Extrayez-le dans `C:\Trading\SafeTrendBot\`
3. Double-cliquez sur `install.ps1` (PowerShell) ou lancez `python install.py`
4. Suivez les instructions à l'écran

### Linux / macOS

```bash
# 1. Extraire
cd ~/Trading
unzip SafeTrendBot_v5.zip

# 2. Installer
make install
# ou
./install.sh
```

### Docker (VPS cloud)

```bash
docker build -t safetrendbot:v5 .
docker run -p 8080:8080 -v safetrendbot-data:/data safetrendbot:v5
```

---

## 2. Premier lancement

### Mode Interface (Desktop)
```bash
# Windows
python main.py

# Linux (avec virtual display si nécessaire)
python main.py
```

### Mode Headless (sans écran)
```bash
python headless.py --paper --symbols EURUSD,GBPUSD
```

### Démarrage automatique (Linux)
```bash
systemctl --user enable safetrendbot
systemctl --user start safetrendbot
```

---

## 3. Licence et activation

SafeTrendBot V5 nécessite une licence valide pour fonctionner.

### Essai gratuit (7 jours)
Au premier lancement, cliquez sur **"Essai gratuit 7 jours"** pour tester toutes les fonctionnalités sans engagement.

### Activer une licence
1. Lancez le bot
2. Une fenêtre "Licence requise" apparaît
3. Cliquez **"J'ai une clé"**
4. Entrez votre clé de licence (format : `STB-XXXXXXXXXXXXXXXX`)
5. Le bot vérifie automatiquement la validité

### Vérification
Votre licence est liée à votre machine (hardware fingerprint). Elle ne peut pas être partagée avec d'autres ordinateurs.

---

## 4. Configuration du broker

SafeTrendBot supporte 8 plateformes :

| Broker | Statut | Configuration requise |
|--------|--------|----------------------|
| MetaTrader 5 | ✅ Stable | MT5 ouvert, compte connecté |
| Interactive Brokers | 🟡 Expérimental | TWS/Gateway ouvert |
| XTB | 🟡 Expérimental | user_id + password |
| cTrader | ⚠️ Squelette | OAuth2 à finaliser |
| Binance | 🟡 Crypto | API key + secret |
| Bybit | 🟡 Crypto | API key + secret |
| Kraken | 🟡 Crypto | API key + secret |
| Coinbase | 🟡 Crypto | API key + secret |

### MT5 (méthode recommandée)
1. Ouvrez MetaTrader 5
2. Connectez-vous à votre compte (réel ou démo)
3. Dans SafeTrendBot → onglet **"Broker"**
4. Sélectionnez **"MT5"**
5. Activez **"Auto-détecter"** ou renseignez le chemin vers votre terminal MT5

### Configuration API Crypto
1. Créez une clé API sur votre exchange (spot trading, pas futures)
2. Autorisez seulement : lecture du solde, ouverture/fermeture de positions
3. **N'activez JAMAIS** le retrait (withdrawal) sur la clé API
4. Copiez la clé et le secret dans SafeTrendBot → onglet **"Broker"**
5. Activez **"Sandbox"** pour les premiers tests

---

## 5. Sélection des paires de trading

### Paires recommandées pour débutants
- **EURUSD** : liquidité maximale, spread faible
- **GBPUSD** : volatilité moyenne
- **USDJPY** : tendances durables
- **XAUUSD (or)** : refuge, tendances fortes

### Timeframe
- **H1** : minimum recommandé (moins de bruit que M15)
- **H4** : pour les swings plus longs
- **D1** : très fiable mais rarement des signaux

### Configuration
1. Onglet **"Tableau de bord"**
2. Section **"Symboles actifs"**
3. Cochez les paires souhaitées
4. Sélectionnez le timeframe (H1 recommandé)

**Règle d'or** : ne tradez jamais plus de 4 paires simultanément. Cela éparpille le capital et augmente le risque corrélation.

---

## 6. Choix du mode de risque

### Profils intégrés

| Profil | Risque/trade | Max positions | Convient pour |
|--------|-------------|---------------|---------------|
| **Safe** | 0.3-0.5% | 2 max | Capital < $5,000, débutants |
| **Normal** | 0.5-1.0% | 4 max | Capital $5,000-$20,000 |
| **Aggressive** | 1.0-2.0% | 6 max | Capital > $20,000, expérimentés |

### Activation
1. Onglet **"Profils trading"**
2. Sélectionnez votre profil
3. Le bot ajuste automatiquement le sizing, les stop-loss et les filtres

### Kelly Criterion (V5)
Le bot calcule automatiquement la taille optimale selon votre historique de trades. Si vous gagnez régulièrement, le sizing augmente légèrement. Si vous perdez, il diminue pour protéger le capital.

---

## 7. Paper Trading (OBLIGATOIRE avant live)

**Avant de trader avec du capital réel, vous DEVEZ passer 4 semaines minimum en Paper Trading.**

### Activation
1. Onglet **"Paper Trading"**
2. Activez le mode **"PAPER"**
3. Capital virtuel : $10,000 (modifiable)
4. Le bot utilise les **prix réels du marché** mais les ordres sont simulés

### Objectifs de validation
Après 100 trades minimum en paper :
- Win rate : > 45%
- Profit factor : > 1.2
- Sharpe : > 0.5
- Max drawdown : < 10%
- Capital final : > capital initial

**Si vous ne remplissez pas ces critères, ne passez PAS en live.**

---

## 8. Lancement en live

### Vérifications pré-lancement
- [ ] 4+ semaines de paper trading concluantes
- [ ] Broker connecté et solde visible
- [ ] Profil de risque sélectionné
- [ ] Au moins 1 paire activée
- [ ] Circuit breaker actif
- [ ] Telegram configuré (optionnel mais recommandé)

### Lancement
1. Vérifiez que le **PIN** est désactivé ou que vous le connaissez
2. Cliquez sur **"▶ Démarrer le bot"** dans la sidebar
3. Le bot affiche : "Connecté : [Broker] — [Solde]"
4. Le moteur analyse les marchés toutes les 5 secondes

### Ce qui se passe automatiquement
- Le bot analyse chaque paire activée
- Il détecte le régime de marché (trending, ranging, etc.)
- Il vérifie les filtres (volatilité, corrélation, news)
- Si conditions réunies, il ouvre une position avec stop-loss et take-profit
- Le trailing stop et break-even se gèrent automatiquement
- Le circuit breaker arrête tout si le drawdown dépasse 15%

### Arrêt
Cliquez sur **"■ Arrêter"** dans la sidebar. Les positions ouvertes **ne sont PAS fermées** automatiquement. Vous devez les fermer manuellement sur votre broker si vous le souhaitez.

---

## 9. Dashboard et monitoring

### Indicateurs en temps réel

| Indicateur | Signification | Seuil critique |
|------------|--------------|----------------|
| **État** | stopped / running / paused / halted | Halted = arrêt forcé |
| **P&L Jour** | Gains/pertes aujourd'hui | > -5% = danger |
| **Positions** | Nombre de trades ouverts | > 4 = risque élevé |
| **Régime** | Trending / Ranging / Volatile / Crash | Crash = pas de trade |
| **Sharpe** | Ratio rendement/risque | < 0 = stratégie KO |
| **Max DD** | Drawdown maximum atteint | > 10% = stop manuel |

### Log temps réel
Onglet **"Journaux"** : chaque décision du bot est loguée avec timestamp.

---

## 10. Web Dashboard (accès mobile)

Après le lancement du bot, accédez depuis n'importe quel appareil :
```
http://[IP_DE_VOTRE_PC]:8080
```

### Sur un VPS
Remplacez `IP_DE_VOTRE_PC` par l'adresse IP de votre serveur.

### Fonctionnalités
- État du bot en temps réel
- P&L, positions, Sharpe
- Logs streamés via WebSocket
- Pas besoin d'installer quoi que ce soit sur le téléphone

---

## 11. Alertes Telegram

### Configuration
1. Créez un bot via @BotFather sur Telegram
2. Récupérez le token et votre chat ID (@userinfobot)
3. Onglet **"Telegram"** dans SafeTrendBot
4. Renseignez token + chat ID
5. Activez les alertes souhaitées :
   - Ouverture/fermeture de positions
   - Drawdown critique
   - Circuit breaker activé
   - Rapport quotidien à [heure configurée]

---

## 12. Mode Prop Firm

Pour les challenges FTMO, The5ers, Funded Trader, etc.

### Activation
1. Onglet **"Profils trading"**
2. Sélectionnez **"Prop Firm Mode"**
3. Choisissez le prop firm : FTMO / The5ers / Funded Trader / Custom
4. Renseignez le capital initial du challenge ($10,000 / $50,000 / $100,000 / $200,000)

### Règles automatiques
Le bot applique automatiquement :
- Limite de perte journalière (ex: 5% pour FTMO)
- Limite de perte totale (ex: 10% pour FTMO)
- Pas de positions le weekend (si interdit)
- Fermeture automatique avant les news de haute importance

### Surveillance
Le dashboard affiche en temps réel :
- Jours de trading : X / minimum requis
- P&L : X% / objectif
- Drawdown : X% / maximum autorisé

---

## 13. Journal et rapports

### Journal des trades
Fichier : `data/journal.db`

Chaque trade est enregistré avec :
- Symbole, direction, volume, prix d'entrée/sortie
- Régime de marché au moment du trade
- Stratégies qui ont voté pour le trade
- Score de confiance
- Résultat (profit/perte)

### Rapports hebdomadaires (V5 Ultra)
Le bot génère automatiquement chaque dimanche :
- Nombre de trades, win rate, P&L net
- Meilleur/pire trade de la semaine
- Meilleur/pire symbole
- Sharpe, Profit Factor
- Répartition par régime de marché

Envoyé automatiquement sur Telegram si configuré.

### Export CSV
Onglet **"Outils"** → **"Export CSV"** pour la déclaration fiscale.

---

## 14. Dépannage

### "MetaTrader5 non détecté"
- Vérifiez que MT5 est ouvert et connecté
- Sur Linux : MT5 ne fonctionne que via Wine (expérimental)
- Solution : utiliser un VPS Windows pour MT5

### "Aucun signal depuis 2 heures"
- C'est **normal** avec les filtres stricts
- Le bot ne trade pas si :
  - Volatilité trop faible ou trop élevée
  - News économiques imminentes
  - Triple Screen non aligné
  - Corrélation forte avec une position ouverte
  - Circuit breaker en warning

### "Licence invalide"
- La licence est liée à votre machine
- Si vous changez de PC, contactez le support pour un transfert
- Maximum 3 transferts par licence

### "Web Dashboard inaccessible"
- Vérifiez que le port 8080 n'est pas bloqué par un firewall
- Sur un VPS, autorisez le port 8080 dans les règles de sécurité

---

## 15. Sécurité et anti-tamper

### Détections automatiques
Le bot vérifie à chaque lancement :
- Aucun debugger attaché (GDB, WinDbg, etc.)
- Pas d'exécution dans une VM/sandbox
- Fichiers sources non modifiés
- Nombre d'instances limité

### En cas de détection
Si une anomalie est détectée, le bot refuse de démarrer et affiche :
```
SafeTrendBot — Accès refusé:
  • Debugger détecté
  • VM/Sandbox détectée
```

### Protéger votre compte
- N'utilisez jamais la même clé API sur plusieurs bots
- Activez l'authentification 2FA sur votre broker
- Ne partagez jamais votre clé de licence
- Gardez une copie de vos logs et journaux de trades

---

## 16. Glossaire

| Terme | Définition |
|-------|-----------|
| **ATR** | Average True Range — mesure la volatilité |
| **Break-even** | Déplacer le stop-loss au prix d'entrée pour un trade sans risque |
| **Circuit Breaker** | Arrêt automatique du bot si pertes excessives |
| **Drawdown (DD)** | Baisse maximale du capital par rapport au pic |
| **Edge** | Avantage statistique sur le marché |
| **H1** | Timeframe 1 heure — une bougie = 1 heure de prix |
| **Kelly** | Formule mathématique pour calculer le sizing optimal |
| **Paper Trading** | Simulation avec prix réels mais argent virtuel |
| **Régime** | État du marché : trending, ranging, volatile, crash |
| **Sharpe** | Ratio mesurant le rendement ajusté du risque |
| **Slippage** | Différence entre le prix attendu et le prix exécuté |
| **Trailing Stop** | Stop-loss qui suit le prix à mesure que le trade gagne |
| **Triple Screen** | Confirmation sur 3 timeframes (D1 + H4 + H1) |
| **WFA** | Walk-Forward Analysis — réoptimisation automatique |

---

**Support :** contact@safetrendbot.com

**Documentation technique :** ARCHITECTURE.md

**Version :** 5.0 Ultra
