"""
Machine Learning Regime Detector — Hidden Markov Model + KMeans.
Découvre automatiquement les régimes de marché sans règles prédefinies.
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from collections import deque

try:
    from sklearn.hmm import hmm  # sklearn ancien
    SKLEARN_AVAILABLE = True
except ImportError:
    try:
        from hmmlearn.hmm import GaussianHMM
        HMMLEARN_AVAILABLE = True
        SKLEARN_AVAILABLE = False
    except ImportError:
        HMMLEARN_AVAILABLE = False
        SKLEARN_AVAILABLE = False

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_KMEANS = True
except ImportError:
    SKLEARN_KMEANS = False

from app.core.regime_detector import MarketRegime


@dataclass
class MLRegimeResult:
    regime: MarketRegime
    confidence: float
    regime_id: int
    features: Dict[str, float]
    model_type: str  # 'hmm' ou 'kmeans'


class MLRegimeDetector:
    """
    Détecte le régime via ML : HMM ou KMeans clustering.
    Si sklearn/hmmlearn non installé, fallback sur règles classiques.
    """

    def __init__(self, n_regimes: int = 5, lookback: int = 100,
                 model_type: str = 'auto'):
        self.n_regimes = n_regimes
        self.lookback = lookback
        self.model_type = model_type
        self._history = deque(maxlen=200)
        self._model = None
        self._scaler = None
        self._last_training = None
        self._regime_labels = {}  # cluster_id -> MarketRegime mapping

    def _extract_features(self, closes, highs, lows, volumes=None) -> np.ndarray:
        """Extrait les features : returns, vol, skewness, momentum, range"""
        n = len(closes)
        if n < 30:
            return np.zeros(5)

        returns = np.diff(closes) / closes[:-1]
        vol_20 = np.std(returns[-20:]) if len(returns) >= 20 else np.std(returns)
        skew = np.mean(returns[-50:]**3) / (np.std(returns[-50:])**3 + 1e-10) if len(returns) >= 50 else 0
        mom_10 = (closes[-1] / closes[-10] - 1) * 100 if n >= 10 else 0
        mom_30 = (closes[-1] / closes[-30] - 1) * 100 if n >= 30 else 0
        atr = np.mean([max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
                       for i in range(max(1,n-14), n)])
        atr_ratio = atr / np.mean(closes[-20:]) * 100 if n >= 20 else 0

        return np.array([vol_20 * 100, skew, mom_10, mom_30, atr_ratio])

    def _train_model(self, features_history: List[np.ndarray]):
        """Entraîne HMM ou KMeans sur l'historique de features"""
        X = np.array(features_history)
        if len(X) < 50:
            return False

        if self.model_type == 'auto':
            if HMMLEARN_AVAILABLE:
                self.model_type = 'hmm'
            elif SKLEARN_KMEANS:
                self.model_type = 'kmeans'
            else:
                self.model_type = 'fallback'
                return False

        if self.model_type == 'hmm' and HMMLEARN_AVAILABLE:
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)
            self._model = GaussianHMM(n_components=self.n_regimes, covariance_type="full", n_iter=100)
            self._model.fit(X_scaled)
            # Détecter les régimes moyens
            means = self._model.means_
            self._regime_labels = self._label_regimes(means)

        elif self.model_type == 'kmeans' and SKLEARN_KMEANS:
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)
            self._model = KMeans(n_clusters=self.n_regimes, random_state=42, n_init=10)
            self._model.fit(X_scaled)
            centers = self._model.cluster_centers_
            self._regime_labels = self._label_regimes(centers)

        self._last_training = datetime.now()
        return True

    def _label_regimes(self, centers: np.ndarray) -> Dict[int, MarketRegime]:
        """Attribue un MarketRegime à chaque cluster selon ses caractéristiques"""
        labels = {}
        for i, c in enumerate(centers):
            vol, skew, mom10, mom30, atr = c
            if vol > 1.5:
                labels[i] = MarketRegime.VOLATILE
            elif mom30 < -3 and atr > 1:
                labels[i] = MarketRegime.CRASH
            elif mom30 > 2 and mom10 > 1:
                labels[i] = MarketRegime.TRENDING_UP
            elif mom30 < -2 and mom10 < -1:
                labels[i] = MarketRegime.TRENDING_DOWN
            elif abs(mom10) < 0.5 and vol < 0.5:
                labels[i] = MarketRegime.RANGING
            else:
                labels[i] = MarketRegime.UNKNOWN
        return labels

    def detect(self, closes, highs, lows, volumes=None) -> MLRegimeResult:
        features = self._extract_features(closes, highs, lows, volumes)
        self._history.append(features)

        # Réentraîner si nécessaire (toutes les 4h ou si pas de modèle)
        need_train = (self._model is None or
                      self._last_training is None or
                      (datetime.now() - self._last_training).seconds > 14400)
        if need_train and len(self._history) >= 100:
            self._train_model(list(self._history))

        if self._model is not None and self._scaler is not None:
            X = self._scaler.transform(features.reshape(1, -1))
            if self.model_type == 'hmm':
                regime_id = self._model.predict(X)[0]
                confidence = float(self._model.predict_proba(X).max())
            else:
                regime_id = self._model.predict(X)[0]
                # Distance au centre comme proxy de confiance
                center = self._model.cluster_centers_[regime_id]
                dist = np.linalg.norm(X - center)
                confidence = max(0.3, 1.0 - dist / 3.0)
            regime = self._regime_labels.get(regime_id, MarketRegime.UNKNOWN)
        else:
            # Fallback sur règles
            regime_id = -1
            regime = self._fallback_detect(features)
            confidence = 0.5

        return MLRegimeResult(
            regime=regime, confidence=round(confidence, 2),
            regime_id=int(regime_id),
            features={
                'volatility': round(features[0], 3),
                'skewness': round(features[1], 3),
                'momentum_10d': round(features[2], 2),
                'momentum_30d': round(features[3], 2),
                'atr_ratio': round(features[4], 3),
            },
            model_type=self.model_type if self._model else 'fallback',
        )

    def _fallback_detect(self, f: np.ndarray) -> MarketRegime:
        vol, skew, mom10, mom30, atr = f
        if mom30 < -3:
            return MarketRegime.CRASH
        elif mom30 > 2:
            return MarketRegime.TRENDING_UP
        elif mom30 < -2:
            return MarketRegime.TRENDING_DOWN
        elif abs(mom10) < 0.5 and vol < 0.5:
            return MarketRegime.RANGING
        elif vol > 1.0:
            return MarketRegime.VOLATILE
        return MarketRegime.UNKNOWN
