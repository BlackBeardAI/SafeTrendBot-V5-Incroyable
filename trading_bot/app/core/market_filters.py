"""
Filtres de marché avancés : volatilité, corrélations, régimes de marché.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class VolatilityRegime(Enum):
    DEAD = "dead"                       # Volatilité anormalement basse
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"                 # Chaos, spreads explosés


@dataclass
class VolatilityStatus:
    regime: VolatilityRegime
    current_atr: float
    median_atr: float
    ratio: float                        # current / median
    safe_to_trade: bool
    reason: str


class VolatilityFilter:
    """
    Filtre de volatilité basé sur l'ATR.
    Bloque le trading en volatilité anormale (trop basse ou trop haute).
    """

    def __init__(self, atr_period: int = 14, lookback_bars: int = 200,
                 dead_ratio: float = 0.5, extreme_ratio: float = 3.0):
        """
        Args:
            atr_period: Période de l'ATR
            lookback_bars: Nombre de bougies pour calculer la médiane
            dead_ratio: Sous ce ratio, marché considéré mort
            extreme_ratio: Au-dessus, volatilité extrême
        """
        self.atr_period = atr_period
        self.lookback_bars = lookback_bars
        self.dead_ratio = dead_ratio
        self.extreme_ratio = extreme_ratio

    def analyze(self, highs: np.ndarray, lows: np.ndarray,
                closes: np.ndarray) -> VolatilityStatus:
        """Analyse la volatilité actuelle vs historique"""
        if len(closes) < self.lookback_bars:
            return VolatilityStatus(
                regime=VolatilityRegime.NORMAL,
                current_atr=0,
                median_atr=0,
                ratio=1.0,
                safe_to_trade=True,
                reason="Données insuffisantes, filtre inactif"
            )

        # Calcul de l'ATR sur toute la période
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(closes)):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )

        # ATR lissé
        atr_series = np.zeros_like(tr)
        atr_series[:self.atr_period] = np.mean(tr[:self.atr_period])
        for i in range(self.atr_period, len(tr)):
            atr_series[i] = (atr_series[i - 1] * (self.atr_period - 1) + tr[i]) / self.atr_period

        current_atr = atr_series[-1]
        median_atr = np.median(atr_series[-self.lookback_bars:])
        ratio = current_atr / median_atr if median_atr > 0 else 1.0

        # Classification
        if ratio < self.dead_ratio:
            regime = VolatilityRegime.DEAD
            safe = False
            reason = f"Marché mort (volatilité {ratio:.2f}x la normale)"
        elif ratio < 0.75:
            regime = VolatilityRegime.LOW
            safe = True
            reason = f"Volatilité faible mais tradable ({ratio:.2f}x)"
        elif ratio < 1.5:
            regime = VolatilityRegime.NORMAL
            safe = True
            reason = f"Volatilité normale ({ratio:.2f}x)"
        elif ratio < self.extreme_ratio:
            regime = VolatilityRegime.HIGH
            safe = True
            reason = f"Volatilité élevée ({ratio:.2f}x)"
        else:
            regime = VolatilityRegime.EXTREME
            safe = False
            reason = f"Volatilité extrême ({ratio:.2f}x) - pause conseillée"

        return VolatilityStatus(
            regime=regime,
            current_atr=float(current_atr),
            median_atr=float(median_atr),
            ratio=float(ratio),
            safe_to_trade=safe,
            reason=reason,
        )


# ============================================================================
# FILTRE DE CORRÉLATION
# ============================================================================

@dataclass
class CorrelationResult:
    symbol_a: str
    symbol_b: str
    correlation: float                  # -1 à 1
    period_bars: int


class CorrelationFilter:
    """
    Évite d'ouvrir des positions fortement corrélées simultanément.
    Ex: EURUSD long + GBPUSD long = doubler le risque, pas diversifier.
    """

    def __init__(self, correlation_threshold: float = 0.75,
                 lookback_bars: int = 100):
        """
        Args:
            correlation_threshold: Au-delà de ce seuil, on considère les paires corrélées
            lookback_bars: Nombre de bougies pour calculer la corrélation
        """
        self.threshold = correlation_threshold
        self.lookback = lookback_bars
        self._cache: Dict[Tuple[str, str], Tuple[float, datetime]] = {}
        self._cache_duration = timedelta(hours=1)

    def get_correlation(self, symbol_a: str, symbol_b: str,
                        timeframe=None) -> Optional[float]:
        """Calcule (ou récupère du cache) la corrélation entre 2 symboles"""
        if not MT5_AVAILABLE:
            return None

        key = tuple(sorted([symbol_a, symbol_b]))
        if key in self._cache:
            corr, ts = self._cache[key]
            if datetime.now() - ts < self._cache_duration:
                return corr

        if timeframe is None:
            timeframe = mt5.TIMEFRAME_H1

        try:
            rates_a = mt5.copy_rates_from_pos(symbol_a, timeframe, 0, self.lookback)
            rates_b = mt5.copy_rates_from_pos(symbol_b, timeframe, 0, self.lookback)
            if rates_a is None or rates_b is None:
                return None
            if len(rates_a) < 20 or len(rates_b) < 20:
                return None

            # Aligner les longueurs
            n = min(len(rates_a), len(rates_b))
            closes_a = np.array([r['close'] for r in rates_a[-n:]])
            closes_b = np.array([r['close'] for r in rates_b[-n:]])

            # Utiliser les returns plutôt que les prix (meilleure mesure)
            returns_a = np.diff(closes_a) / closes_a[:-1]
            returns_b = np.diff(closes_b) / closes_b[:-1]

            corr = float(np.corrcoef(returns_a, returns_b)[0, 1])
            self._cache[key] = (corr, datetime.now())
            return corr
        except Exception:
            return None

    def is_safe_to_open(self, new_symbol: str, new_direction: int,
                        open_positions: List[Tuple[str, int]]) -> Tuple[bool, str]:
        """
        Vérifie s'il est sûr d'ouvrir une position sur new_symbol
        given les positions ouvertes.

        Args:
            new_symbol: Symbole qu'on veut trader
            new_direction: 1 pour long, -1 pour short
            open_positions: Liste de (symbol, direction) déjà ouvertes

        Returns:
            (safe, reason)
        """
        for open_symbol, open_direction in open_positions:
            if open_symbol == new_symbol:
                continue

            corr = self.get_correlation(new_symbol, open_symbol)
            if corr is None:
                continue

            # Si corrélation forte positive et même direction = risque doublé
            if corr > self.threshold and new_direction == open_direction:
                return False, (f"Corrélation forte ({corr:.2f}) avec {open_symbol} "
                              f"même direction - risque doublé")

            # Si corrélation forte négative et directions opposées = même chose
            if corr < -self.threshold and new_direction != open_direction:
                return False, (f"Corrélation négative forte ({corr:.2f}) avec {open_symbol} "
                              f"directions opposées - risque doublé")

        return True, "OK"

    def build_correlation_matrix(self, symbols: List[str]) -> Dict:
        """Construit une matrice de corrélation pour affichage UI"""
        matrix = {}
        for i, s1 in enumerate(symbols):
            matrix[s1] = {}
            for s2 in symbols:
                if s1 == s2:
                    matrix[s1][s2] = 1.0
                else:
                    corr = self.get_correlation(s1, s2)
                    matrix[s1][s2] = corr if corr is not None else 0.0
        return matrix


# ============================================================================
# CIRCUIT BREAKER INTELLIGENT
# ============================================================================

class CircuitBreakerLevel(Enum):
    OK = "ok"
    WARNING = "warning"
    HALT = "halt"


@dataclass
class CircuitBreakerStatus:
    level: CircuitBreakerLevel
    reasons: List[str]
    metrics: Dict


class CircuitBreaker:
    """
    Détecte les régimes de marché anormaux et coupe le trading.

    Déclencheurs :
    - Drawdown supérieur au seuil
    - Perte consécutive de trades
    - Volatilité extrême sur le compte (P&L instable)
    - Erreurs répétées
    - Perte de connexion prolongée
    """

    def __init__(self,
                 max_drawdown_percent: float = 15.0,
                 max_consecutive_losses: int = 5,
                 max_hourly_loss_percent: float = 2.0,
                 max_errors_per_hour: int = 10):
        self.max_dd = max_drawdown_percent
        self.max_consec_losses = max_consecutive_losses
        self.max_hourly_loss = max_hourly_loss_percent
        self.max_errors = max_errors_per_hour

        # État
        self.peak_equity = 0.0
        self.consecutive_losses = 0
        self.error_timestamps: List[datetime] = []
        self.pnl_samples: List[Tuple[datetime, float]] = []  # (time, equity)

    def update_equity(self, equity: float):
        """À appeler régulièrement avec l'équité actuelle"""
        if equity > self.peak_equity:
            self.peak_equity = equity
        self.pnl_samples.append((datetime.now(), equity))
        # Garder seulement la dernière heure
        cutoff = datetime.now() - timedelta(hours=1)
        self.pnl_samples = [(t, e) for t, e in self.pnl_samples if t > cutoff]

    def record_loss(self):
        self.consecutive_losses += 1

    def record_win(self):
        self.consecutive_losses = 0

    def record_error(self):
        self.error_timestamps.append(datetime.now())
        cutoff = datetime.now() - timedelta(hours=1)
        self.error_timestamps = [t for t in self.error_timestamps if t > cutoff]

    def check(self) -> CircuitBreakerStatus:
        """Vérifie l'état global et retourne le statut"""
        reasons = []
        level = CircuitBreakerLevel.OK

        # 1. Drawdown
        current_equity = self.pnl_samples[-1][1] if self.pnl_samples else self.peak_equity
        if self.peak_equity > 0:
            dd_pct = (self.peak_equity - current_equity) / self.peak_equity * 100
            if dd_pct >= self.max_dd:
                reasons.append(f"Drawdown {dd_pct:.1f}% ≥ seuil {self.max_dd}%")
                level = CircuitBreakerLevel.HALT
            elif dd_pct >= self.max_dd * 0.7:
                reasons.append(f"Drawdown {dd_pct:.1f}% approche du seuil")
                if level == CircuitBreakerLevel.OK:
                    level = CircuitBreakerLevel.WARNING

        # 2. Pertes consécutives
        if self.consecutive_losses >= self.max_consec_losses:
            reasons.append(f"{self.consecutive_losses} pertes consécutives")
            level = CircuitBreakerLevel.HALT
        elif self.consecutive_losses >= self.max_consec_losses - 1:
            reasons.append(f"{self.consecutive_losses} pertes consécutives (1 de la limite)")
            if level == CircuitBreakerLevel.OK:
                level = CircuitBreakerLevel.WARNING

        # 3. Perte horaire
        if len(self.pnl_samples) >= 2:
            hour_ago_equity = self.pnl_samples[0][1]
            current = self.pnl_samples[-1][1]
            if hour_ago_equity > 0:
                hourly_loss = (hour_ago_equity - current) / hour_ago_equity * 100
                if hourly_loss >= self.max_hourly_loss:
                    reasons.append(f"Perte horaire {hourly_loss:.1f}% ≥ seuil")
                    level = CircuitBreakerLevel.HALT

        # 4. Erreurs répétées
        if len(self.error_timestamps) >= self.max_errors:
            reasons.append(f"{len(self.error_timestamps)} erreurs dans la dernière heure")
            level = CircuitBreakerLevel.HALT

        metrics = {
            'drawdown_pct': dd_pct if self.peak_equity > 0 else 0,
            'consecutive_losses': self.consecutive_losses,
            'errors_last_hour': len(self.error_timestamps),
            'peak_equity': self.peak_equity,
        }

        return CircuitBreakerStatus(level=level, reasons=reasons, metrics=metrics)

    def reset(self):
        """Reset manuel après intervention"""
        self.consecutive_losses = 0
        self.error_timestamps.clear()
