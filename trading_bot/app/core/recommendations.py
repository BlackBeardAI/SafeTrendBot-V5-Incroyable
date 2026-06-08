"""
Moteur de recommandations SafeTrendBot.

Génère des recommandations contextuelles basées sur :
- L'état du bot (connecté, actif, en erreur)
- Les performances récentes (gains, pertes, drawdown)
- Les conditions de marché (signaux, volatilité, heures)
- La configuration (risque, symboles, profil)
- Les patterns détectés dans le journal des trades
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import List, Optional


class RecommendationPriority(Enum):
    CRITICAL = "critical"   # Erreur bloquante
    HIGH     = "high"       # À traiter aujourd'hui
    MEDIUM   = "medium"     # À traiter cette semaine
    INFO     = "info"       # Information utile


class RecommendationCategory(Enum):
    CONNEXION  = "connexion"
    RISQUE     = "risque"
    PERFORMANCE = "performance"
    MARCHE     = "marche"
    CONFIG     = "config"
    EDUCATION  = "education"


@dataclass
class Recommendation:
    title: str
    detail: str
    priority: RecommendationPriority
    category: RecommendationCategory
    action: Optional[str] = None    # Texte du bouton d'action
    action_target: Optional[str] = None  # Onglet à ouvrir (ex: "broker")
    icon: str = "💡"
    created_at: datetime = field(default_factory=datetime.now)


class RecommendationEngine:
    """
    Analyse l'état complet du bot et génère des recommandations
    priorisées et actionnables.
    """

    def generate(self, engine, config) -> List[Recommendation]:
        recs = []

        recs += self._check_connexion(engine, config)
        recs += self._check_bot_state(engine, config)
        recs += self._check_performance(engine, config)
        recs += self._check_market(engine, config)
        recs += self._check_config(engine, config)
        recs += self._check_education(engine, config)

        # Trier par priorité
        order = [
            RecommendationPriority.CRITICAL,
            RecommendationPriority.HIGH,
            RecommendationPriority.MEDIUM,
            RecommendationPriority.INFO,
        ]
        recs.sort(key=lambda r: order.index(r.priority))
        return recs

    # ------------------------------------------------------------------ #
    # CONNEXION
    # ------------------------------------------------------------------ #

    def _check_connexion(self, engine, config) -> List[Recommendation]:
        recs = []

        broker_connected = (
            engine and hasattr(engine, 'broker') and
            engine.broker is not None and engine.broker.is_connected()
        )

        if not broker_connected:
            recs.append(Recommendation(
                title="MetaTrader 5 non connecté",
                detail=(
                    "Le bot ne peut pas récupérer les données de marché ni placer de trades.\n\n"
                    "Étapes :\n"
                    "1. Ouvrez MetaTrader 5 sur votre PC\n"
                    "2. Connectez-vous à votre compte (démo recommandé)\n"
                    "3. Allez dans Outils → Options → Expert Advisors\n"
                    "4. Cochez 'Autoriser le trading automatique'\n"
                    "5. Redémarrez le bot"
                ),
                priority=RecommendationPriority.CRITICAL,
                category=RecommendationCategory.CONNEXION,
                action="Ouvrir Broker",
                action_target="broker",
                icon="🔴",
            ))
        return recs

    # ------------------------------------------------------------------ #
    # ÉTAT DU BOT
    # ------------------------------------------------------------------ #

    def _check_bot_state(self, engine, config) -> List[Recommendation]:
        recs = []
        if engine is None:
            return recs

        from app.core.trading_engine_v3 import BotState

        if engine.state == BotState.STOPPED:
            recs.append(Recommendation(
                title="Le bot n'est pas démarré",
                detail=(
                    "Le bot est configuré mais inactif. Aucun signal n'est analysé, "
                    "aucun trade ne sera placé.\n\n"
                    "Conseil : commencez en mode Paper Trading pour observer "
                    "le comportement du bot sans risque réel."
                ),
                priority=RecommendationPriority.HIGH,
                category=RecommendationCategory.CONFIG,
                action="Démarrer le bot",
                action_target="start",
                icon="▶️",
            ))

        elif engine.state == BotState.ERROR:
            recs.append(Recommendation(
                title="Le bot est en erreur",
                detail=(
                    "Le moteur a rencontré une erreur et s'est arrêté.\n"
                    "Consultez l'onglet Journaux pour voir le détail de l'erreur."
                ),
                priority=RecommendationPriority.CRITICAL,
                category=RecommendationCategory.CONNEXION,
                action="Voir les journaux",
                action_target="logs",
                icon="❌",
            ))

        elif engine.state == BotState.HALTED:
            recs.append(Recommendation(
                title="Circuit breaker déclenché",
                detail=(
                    "Le bot s'est arrêté automatiquement pour protéger votre capital.\n"
                    "Causes possibles : drawdown excessif, trop de pertes consécutives.\n\n"
                    "Ne relancez pas précipitamment. Analysez d'abord ce qui s'est passé "
                    "dans l'onglet Analyses."
                ),
                priority=RecommendationPriority.CRITICAL,
                category=RecommendationCategory.RISQUE,
                action="Voir les analyses",
                action_target="analytics",
                icon="🚨",
            ))

        # Circuit breaker pas encore déclenché mais proche
        cb = getattr(engine, 'circuit_breaker', None)
        if cb and engine.state == BotState.RUNNING:
            if engine.circuit_breaker.consecutive_losses >= 3:
                n = engine.circuit_breaker.consecutive_losses
                recs.append(Recommendation(
                    title=f"{n} pertes consécutives",
                    detail=(
                        f"Le bot a enregistré {n} pertes d'affilée. "
                        f"Le circuit breaker se déclenche à {config.strategy.max_consecutive_losses}.\n\n"
                        "Considérez de mettre le bot en pause et d'analyser les conditions "
                        "de marché actuelles."
                    ),
                    priority=RecommendationPriority.HIGH,
                    category=RecommendationCategory.RISQUE,
                    action="Voir les analyses",
                    action_target="analytics",
                    icon="⚠️",
                ))

        return recs

    # ------------------------------------------------------------------ #
    # PERFORMANCE
    # ------------------------------------------------------------------ #

    def _check_performance(self, engine, config) -> List[Recommendation]:
        recs = []
        if engine is None:
            return recs

        # Mode paper : analyser les résultats
        if engine.mode == "paper":
            try:
                stats = engine.paper_engine.get_stats()
                total_trades = stats.get('total_trades', 0)
                win_rate = stats.get('win_rate', 0)
                ret_pct = stats.get('return_pct', 0)

                if total_trades == 0:
                    recs.append(Recommendation(
                        title="Aucun trade paper effectué",
                        detail=(
                            "Le bot tourne en mode Paper Trading mais n'a pas encore placé "
                            "de trade simulé.\n\n"
                            "Causes possibles :\n"
                            "• MT5 n'est pas connecté (pas de données)\n"
                            "• Les seuils de signal sont trop stricts\n"
                            "• Le marché est peu actif (week-end, nuit)\n\n"
                            "Vérifiez l'onglet Journaux pour voir ce qui se passe."
                        ),
                        priority=RecommendationPriority.MEDIUM,
                        category=RecommendationCategory.PERFORMANCE,
                        action="Voir les journaux",
                        action_target="logs",
                        icon="📊",
                    ))
                elif total_trades >= 10:
                    if win_rate < 40:
                        recs.append(Recommendation(
                            title=f"Win rate faible : {win_rate:.0f}%",
                            detail=(
                                f"Sur {total_trades} trades, seulement {win_rate:.0f}% sont gagnants.\n\n"
                                "Avec un ratio R:R de 2:1, un win rate de 40% suffit pour être "
                                "rentable. En dessous de 35%, les conditions de marché ne sont "
                                "peut-être pas favorables.\n\n"
                                "Suggestions :\n"
                                "• Analyser quels symboles perdent (onglet Analyses)\n"
                                "• Essayer un autre profil de trading\n"
                                "• Vérifier si c'est un problème de timing (heures)"
                            ),
                            priority=RecommendationPriority.MEDIUM,
                            category=RecommendationCategory.PERFORMANCE,
                            action="Voir les analyses",
                            action_target="analytics",
                            icon="📉",
                        ))
                    elif win_rate >= 60 and ret_pct > 0:
                        recs.append(Recommendation(
                            title=f"Bons résultats paper : {win_rate:.0f}% WR, {ret_pct:+.1f}%",
                            detail=(
                                f"Excellentes performances en simulation !\n"
                                f"Win rate : {win_rate:.0f}% — Rendement : {ret_pct:+.1f}%\n\n"
                                f"Si ces résultats sont stables depuis au moins 2 semaines, "
                                f"vous pouvez envisager de passer en mode Live avec un risque "
                                f"minimal (0.5% par trade maximum au début)."
                            ),
                            priority=RecommendationPriority.INFO,
                            category=RecommendationCategory.PERFORMANCE,
                            icon="✅",
                        ))

                if ret_pct < -10:
                    recs.append(Recommendation(
                        title=f"Drawdown paper important : {ret_pct:.1f}%",
                        detail=(
                            f"Le compte paper a perdu {abs(ret_pct):.1f}% depuis le début.\n\n"
                            "Ne passez PAS en mode Live dans ces conditions. "
                            "Analysez les trades perdants et ajustez le profil "
                            "(essayez le profil 🛡️ Safe)."
                        ),
                        priority=RecommendationPriority.HIGH,
                        category=RecommendationCategory.RISQUE,
                        action="Profils trading",
                        action_target="profiles",
                        icon="⚠️",
                    ))
            except Exception:
                pass

        return recs

    # ------------------------------------------------------------------ #
    # MARCHÉ
    # ------------------------------------------------------------------ #

    def _check_market(self, engine, config) -> List[Recommendation]:
        recs = []

        now = datetime.now()
        weekday = now.weekday()  # 0=lundi, 6=dimanche

        # Week-end
        if weekday >= 5:
            days_until_monday = 7 - weekday
            recs.append(Recommendation(
                title="Marché forex fermé (week-end)",
                detail=(
                    f"Le forex est fermé du vendredi 22h au dimanche 22h (heure de Paris).\n"
                    f"Réouverture : lundi matin.\n\n"
                    "Profitez du week-end pour :\n"
                    "• Analyser les trades de la semaine\n"
                    "• Vérifier la configuration\n"
                    "• Consulter l'analyse de tendance 5 ans (onglet Tendances)"
                ),
                priority=RecommendationPriority.INFO,
                category=RecommendationCategory.MARCHE,
                icon="📅",
            ))

        # Heures de forte liquidité
        hour = now.hour
        if 13 <= hour <= 17:
            recs.append(Recommendation(
                title="🔥 Chevauchement Londres / New York",
                detail=(
                    "Vous êtes en période de chevauchement des sessions Londres et New York "
                    "(13h-17h heure Paris).\n\n"
                    "C'est la période de plus forte liquidité et volatilité de la journée. "
                    "Les signaux sont plus fiables et les spreads plus faibles.\n\n"
                    "Idéal pour trader EURUSD, GBPUSD et USDJPY."
                ),
                priority=RecommendationPriority.INFO,
                category=RecommendationCategory.MARCHE,
                icon="💹",
            ))
        elif 9 <= hour <= 11:
            recs.append(Recommendation(
                title="Session London ouverte",
                detail=(
                    "La session de Londres est active (8h-17h heure locale).\n"
                    "Bonne période pour les paires EUR et GBP."
                ),
                priority=RecommendationPriority.INFO,
                category=RecommendationCategory.MARCHE,
                icon="🇬🇧",
            ))

        return recs

    # ------------------------------------------------------------------ #
    # CONFIGURATION
    # ------------------------------------------------------------------ #

    def _check_config(self, engine, config) -> List[Recommendation]:
        recs = []

        # Vérifier le profil
        active = config.strategy.active_profile
        if active == "aggressive":
            recs.append(Recommendation(
                title="Profil Aggressive activé",
                detail=(
                    "Vous êtes en mode Aggressive (2% de risque par trade).\n\n"
                    "Rappel : avec 10 pertes consécutives, vous perdez 20% du capital.\n"
                    "Assurez-vous d'avoir testé ce profil en Paper Trading pendant "
                    "au moins 2 semaines avant de l'utiliser en réel."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.RISQUE,
                icon="🔥",
            ))

        # Un seul symbole
        enabled = [s for s in config.symbols if s.enabled]
        if len(enabled) <= 1:
            recs.append(Recommendation(
                title="Un seul symbole actif",
                detail=(
                    f"Vous tradez uniquement {enabled[0].symbol if enabled else 'aucun symbole'}.\n\n"
                    "Avec 5 symboles (EURUSD, GBPUSD, USDJPY, XAUUSD, AUDUSD), "
                    "vous multipliez les opportunités de signal et diversifiez le risque.\n\n"
                    "Ajoutez des symboles dans Paramètres → Symboles."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.CONFIG,
                action="Paramètres",
                action_target="settings",
                icon="🎯",
            ))

        # Timeframe H4 (trop lent)
        if any(s.timeframe == "H4" for s in enabled):
            recs.append(Recommendation(
                title="Timeframe H4 détecté",
                detail=(
                    "Un ou plusieurs symboles utilisent le timeframe H4.\n\n"
                    "En H4, le bot analyse seulement 6 bougies par jour — "
                    "au maximum 1-3 signaux par semaine.\n\n"
                    "Passez en H1 pour 4× plus de signaux tout en restant rigoureux."
                ),
                priority=RecommendationPriority.MEDIUM,
                category=RecommendationCategory.CONFIG,
                action="Paramètres",
                action_target="settings",
                icon="⏱️",
            ))

        # Telegram non configuré
        if not config.telegram.enabled or not config.telegram.token:
            recs.append(Recommendation(
                title="Telegram non configuré",
                detail=(
                    "Sans Telegram, vous ne serez pas notifié des trades ouverts/fermés "
                    "ni des alertes importantes quand vous n'êtes pas devant l'écran.\n\n"
                    "Configuration en 3 étapes :\n"
                    "1. Créez un bot sur @BotFather (Telegram)\n"
                    "2. Copiez le token dans l'onglet Telegram\n"
                    "3. Récupérez votre Chat ID via @userinfobot"
                ),
                priority=RecommendationPriority.INFO,
                category=RecommendationCategory.CONFIG,
                action="Configurer Telegram",
                action_target="telegram",
                icon="📱",
            ))

        # PIN non configuré
        if not config.security.enabled:
            recs.append(Recommendation(
                title="Verrouillage PIN non activé",
                detail=(
                    "Sans PIN, n'importe qui ayant accès à votre PC peut démarrer "
                    "le bot ou modifier la configuration.\n\n"
                    "Activez le PIN dans Paramètres → Sécurité."
                ),
                priority=RecommendationPriority.INFO,
                category=RecommendationCategory.CONFIG,
                action="Paramètres",
                action_target="settings",
                icon="🔐",
            ))

        return recs

    # ------------------------------------------------------------------ #
    # ÉDUCATION
    # ------------------------------------------------------------------ #

    def _check_education(self, engine, config) -> List[Recommendation]:
        recs = []

        # Si le bot tourne en live sans paper trading préalable
        if engine and engine.mode == "live":
            try:
                stats = engine.paper_engine.get_stats()
                if stats.get('total_trades', 0) < 20:
                    recs.append(Recommendation(
                        title="Peu de trades paper avant le mode Live",
                        detail=(
                            "Vous tradez en mode Live avec peu d'historique paper.\n\n"
                            "Recommandation : effectuez au moins 20-30 trades paper "
                            "avec un win rate stable avant de risquer de l'argent réel.\n\n"
                            "Le paper trading révèle les problèmes de configuration "
                            "sans coût réel."
                        ),
                        priority=RecommendationPriority.HIGH,
                        category=RecommendationCategory.EDUCATION,
                        action="Paper Trading",
                        action_target="paper",
                        icon="🎓",
                    ))
            except Exception:
                pass

        # Rappel sur l'analyse de tendance
        recs.append(Recommendation(
            title="Analysez les tendances avant de trader",
            detail=(
                "L'onglet 'Tendances 5 ans' vous permet de comprendre si un symbole "
                "est en tendance haussière ou baissière sur le long terme.\n\n"
                "Trader dans le sens de la tendance long terme améliore statistiquement "
                "le win rate. Par exemple, si EURUSD est en tendance baissière depuis "
                "6 mois, évitez les positions BUY longues."
            ),
            priority=RecommendationPriority.INFO,
            category=RecommendationCategory.EDUCATION,
            action="Tendances 5 ans",
            action_target="trend",
            icon="📈",
        ))

        return recs
