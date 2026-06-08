# Tunnel de Vente SafeTrendBot V5

**Processus commercial : Messagerie sécurisée → Paiement Crypto → Installation à distance**

---

## Vue d'ensemble du tunnel

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   LEAD      │ → │  DISCORD/   │ → │   PAIEMENT   │ → │   INSTALL    │
│  (client)   │    │   SIGNAL    │    │   CRYPTO     │    │   REMOTE     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                   │                   │                   │
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
Trouve le bot       Chat sécurisé       Reçoit la clé       TeamViewer/
sur les réseaux     avec le vendeur      de licence          AnyDesk
                                                              ↓
                                                         Bot configuré
                                                         + formation
```

---

## 1. Canal de messagerie sécurisée

### Options recommandées

| Plateforme | Sécurité | Avantage | Inconvénient |
|------------|----------|----------|--------------|
| **Signal** | E2E encryption | Anonymat max | Pas de canal public |
| **Telegram (Secret Chat)** | E2E encryption | Facile à utiliser | Numéro requis |
| **Session** | E2E + anonyme | Pas de numéro | Moins connu |
| **Discord DM** | Standard | Communauté trading | Pas E2E |
| **ProtonMail** | E2E email | Formalisé | Pas instantané |

### Recommandation
**Signal** pour les conversations commerciales + **Discord** pour la communauté publique.

### Setup du canal
1. Crée un compte Signal dédié (nouveau numéro)
2. Publie ton lien Signal sur : Twitter/X, Discord, forums trading, TikTok
3. Première réponse automatique : "Salut ! Merci pour l'intérêt. SafeTrendBot V5 — Essai 7 jours gratuit ou licence complète. Dis-moi ce que tu cherches."

---

## 2. Script de vente (conversation type)

### Phase 1 : Découverte (2-3 messages)
```
Client : "Salut, c'est quoi ce bot ?"
Toi    : "SafeTrendBot V5 — bot de trading multi-broker avec 
          intelligence adaptative (régime de marché, risk manager Kelly,
          triple screen, 17 modules). 7 jours d'essai gratuit ou 
          licence complète. Tu trades déjà ?"

Client : "Oui sur MT5 depuis 6 mois"
Toi    : "Parfait. Le bot se connecte direct à MT5. Tu peux tester
          en paper trading avant tout risque. Quel capital ?"

Client : "Environ 5000€"
Toi    : "Ok — avec 0.5% risque par trade et le mode Safe du bot,
          tu peux tester sans stress. L'essai te donne accès à TOUT.
          Tu veux l'essai ou direct la licence ?"
```

### Phase 2 : Proposition (1 message)
```
Toi : "Voici les options :

      🎮 ESSAI GRATUIT (7 jours)
         - Toutes les fonctionnalités
         - Support Telegram
         - Pas de carte requise

      💎 LICENCE COMPLÈTE — 0.05 BTC
         - À vie, toutes les mises à jour
         - Support prioritaire Signal
         - Installation à distance incluse
         - Configuration personnalisée

      🏆 PACK PROP FIRM — 0.08 BTC
         - Licence complète
         + Mode Prop Firm (FTMO/TFF/MFF)
         + 2 sessions coaching 1h
         + Paramètres optimisés pour challenge

      Paiement : BTC / ETH / USDT (TRC20)"
```

### Phase 3 : Paiement
```
Client : "Je prends la licence complète"
Toi    : "Parfait. Voici l'adresse USDT (TRC20) — frais minimes :
          
          TDvVnv... [ADRESSE WALLET]
          
          Montant : 0.05 BTC = [X] USDT
          
          Envoie le hash de transaction dès que c'est fait,
          je génère ta clé de licence immédiatement."
```

### Phase 4 : Activation
```
Toi : "✅ Paiement confirmé (3 confirmations)
      
      Ta clé de licence :
      STB-A7B3D9E4F5C2A8B1
      
      Elle est liée à TON PC uniquement (hardware fingerprint).
      
      Étape suivante : je prends la main à distance pour
      l'installation complète + configuration MT5.
      
      Télécharge AnyDesk : anydesk.com
      Envoie-moi ton ID et le mot de passe."
```

### Phase 5 : Installation à distance (30-45 min)
```
Toi : "[Connexion TeamViewer/AnyDesk]
      
      1. ✅ Vérification système (Python, dépendances)
      2. ✅ Installation du bot
      3. ✅ Configuration MT5 + connexion broker
      4. ✅ Sélection des paires (EURUSD, GBPUSD, USDJPY)
      5. ✅ Activation de la licence
      6. ✅ Test Paper Trading (5 min)
      7. ✅ Configuration Telegram alerts
      8. ✅ Explication du dashboard et logs
      9. ✅ Checklist de sécurité (risque, drawdown)
      
      Bot prêt ! Tu peux lancer dès maintenant."
```

### Phase 6 : Suivi (J+1, J+7, J+30)
```
J+1 : "Premier jour de trading ? Tout se passe bien ?
        Envoie-moi un screenshot du dashboard si tu veux
        que je vérifie la config."

J+7 : "Fin de la première semaine ! Résultats ?
        Si tu veux ajuster les paramètres, on fait un call 15 min."

J+30 : "Bilan du premier mois. Sharpe ? Win rate ?
         Si c'est positif, on peut parler scaling du capital."
```

---

## 3. Paiement en Crypto

### Adresses wallet (à personnaliser avec tes vraies adresses)

| Crypto | Réseau | Adresse type | Usage |
|--------|--------|-------------|-------|
| **Bitcoin** | On-chain | bc1q... | Paiements > 500€ |
| **Ethereum** | ERC-20 | 0x... | Paiements moyens |
| **USDT** | TRC-20 (Tron) | T... | RECOMMANDÉ — frais ~1$ |
| **USDT** | ERC-20 | 0x... | Si client préfère ETH |
| **USDC** | TRC-20 | T... | Alternative stable |

### Pourquoi USDT TRC-20 ?
- Frais : ~1 USDT par transaction (vs 20-50$ ETH)
- Confirmation : 1-3 minutes
- Disponible sur tous les exchanges

### Vérification du paiement
1. Client envoie le hash (TXID)
2. Vérifie sur : tronscan.org / blockchain.com / etherscan.io
3. Attendre 3 confirmations minimum
4. Confirmer le montant exact

---

## 4. Installation à distance — Procédure

### Prérequis chez le client
- Windows 10/11 ou Ubuntu 22.04+
- MetaTrader 5 installé et connecté (ou credentials broker)
- Connexion internet stable (10 Mbps minimum)
- TeamViewer ou AnyDesk installé

### Outils de prise de main

| Outil | Avantage | Inconvénient | Sécurité |
|-------|----------|--------------|----------|
| **AnyDesk** | Léger, pas d'install | Gratuit limité | ID + mot de passe |
| **TeamViewer** | Complet, fichier | Lourd, payant | 2FA disponible |
| **RustDesk** | Open source, gratuit | Moins connu | Self-hosted possible |
| **Chrome Remote** | Aucun install | Nécessite Chrome | Compte Google |

### Procédure type (AnyDesk)

```
1. Client ouvre AnyDesk
2. Client te donne : AnyDesk ID + mot de passe temporaire
3. Tu te connectes
4. Tu demandes : "Je vois ton écran, c'est bien ?"
5. Tu prends le contrôle (client clique "Accepter")
6. Tu installes le bot
7. Tu testes la connexion MT5
8. Tu configures
9. Tu déconnectes
10. Client vérifie que tout fonctionne seul
```

### Sécurité de la session
- Demande au client de **ne pas ouvrir son navigateur** (mots de passe)
- Ne stocke **jamais** les credentials broker (il les entre lui-même)
- Encourage le client à **changer le mot de passe AnyDesk** après la session
- Utilise un **mot de passe temporaire** (à usage unique)

---

## 5. Checklist post-installation

### À faire avant de déconnecter
- [ ] Le bot se lance sans erreur
- [ ] MT5 est connecté et affiche le solde
- [ ] La licence est activée et valide
- [ ] Paper Trading fonctionne (1 trade test)
- [ ] Telegram envoie un message de test
- [ ] Le client sait où trouver les logs
- [ ] Le client connaît le mot de passe PIN (si activé)
- [ ] Le client a le lien vers le guide utilisateur
- [ ] Le client a ton contact Signal pour support

### À expliquer au client
- [ ] "Ne touche pas aux paramètres pendant 2 semaines"
- [ ] "Si le bot est halted, ne le relance pas sans m'en parler"
- [ ] "Les pertes font partie du jeu — la clé est la taille des positions"
- [ ] "Garde toujours 20% du capital hors trading (cash de secours)"

---

## 6. Support post-vente

### Niveau 1 : Autonome (inclus licence)
- Guide utilisateur PDF
- FAQ Discord/Signal
- Logs auto-explicatifs

### Niveau 2 : Prioritaire (inclus licence)
- Réponse sous 24h sur Signal
- Ajustement de paramètres à distance (15 min)
- Mise à jour gratuite V5.X

### Niveau 3 : Coaching (pack Prop Firm)
- Call 1h / mois
- Analyse des résultats
- Optimisation des stratégies
- Préparation challenge Prop Firm

### Tarifs support (optionnel)
| Service | Prix |
|---------|------|
| Session dépannage 30 min | 0.01 BTC |
| Optimisation paramètres personnalisés | 0.02 BTC |
| Coaching mensuel 1h | 0.03 BTC |
| Pack "Mains dans le cambouis" (1 mois accompagnement) | 0.05 BTC |

---

## 7. Marketing — Où trouver des clients

### Canaux organiques (gratuit)
- **Twitter/X** : Threads sur le trading automatique, screenshots de résultats paper
- **Discord** : Rejoindre des serveurs trading francophones, aider, puis proposer
- **TikTok/YouTube Shorts** : "Mon bot a trade pendant que je dormais" (résultats paper)
- **Reddit** : r/Forex, r/algotrading — partager des insights, pas spammer

### Canaux payants (si scaling)
- **Google Ads** : mots-clés "bot trading forex", "ea mt5"
- **Influenceurs trading** : affiliation 20-30% par vente
- **Discord Boost** : serveur communautaire avec rôle "Vérifié"

### Contenu type
```
Tweet exemple :
"Jour 14 de paper trading avec SafeTrendBot V5 :
- 23 trades
- Win rate 52%
- Sharpe 1.1
- Max DD 3%
- P&L +4.2%

Prochaine étape : compte réel à 0.5% risque.
Si ça t'intéresse, DM."
```

---

## 8. Outils pour le vendeur

### Génération de clés (manuel ou auto)
```bash
# Manuel
python -c "
from app.core.license_manager import LicenseManager
lm = LicenseManager(secret_key='TON_SECRET')
key = lm.generate_license('client@email.com', 'lifetime')
print(key)
"

# Auto via serveur
POST /admin/generate {email, type}
```

### Tracking des ventes
Spreadsheet simple :
| Date | Client | Pack | Crypto | Montant | TXID | Clé | Installé ? | Suivi |
|------|--------|------|--------|---------|------|-----|-----------|-------|

### Templates de messages
Crée des quick-replies dans Signal/Telegram :
- `/prix` → envoie le tableau des packs
- `/essai` → instructions essai 7 jours
- `/install` → lien AnyDesk + procédure
- `/support` → heures de disponibilité

---

**SafeTrendBot V5 — Commercial Document**
**Version :** 1.0
**Dernière mise à jour :** Juin 2026
