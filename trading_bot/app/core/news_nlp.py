"""
News NLP — analyse sentiment des actualités économiques en temps réel.
"""
import re
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from collections import deque
import requests


@dataclass
class SentimentResult:
    symbol: str
    sentiment: float  # -1.0 à 1.0
    confidence: float
    source: str
    headline: str
    impact: str  # 'low', 'medium', 'high'
    raw_data: Dict


class NewsNLPAnalyzer:
    """
    Analyse le sentiment des news économiques.
    Fallback : dictionnaire de mots si transformers non installé.
    """

    def __init__(self, use_transformers: bool = True):
        self.use_transformers = use_transformers
        self._sentiment_pipeline = None
        self._cache: deque = deque(maxlen=100)
        self._last_fetch = None

        # Dictionnaire fallback
        self._positive_words = {
            'surge', 'rally', 'gain', 'rise', 'bullish', 'strong', 'growth',
            'expansion', 'optimistic', 'upbeat', 'beat', 'outperform',
            'hausse', 'progression', 'croissance', 'optimisme', 'positif',
        }
        self._negative_words = {
            'crash', 'drop', 'fall', 'decline', 'bearish', 'weak', 'recession',
            'contraction', 'pessimistic', 'miss', 'underperform', 'plunge',
            'baisse', 'chute', 'récession', 'crise', 'négatif', 'inflation',
        }
        self._high_impact_events = {
            'nfp', 'nonfarm', 'cpi', 'inflation', 'fed', 'fomc', 'rate',
            'gdp', 'ecb', 'boe', 'boj', 'interest', 'taux', 'chômage',
        }

        if use_transformers:
            try:
                from transformers import pipeline
                self._sentiment_pipeline = pipeline("sentiment-analysis",
                                                       model="distilbert-base-uncased-finetuned-sst-2-english")
            except ImportError:
                self.use_transformers = False

    def fetch_news(self, symbol: str = "FOREX") -> List[Dict]:
        """Récupère les news depuis ForexFactory ou fallback"""
        try:
            # Simplifié : utiliser l'API existante du bot
            from bot.news_feed import NewsFeed
            feed = NewsFeed()
            return feed.get_latest(symbol, count=10)
        except Exception:
            return []

    def analyze_sentiment(self, text: str) -> tuple:
        """Retourne (sentiment, confidence)"""
        if self._sentiment_pipeline and self.use_transformers:
            try:
                result = self._sentiment_pipeline(text[:512])[0]
                score = result['score']
                label = result['label']
                sentiment = score if label == 'POSITIVE' else -score
                return sentiment, score
            except Exception:
                pass

        # Fallback dictionnaire
        text_lower = text.lower()
        pos_count = sum(1 for w in self._positive_words if w in text_lower)
        neg_count = sum(1 for w in self._negative_words if w in text_lower)
        total = pos_count + neg_count
        if total == 0:
            return 0.0, 0.3
        sentiment = (pos_count - neg_count) / total
        confidence = min(0.9, total / 5)
        return sentiment, confidence

    def analyze_symbol(self, symbol: str) -> Optional[SentimentResult]:
        """Analyse le sentiment global pour un symbole"""
        news = self.fetch_news(symbol)
        if not news:
            return None

        sentiments = []
        for item in news:
            text = item.get('title', '') + ' ' + item.get('summary', '')
            sent, conf = self.analyze_sentiment(text)
            sentiments.append((sent, conf, item))

        if not sentiments:
            return None

        # Pondérer par récence
        now = datetime.now()
        weighted_sum = 0.0
        weight_total = 0.0
        for sent, conf, item in sentiments:
            age_hours = (now - item.get('time', now)).total_seconds() / 3600
            weight = max(0.1, 1.0 - age_hours / 24)  # Décrémente sur 24h
            weighted_sum += sent * conf * weight
            weight_total += conf * weight

        avg_sentiment = weighted_sum / weight_total if weight_total > 0 else 0
        avg_confidence = min(0.95, sum(c for _, c, _ in sentiments) / len(sentiments))

        # Détecter l'impact
        all_text = ' '.join(n.get('title', '') for n in news).lower()
        impact = 'low'
        if any(e in all_text for e in self._high_impact_events):
            impact = 'high'
        elif len(news) > 5:
            impact = 'medium'

        best_headline = max(sentiments, key=lambda x: abs(x[0]))[2].get('title', '')

        return SentimentResult(
            symbol=symbol, sentiment=round(avg_sentiment, 2),
            confidence=round(avg_confidence, 2), source='NewsNLP',
            headline=best_headline, impact=impact,
            raw_data={'articles_count': len(news)},
        )

    def is_safe_to_trade(self, symbol: str, direction: int,
                         sentiment_threshold: float = 0.3) -> tuple:
        """
        Vérifie si le sentiment est aligné avec la direction du trade.
        Retourne (safe, reason).
        """
        result = self.analyze_symbol(symbol)
        if result is None:
            return True, "Pas de news disponible"

        if result.impact == 'high' and abs(result.sentiment) > 0.5:
            # News forte divergence avec notre direction
            if (direction > 0 and result.sentiment < -sentiment_threshold) or                (direction < 0 and result.sentiment > sentiment_threshold):
                return False, f"Sentiment négatif ({result.sentiment}) contre position {direction} — {result.headline[:50]}"

        if result.confidence > 0.7 and abs(result.sentiment) > 0.7:
            return True, f"Sentiment fort {'haussier' if result.sentiment > 0 else 'baissier'} confirmé"

        return True, f"Sentiment neutre ({result.sentiment})"
