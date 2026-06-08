"""
Slippage Learning — apprend le slippage par broker, symbole, et heure.
Ajuste le sizing et les attentes en conséquence.
"""
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque


@dataclass
class SlippageProfile:
    broker: str
    symbol: str
    hour: int
    avg_slippage_bps: float
    max_slippage_bps: float
    sample_count: int
    reliability_score: float  # 0-1


class SlippageLearner:
    """
    Apprend et prédit le slippage pour optimiser l'exécution.
    """

    def __init__(self, max_samples: int = 500):
        self.max_samples = max_samples
        self._data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        # clé: "broker|symbol|hour"

    def record(self, broker: str, symbol: str, requested_price: float,
               filled_price: float, direction: int, timestamp: Optional[datetime] = None):
        """Enregistre un nouveau point de données"""
        if requested_price <= 0 or filled_price <= 0:
            return
        ts = timestamp or datetime.now()
        hour = ts.hour

        slippage_bps = abs(filled_price - requested_price) / requested_price * 10000
        # Direction : si buy et fill > ask = mauvais slippage
        if direction == 1 and filled_price > requested_price:
            slippage_bps = -slippage_bps
        elif direction == -1 and filled_price < requested_price:
            slippage_bps = -slippage_bps

        key = f"{broker}|{symbol}|{hour}"
        self._data[key].append({
            'slippage_bps': slippage_bps,
            'time': ts,
        })

    def predict(self, broker: str, symbol: str, hour: Optional[int] = None) -> SlippageProfile:
        """Prédit le slippage attendu"""
        h = hour if hour is not None else datetime.now().hour
        key = f"{broker}|{symbol}|{h}"
        samples = list(self._data.get(key, []))

        if len(samples) < 3:
            # Fallback : tous les heures confondues
            all_hours = [v for k, v in self._data.items()
                         if k.startswith(f"{broker}|{symbol}|")]
            if all_hours:
                samples = [s for sublist in all_hours for s in sublist]

        if len(samples) < 3:
            return SlippageProfile(broker, symbol, h, 0, 0, 0, 0.0)

        values = [s['slippage_bps'] for s in samples]
        avg = np.mean(values)
        mx = max(values)
        reliability = min(1.0, len(samples) / 50)

        return SlippageProfile(
            broker=broker, symbol=symbol, hour=h,
            avg_slippage_bps=round(avg, 2),
            max_slippage_bps=round(mx, 2),
            sample_count=len(samples),
            reliability_score=round(reliability, 2),
        )

    def get_adjustment(self, broker: str, symbol: str) -> float:
        """
        Retourne un multiplicateur de taille selon le slippage attendu.
        Ex: slippage élevé = réduire la taille de 20%.
        """
        profile = self.predict(broker, symbol)
        if profile.reliability_score < 0.2:
            return 1.0  # Pas assez de données

        # Si slippage moyen > 5 bps (0.05%), réduire
        if profile.avg_slippage_bps > 5:
            return max(0.5, 1.0 - (profile.avg_slippage_bps - 5) / 20)
        return 1.0

    def get_recommendation(self, broker: str, symbol: str) -> str:
        profile = self.predict(broker, symbol)
        if profile.avg_slippage_bps > 10:
            return f"⚠️ Slippage élevé ({profile.avg_slippage_bps:.1f} bps) — réduire taille ou éviter heure {profile.hour}"
        elif profile.avg_slippage_bps > 5:
            return f"⚡ Slippage modéré ({profile.avg_slippage_bps:.1f} bps)"
        return f"✅ Slippage faible ({profile.avg_slippage_bps:.1f} bps)"
