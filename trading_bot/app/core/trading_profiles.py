"""
Profils de trading pré-configurés.

3 modes de risque :
- SAFE     : très conservateur, peu de trades, faible risque
- NORMAL   : équilibré (défaut)
- AGGRESSIVE : plus de trades, risque plus élevé

3 stratégies de base classiques (documentées dans la littérature financière) :
- TREND_FOLLOWING : suit les tendances établies
- MEAN_REVERSION  : achète bas, vend haut sur les rebonds
- BREAKOUT        : entre sur cassure de niveaux

⚠️ AVERTISSEMENT IMPORTANT :
Aucune de ces stratégies ne garantit un gain.
Les paramètres sont issus de la littérature publique (Murphy, Schwager).
Toute stratégie doit être backtestée puis paper-tradée pendant
plusieurs semaines avant utilisation en réel.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict


class TradingMode(Enum):
    SAFE = "safe"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"


class StrategyProfile(Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    BALANCED = "balanced"          # Mix des 3 (vote majoritaire)
    CUSTOM = "custom"


@dataclass
class TradingProfile:
    """Configuration complète d'un profil de trading"""
    name: str
    description: str
    mode: TradingMode
    strategy: StrategyProfile

    # Risque
    risk_per_trade_pct: float       # % du capital par trade
    max_concurrent_positions: int   # Nb max de positions ouvertes
    max_daily_loss_pct: float       # Stop loss journalier (% du compte)
    max_drawdown_pct: float         # Drawdown max avant arrêt

    # Stratégie
    min_strategies_agreement: int   # Nb min de stratégies qui doivent voter pareil
    min_confidence: float           # Confiance min (0-1)
    risk_reward_ratio: float        # Ratio TP/SL (ex: 2.0 = TP 2x plus loin que SL)
    atr_multiplier_sl: float        # SL = ATR × ce multiplicateur

    # Filtres
    use_volatility_filter: bool
    use_correlation_filter: bool
    use_news_filter: bool
    use_session_filter: bool

    # Trailing
    enable_trailing_stop: bool
    enable_breakeven: bool

    # Avertissements à afficher
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# 3 MODES DE RISQUE (Safe / Normal / Aggressive)
# ============================================================================

PROFILE_SAFE = TradingProfile(
    name="🛡️ Safe",
    description=(
        "Mode conservateur. Peu de trades mais haute qualité. "
        "Adapté pour débuter ou pour les comptes importants."
    ),
    mode=TradingMode.SAFE,
    strategy=StrategyProfile.BALANCED,
    risk_per_trade_pct=0.5,
    max_concurrent_positions=2,
    max_daily_loss_pct=2.0,
    max_drawdown_pct=10.0,
    min_strategies_agreement=2,   # 2/4 (au lieu de 3/4 qui bloquait trop)
    min_confidence=0.55,          # 55 % au lieu de 70 %
    risk_reward_ratio=2.5,
    atr_multiplier_sl=2.0,
    use_volatility_filter=False,  # Désactivé pour ne pas trop bloquer
    use_correlation_filter=False,
    use_news_filter=False,
    use_session_filter=False,
    enable_trailing_stop=True,
    enable_breakeven=True,
    warnings=[
        "Ce mode produit 1 à 5 trades par semaine selon les conditions.",
        "Il attend des signaux de qualité — patience requise.",
    ],
)

PROFILE_NORMAL = TradingProfile(
    name="⚖️ Normal",
    description=(
        "Mode équilibré recommandé. "
        "Bonne fréquence de trades avec gestion du risque standard."
    ),
    mode=TradingMode.NORMAL,
    strategy=StrategyProfile.BALANCED,
    risk_per_trade_pct=1.0,
    max_concurrent_positions=3,
    max_daily_loss_pct=3.0,
    max_drawdown_pct=15.0,
    min_strategies_agreement=1,   # 1/4 suffit avec confiance adéquate
    min_confidence=0.45,
    risk_reward_ratio=2.0,
    atr_multiplier_sl=1.5,
    use_volatility_filter=False,
    use_correlation_filter=False,
    use_news_filter=False,
    use_session_filter=False,
    enable_trailing_stop=True,
    enable_breakeven=True,
    warnings=[
        "Plusieurs trades par semaine attendus.",
    ],
)

PROFILE_AGGRESSIVE = TradingProfile(
    name="🔥 Aggressive",
    description=(
        "Mode actif avec risque plus élevé par trade. "
        "Réservé aux utilisateurs expérimentés."
    ),
    mode=TradingMode.AGGRESSIVE,
    strategy=StrategyProfile.BALANCED,
    risk_per_trade_pct=2.0,
    max_concurrent_positions=5,
    max_daily_loss_pct=5.0,
    max_drawdown_pct=20.0,
    min_strategies_agreement=1,
    min_confidence=0.35,
    risk_reward_ratio=1.5,
    atr_multiplier_sl=1.2,
    use_volatility_filter=False,
    use_correlation_filter=False,
    use_news_filter=False,
    use_session_filter=False,
    enable_trailing_stop=True,
    enable_breakeven=True,
    warnings=[
        "⚠️ Risque élevé : 2% par trade × 10 pertes = -20% du capital.",
        "⚠️ TOUJOURS tester en Paper Trading avant d'utiliser en réel.",
        "⚠️ NE PAS utiliser avec de l'argent dont vous avez besoin.",
    ],
)


# ============================================================================
# STRATÉGIES PURES (variantes du mode équilibré)
# ============================================================================

PROFILE_TREND_PURE = TradingProfile(
    name="📈 Trend Following pur",
    description=(
        "Stratégie basée uniquement sur le suivi de tendance. "
        "Achète sur les hausses, vend sur les baisses. Performant en trending market, "
        "perdant en marché latéral. Inspiré de la méthodologie de Richard Donchian / "
        "Tortues Traders, documentée dans 'Way of the Turtle' de Curtis Faith."
    ),
    mode=TradingMode.NORMAL,
    strategy=StrategyProfile.TREND_FOLLOWING,
    risk_per_trade_pct=1.0,
    max_concurrent_positions=3,
    max_daily_loss_pct=3.0,
    max_drawdown_pct=20.0,
    min_strategies_agreement=1,
    min_confidence=0.5,
    risk_reward_ratio=3.0,           # Trend follow = let winners run
    atr_multiplier_sl=2.0,
    use_volatility_filter=True,
    use_correlation_filter=True,
    use_news_filter=True,
    use_session_filter=True,
    enable_trailing_stop=True,
    enable_breakeven=True,
    warnings=[
        "Le trend following gagne peu de trades mais avec des gains importants.",
        "Attendez-vous à 30-40% de win rate mais R:R de 3:1.",
    ],
)

PROFILE_MEAN_REVERSION_PURE = TradingProfile(
    name="🔄 Mean Reversion pur",
    description=(
        "Stratégie basée sur le retour à la moyenne. "
        "Achète quand le prix s'éloigne fortement de sa moyenne mobile. "
        "Performant en marché latéral, perdant en marché trending fort. "
        "Inspiré des bandes de Bollinger (John Bollinger, 1980s) et RSI extrêmes (Wilder)."
    ),
    mode=TradingMode.NORMAL,
    strategy=StrategyProfile.MEAN_REVERSION,
    risk_per_trade_pct=0.75,
    max_concurrent_positions=4,
    max_daily_loss_pct=3.0,
    max_drawdown_pct=15.0,
    min_strategies_agreement=1,
    min_confidence=0.55,
    risk_reward_ratio=1.5,           # Mean reversion = small gains, high winrate
    atr_multiplier_sl=1.0,
    use_volatility_filter=True,
    use_correlation_filter=True,
    use_news_filter=True,
    use_session_filter=True,
    enable_trailing_stop=False,      # Targets fixes pour mean reversion
    enable_breakeven=True,
    warnings=[
        "Mean reversion perd beaucoup en marché trending fort.",
        "Win rate généralement 55-65% mais R:R 1.5:1.",
    ],
)

PROFILE_BREAKOUT_PURE = TradingProfile(
    name="💥 Breakout pur",
    description=(
        "Stratégie basée sur les cassures de niveaux clés. "
        "Entre dans le sens de la cassure. "
        "Inspiré de la méthodologie d'Edwards & Magee ('Technical Analysis of Stock Trends', 1948)."
    ),
    mode=TradingMode.NORMAL,
    strategy=StrategyProfile.BREAKOUT,
    risk_per_trade_pct=1.0,
    max_concurrent_positions=3,
    max_daily_loss_pct=3.0,
    max_drawdown_pct=18.0,
    min_strategies_agreement=1,
    min_confidence=0.6,
    risk_reward_ratio=2.5,
    atr_multiplier_sl=1.5,
    use_volatility_filter=True,
    use_correlation_filter=True,
    use_news_filter=True,
    use_session_filter=True,
    enable_trailing_stop=True,
    enable_breakeven=True,
    warnings=[
        "Beaucoup de fausses cassures (false breakouts).",
        "Le filtre de volume aide mais n'est pas miraculeux.",
    ],
)


# ============================================================================
# REGISTRE
# ============================================================================

ALL_PROFILES: Dict[str, TradingProfile] = {
    "safe": PROFILE_SAFE,
    "normal": PROFILE_NORMAL,
    "aggressive": PROFILE_AGGRESSIVE,
    "trend_pure": PROFILE_TREND_PURE,
    "mean_reversion_pure": PROFILE_MEAN_REVERSION_PURE,
    "breakout_pure": PROFILE_BREAKOUT_PURE,
}


def get_profile(profile_id: str) -> TradingProfile:
    """Récupère un profil par son ID. Retourne NORMAL par défaut."""
    return ALL_PROFILES.get(profile_id, PROFILE_NORMAL)


def list_profiles() -> List[TradingProfile]:
    """Liste tous les profils disponibles."""
    return list(ALL_PROFILES.values())
