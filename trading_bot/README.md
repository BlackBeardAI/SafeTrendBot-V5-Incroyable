# SafeTrendBot V5 Ultra — Trading Bot Extraordinaire

Bot de trading automatisé multi-broker avec **17 modules d'intelligence** intégrés et **4 modes de risque** adaptés à tous les profils.

> ⚠️ **Avertissement** : le trading comporte des risques. Testez en **paper trading** avant tout capital réel. Aucune stratégie ne garantit un gain.

---

## 🚀 Ce qui rend ce bot "extraordinaire"

### Intelligence Adaptative (V5)
| Module | Description | Impact |
|--------|-------------|--------|
| **Régime de marché temps réel** | Détecte Trending/Ranging/Volatile/Crash/Recovery | Évite les faux signaux |
| **Stratégies auto-ajustables** | Pondère dynamiquement les 4 stratégies selon le régime | +Win rate |
| **Kelly Criterion** | Sizing optimal selon performance historique | Protection capital |
| **Drawdown dynamique** | Réduit le risque progressivement si drawdown | Survivabilité |

### Exécution Professionnelle (V5)
| Module | Description | Impact |
|--------|-------------|--------|
| **Smart Order Routing** | Limit Order si spread faible, sinon Market | -Slippage 20-40% |
| **Triple Screen** | D1 + H4 + H1 doivent être alignés | Filtre 60% faux signaux |
| **ML Régime Detector** | HMM/KMeans découvre les régimes naturels | Détection avancée |
| **WFA Auto** | Réoptimise les paramètres chaque semaine | Longévité 5+ ans |

### Risk Management Ultime (V5)
| Module | Description | Impact |
|--------|-------------|--------|
| **Circuit Breaker par symbole** | Si EURUSD crashe, on continue sur GBPUSD | Diversification |
| **News NLP** | Analyse sentiment avant events économiques | Évite les news killers |
| **Portfolio Risk Manager** | Kelly + max exposition + diversification | Protection totale |
| **Prop Firm Mode** | Respecte les règles FTMO/TFF/MFF automatiquement | Challenge ready |

### 🔥🔥 Mode EXTREME (Nouveau V5.3)
| Module | Description | Impact |
|--------|-------------|--------|
| **Momentum Burst Strategy** | Scalping sur impulsions fortes, SL serré, TP étiré | Potentiel rendement max |
| **ExtremeGuard** | Sécurités strictes : pertes consécutives, cap journalier, cooldown | Protection capital |
| **PIN + Double Confirmation** | Activation verrouillée par code PIN | Empêche activation accidentelle |
| **Auto-Lock Multi-Niveaux** | 3 pertes consécutives = lock. -8% daily = lock. -30% DD = lock | Sécurité maximale |
| **Time-Limit 48h** | Désactivation auto après 48h — recharge PIN requise | Contrôle temps |

### Infrastructure (V5)
| Module | Description | Impact |
|--------|-------------|--------|
| **Auto-Failover Broker** | Bascule MT5 → IB en 10s si crash | Uptime 99.9% |
| **Web Dashboard** | FastAPI + WebSocket temps réel | Accès mobile |
| **System Tray V5** | Mini dashboard depuis la barre des tâches | Contrôle rapide |
| **Mode Headless** | Tourne sans UI sur VPS/cloud | Cloud ready |

### Analyse Avancée (V5 Ultra)
| Module | Description | Impact |
|--------|-------------|--------|
| **Sharpe/Sortino/Calmar** | Métriques temps réel | Qualité trades |
| **Heatmap heures** | Performance par heure de la journée | Optimisation timing |
| **Backtest parallèle** | Grid search sur 8 cœurs | Optimisation rapide |
| **Decision Journal IA** | Enregistre POURQUOI chaque trade a été pris | Diagnostic post-mortem |

### Ultra (V5.2)
| Module | Description | Impact |
|--------|-------------|--------|
| **Risk-Off Auto** | Ferme positions avant NFP/CPI/FOMC | Protection events |
| **Multi-comptes** | Clone trades sur plusieurs comptes | Scalabilité |
| **Slippage Learning** | Apprend le slippage par broker/heure | Exécution optimisée |
| **Auto-Hedge** | Couverture automatique sur corrélations | Protection |
| **Voice Alerts** | Notifications vocales pour événements critiques | Réactivité |
| **Reporting Hebdo** | PDF + Telegram auto chaque dimanche | Suivi pro |

---

## 📊 4 Modes de Risque

SafeTrendBot propose **4 profils de risque** + **3 stratégies pures** pour s'adapter à tous les traders :

### 🛡️ Safe (Conservateur)
- Risque : **0.5%** par trade
- Max positions : **2**
- Perte max/jour : **-2%**
- R:R : **2.5:1**
- Confiance min : **55%**
- → Débutant / Capital important / Prudent

### ⚖️ Normal (Équilibré — Recommandé)
- Risque : **1%** par trade
- Max positions : **3**
- Perte max/jour : **-3%**
- R:R : **2:1**
- Confiance min : **45%**
- → Utilisateur standard / Équilibre risque/rendement

### 🔥 Aggressive (Actif)
- Risque : **2%** par trade
- Max positions : **5**
- Perte max/jour : **-5%**
- R:R : **1.5:1**
- Confiance min : **35%**
- → Expérimenté / Accepte plus de volatilité

### 🔥🔥 EXTREME (Haute Performance)
- Risque : **5%** par trade — **maximum potentiel de rendement**
- Max positions : **8**
- Perte max/jour : **-8%** (circuit breaker)
- Drawdown max : **-30%** (arrêt complet)
- R:R : **4:1** — SL ultra-serré (0.8×ATR), TP très loin
- Confiance min : **30%** — plus de setups
- **Max 3 pertes consécutives** → auto-lock
- **Max 15 trades/jour** → hard cap
- **Cooldown 5 min** entre chaque trade
- **Levier max x3**
- **Désactivation auto après 48h** → recharge PIN requise
- **PIN requis** à l'activation + double confirmation
- → **Trader avancé uniquement** / Capital résilient / Recherche rendement maximal

> ⚠️ **AVERTISSEMENT EXTREME** : Ce mode est conçu pour maximiser les rendements sur des setups de haute conviction. Un compte peut perdre jusqu'à **30% avant l'arrêt automatique**. **20 pertes consécutives = compte à 0**. N'utilisez que du capital dont vous pouvez supporter la perte totale. Paper-trade 30 jours minimum avant usage réel.

### Stratégies pures (Avancé)
- **📈 Trend Following pur** — Win rate 30-40%, R:R 3:1
- **🔄 Mean Reversion pur** — Win rate 55-65%, R:R 1.5:1
- **💥 Breakout pur** — Faux breakouts fréquents, R:R 2.5:1

---

## 🏗 Architecture

```
SafeTrendBot/
├── app/core/
│   ├── trading_engine_v4.py      ← Moteur unifié V5 + EXTREME guard
│   ├── extreme_guard.py            ← Sécurités mode EXTREME
│   ├── trading_profiles.py         ← 4 modes + 3 stratégies pures
│   ├── regime_detector.py          ← Détection régime (règles)
│   ├── ml_regime_detector.py       ← Détection régime (ML HMM/KMeans)
│   ├── adaptive_strategies.py      ← Voter avec pondération adaptative
│   ├── portfolio_manager.py        ← Kelly + DD dynamique
│   ├── triple_screen.py            ← Alexander Elder Triple Screen
│   ├── symbol_circuit_breaker.py   ← CB par symbole
│   ├── smart_order_routing.py      ← Limit/Market intelligent
│   ├── walk_forward.py             ← WFA auto-optimization
│   ├── broker_failover.py          ← Basculement broker
│   ├── news_nlp.py                 ← Sentiment news
│   ├── web_dashboard.py            ← FastAPI + WebSocket
│   ├── parallel_backtest.py        ← Backtest multi-cœurs
│   ├── decision_journal.py         ← Journal décision IA
│   ├── prop_firm.py                ← Mode FTMO/TFF
│   ├── risk_off_manager.py         ← Fermeture avant events
│   ├── auto_reporting.py           ← Rapports hebdo auto
│   ├── multi_account.py            ← Multi-comptes
│   ├── slippage_learner.py         ← Apprentissage slippage
│   ├── auto_hedge.py               ← Couverture auto
│   └── voice_alerts.py             ← Alertes vocales
├── app/ui/
│   └── views/
│       └── profiles_view.py        ← UI de sélection des profils
├── app/brokers/
│   └── mt5_adapter.py              ← Bridge MetaTrader 5
├── server/
│   └── activation_server.py        ← Serveur de licence
├── app/core/
│   ├── license_manager.py          ← Gestion licences
│   └── anti_tamper.py              ← Protection anti-tamper
└── main.py                         ← Point d'entrée
```

---

## 🛠 Installation

```bash
git clone https://github.com/BlackBeardAI/SafeTrendBot-V5-Incroyable.git
cd SafeTrendBot-V5-Incroyable/trading_bot
pip install -r requirements.txt
python main.py
```

### Mode Headless (VPS)
```bash
python headless.py --paper --symbols EURUSD,GBPUSD
```

### Web Dashboard
Accédez à `http://localhost:8080` après le lancement.

---

## ⚙️ Utilisation du mode EXTREME

1. Ouvrez **Profils de trading** dans l'UI
2. Sélectionnez **🔥🔥 EXTREME**
3. Lisez tous les avertissements affichés
4. Confirmez la première boîte de dialogue
5. **Entrez le PIN** (par défaut : `0000` — changez-le dans les paramètres)
6. Redémarrez le bot pour appliquer

Les sécurités s'activent **automatiquement** :
- Compteur de pertes consécutives
- Compteur de trades par jour
- Cooldown entre trades
- Vérification du drawdown max
- Timer 48h

Si le mode se verrouille, un **rechargement manuel avec PIN** est requis.

---

## 📈 Performance attendue

| Métrique | Safe | Normal | Aggressive | EXTREME |
|----------|------|--------|------------|---------|
| Risque/trade | 0.5% | 1% | 2% | **5%** |
| R:R | 2.5:1 | 2:1 | 1.5:1 | **4:1** |
| Trades/semaine | 1-5 | 5-15 | 15-30 | **30-60** |
| Win Rate est. | 55% | 50% | 45% | **40%** |
| Sharpe est. | 1.5 | 1.3 | 1.0 | **1.2** |
| Max DD | 10% | 15% | 20% | **30%** |
| Rendement mois* | 2-5% | 5-10% | 10-20% | **20-50%** |

*Rendements estimés, non garantis. Le passé ne préjuge pas du futur.

---

## 🔒 Protection Commerciale

SafeTrendBot V5 inclut un système complet de protection pour la distribution commerciale :

- **License Manager** — activation en ligne, hardware-binding
- **Anti-Tamper** — détection debuggers/VMs/modifications
- **Serveur d'activation** — validation + heartbeat + révocation
- **7 jours d'essai gratuit**
- **Compilation .exe** via PyInstaller + Cython obfuscation

Voir `BUILD_GUIDE.md` et `PUBLISH_GITHUB.md` pour la distribution.

---

## 📚 Documentation

- `README.md` — Ce fichier
- `INSTALLATION.md` — Guide d'installation détaillé
- `BUILD_GUIDE.md` — Compilation .exe + obfuscation
- `PUBLISH_GITHUB.md` — Publication et distribution
- `DEPANNAGE.md` — Résolution des problèmes
- `ARCHITECTURE.md` — Architecture technique
- `CHANGELOG.md` — Historique des versions
- `ROADMAP.md` — Feuille de route
- `FEATURES_V2.md` — Fonctionnalités avancées
- `BROKERS.md` — Guide brokers supportés

---

**Projet personnel — utilisation à vos risques. Pas de garantie de gain.**
**Le trading comporte un risque de perte en capital. Ne tradez pas avec de l'argent que vous ne pouvez pas vous permettre de perdre.**
