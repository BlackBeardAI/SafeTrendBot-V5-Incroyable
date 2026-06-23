"""
Agrégateur de flux RSS d'actualités financières.
Sources légitimes et gratuites (RSS publics) - pour LECTURE HUMAINE uniquement.
Ces news ne déclenchent AUCUN trade automatique.

Usage :
    from news_feed import NewsFeed
    feed = NewsFeed()
    articles = feed.fetch_all()
"""

import logging
import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional
import re

logger = logging.getLogger("NewsFeed")


@dataclass
class NewsArticle:
    source: str
    title: str
    link: str
    summary: str
    published: datetime
    category: str = "general"

    def to_dict(self) -> dict:
        d = asdict(self)
        d['published'] = self.published.isoformat()
        return d


class NewsFeed:
    """Agrégateur de flux RSS de sources financières reconnues"""

    # Sources RSS publiques et légitimes (CGU respectées)
    SOURCES = {
        'Reuters Business': {
            'url': 'https://feeds.reuters.com/reuters/businessNews',
            'category': 'business',
        },
        'Reuters World': {
            'url': 'https://feeds.reuters.com/Reuters/worldNews',
            'category': 'world',
        },
        'Financial Times': {
            'url': 'https://www.ft.com/rss/home',
            'category': 'markets',
        },
        'CNBC Markets': {
            'url': 'https://www.cnbc.com/id/10000664/device/rss/rss.html',
            'category': 'markets',
        },
        'Investing.com Forex': {
            'url': 'https://www.investing.com/rss/news_1.rss',
            'category': 'forex',
        },
        'MarketWatch Top': {
            'url': 'http://feeds.marketwatch.com/marketwatch/topstories/',
            'category': 'markets',
        },
        'Yahoo Finance': {
            'url': 'https://finance.yahoo.com/news/rssindex',
            'category': 'markets',
        },
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (NewsFeedAggregator/1.0)'
        }

    def fetch_source(self, name: str) -> List[NewsArticle]:
        """Récupère les articles d'une source"""
        if name not in self.SOURCES:
            return []

        source_info = self.SOURCES[name]
        try:
            response = requests.get(
                source_info['url'],
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return self._parse_rss(
                response.content,
                source_name=name,
                category=source_info['category']
            )
        except requests.RequestException as e:
            logger.warning(f"Erreur {name} : {e}")
            return []

    def fetch_all(self, max_per_source: int = 10) -> List[NewsArticle]:
        """Récupère tous les articles de toutes les sources"""
        all_articles = []
        for name in self.SOURCES:
            articles = self.fetch_source(name)
            all_articles.extend(articles[:max_per_source])

        # Trier par date décroissante
        all_articles.sort(key=lambda a: a.published, reverse=True)
        return all_articles

    def _parse_rss(self, content: bytes, source_name: str, category: str) -> List[NewsArticle]:
        """Parse un flux RSS 2.0 standard"""
        articles = []
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return articles

        # RSS 2.0 : <channel><item>
        for item in root.findall('.//item'):
            try:
                title = self._get_text(item, 'title')
                link = self._get_text(item, 'link')
                description = self._get_text(item, 'description')
                pub_date_str = self._get_text(item, 'pubDate')

                # Parser la date
                published = self._parse_date(pub_date_str)

                # Nettoyer le HTML du summary
                summary = self._clean_html(description)[:300]

                if title and link:
                    articles.append(NewsArticle(
                        source=source_name,
                        title=title,
                        link=link,
                        summary=summary,
                        published=published,
                        category=category,
                    ))
            except (AttributeError, ValueError):
                continue

        return articles

    @staticmethod
    def _get_text(element, tag: str) -> str:
        child = element.find(tag)
        return (child.text or '').strip() if child is not None else ''

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse une date RSS (RFC 822)"""
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            return parsedate_to_datetime(date_str)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)

    @staticmethod
    def _clean_html(text: str) -> str:
        """Supprime les tags HTML d'un texte"""
        if not text:
            return ''
        # Décoder les entités HTML courantes
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
        # Supprimer les tags
        text = re.sub(r'<[^>]+>', '', text)
        # Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def filter_by_keywords(self, articles: List[NewsArticle],
                          keywords: List[str]) -> List[NewsArticle]:
        """Filtre les articles contenant certains mots-clés"""
        if not keywords:
            return articles
        keywords_lower = [k.lower() for k in keywords]
        return [
            a for a in articles
            if any(k in a.title.lower() or k in a.summary.lower() for k in keywords_lower)
        ]


if __name__ == '__main__':
    feed = NewsFeed()
    print("=" * 70)
    print("AGRÉGATEUR D'ACTUALITÉS FINANCIÈRES")
    print("=" * 70)
    print("\n⚠️  Rappel : ces news sont pour LECTURE HUMAINE.")
    print("    Aucun trade n'est déclenché automatiquement.\n")

    articles = feed.fetch_all(max_per_source=5)
    print(f"Total : {len(articles)} articles récupérés\n")

    for article in articles[:20]:
        print(f"📰 [{article.source}] {article.published.strftime('%Y-%m-%d %H:%M')}")
        print(f"   {article.title}")
        print(f"   {article.link}\n")
