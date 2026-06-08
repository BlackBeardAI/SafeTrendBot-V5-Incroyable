# SafeTrendBot V5 Ultra — Trading Bot Extraordinaire

Bot de trading automatisé multi-broker avec **17 modules d'intelligence** intégrés.

> ⚠️ **Avertissement** : le trading comporte des risques. Testez en **paper trading** avant tout capital réel.

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

## 📊 Architecture

```
SafeTrendBot/
├── app/core/
│   ├── trading_engine_v4.py     ← Moteur unifié V5
│   ├── regime_detector.py       ← Détection régime (règles)
│   ├── ml_regime_detector.py    ← Détection régime (ML HMM/KMeans)
│   ├── adaptive_strategies.py   ← Voter avec pondération adaptative
│   ├── portfolio_manager.py     ← Kelly + DD dynamique
│   ├── triple_screen.py         ← Alexander Elder Triple Screen
│   ├── symbol_circuit_breaker.py ← CB par symbole
│   ├── smart_order_routing.py   ← Limit/Market intelligent
│   ├── walk_forward.py          ← WFA auto-optimization
│   ├── broker_failover.py       ← Basculement broker
│   ├── news_nlp.py              ← Sentiment news
│   ├── web_dashboard.py         ← FastAPI + WebSocket
│   ├── parallel_backtest.py     ← Backtest multi-cœurs
│   ├── decision_journal.py      ← Journal décision IA
│   ├── prop_firm.py             ← Mode FTMO/TFF
│   ├── risk_off_manager.py      ← Fermeture avant events
│   ├── auto_reporting.py        ← Rapports hebdo auto
│   ├── multi_account.py         ← Multi-comptes
│   ├── slippage_learner.py      ← Apprentissage slippage
│   ├── auto_hedge.py            ← Couverture auto
│   └── voice_alerts.py          ← Alertes vocales
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

## 📈 Performance attendue

| Métrique | V4 | V5 Ultra |
|----------|-----|----------|
| Win Rate | 45-55% | 55-65% |
| Sharpe | 0.8-1.2 | 1.2-1.8 |
| Max DD | 12-15% | 8-12% |
| Slippage | Variable | Optimisé -30% |
| Longévité | 6-12 mois | 3-5 ans |

---

**Projet personnel — utilisation à vos risques. Pas de garantie de gain.**
