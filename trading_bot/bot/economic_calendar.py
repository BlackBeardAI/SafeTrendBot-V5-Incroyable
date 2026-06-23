"""
Calendrier économique - Filtre de news à haute volatilité
Utilisé par le bot pour s'abstenir de trader autour des annonces majeures.

Source : ForexFactory (RSS public, gratuit, fiable depuis 20 ans)
Documentation : https://www.forexfactory.com/calendar

Usage standalone :
    python economic_calendar.py
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from typing import List, Optional
import json
import os
import re
import logging

logger = logging.getLogger("EconomicCalendar")


@dataclass
class EconomicEvent:
    title: str
    country: str
    impact: str          # "High", "Medium", "Low"
    time: datetime
    forecast: Optional[str] = None
    previous: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d['time'] = self.time.isoformat()
        return d


class EconomicCalendar:
    """Récupère et filtre les événements économiques majeurs"""

    # Sources RSS publiques et gratuites
    FOREXFACTORY_RSS = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    
    # Devises principales à surveiller selon les paires tradées
    MAJOR_CURRENCIES = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD'}

    # Fenêtre de sécurité autour des news (en minutes)
    SAFETY_WINDOW_MINUTES = 30

    def __init__(self, cache_path: str = '/tmp/economic_calendar_cache.json',
                 cache_duration_minutes: int = 60):
        self.cache_path = cache_path
        self.cache_duration = timedelta(minutes=cache_duration_minutes)

    def fetch_events(self, force_refresh: bool = False) -> List[EconomicEvent]:
        """Récupère les événements depuis le cache ou la source"""
        if not force_refresh and self._is_cache_valid():
            return self._load_cache()

        try:
            events = self._fetch_from_source()
            self._save_cache(events)
            return events
        except requests.RequestException as e:
            logger.warning(f"Erreur récupération calendrier : {e}")
            # Fallback sur le cache même expiré
            if os.path.exists(self.cache_path):
                return self._load_cache()
            return []

    def _fetch_from_source(self) -> List[EconomicEvent]:
        """Télécharge et parse le flux RSS ForexFactory"""
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; EconomicCalendarBot/1.0)'}
        response = requests.get(self.FOREXFACTORY_RSS, headers=headers, timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        events = []

        # Format ForexFactory : <event> dans <weeklyevents>
        for event_node in root.findall('.//event'):
            try:
                title = event_node.findtext('title', '').strip()
                country = event_node.findtext('country', '').strip()
                impact = event_node.findtext('impact', 'Low').strip()
                date_str = event_node.findtext('date', '').strip()
                time_str = event_node.findtext('time', '').strip()
                forecast = event_node.findtext('forecast', '').strip() or None
                previous = event_node.findtext('previous', '').strip() or None

                # Parser la date/heure
                dt = self._parse_datetime(date_str, time_str)
                if dt is None:
                    continue

                events.append(EconomicEvent(
                    title=title,
                    country=country,
                    impact=impact,
                    time=dt,
                    forecast=forecast,
                    previous=previous,
                ))
            except (AttributeError, ValueError) as e:
                continue

        return events

    def _parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse les formats de date ForexFactory (ex: '11-25-2024' + '8:30am')"""
        if not date_str:
            return None

        try:
            # Format date : MM-DD-YYYY
            date_part = datetime.strptime(date_str, '%m-%d-%Y')

            # Pas d'heure = all-day event, on met à minuit
            if not time_str or time_str.lower() in ('all day', 'tentative'):
                return date_part.replace(tzinfo=timezone.utc)

            # Format heure : 8:30am ou 14:30
            time_str = time_str.lower().replace(' ', '')
            if 'am' in time_str or 'pm' in time_str:
                time_part = datetime.strptime(time_str, '%I:%M%p').time()
            else:
                time_part = datetime.strptime(time_str, '%H:%M').time()

            return datetime.combine(date_part.date(), time_part, tzinfo=timezone.utc)
        except ValueError:
            return None

    def is_safe_to_trade(self, symbol: str = 'EURUSD',
                         now: Optional[datetime] = None) -> tuple[bool, Optional[EconomicEvent]]:
        """
        Vérifie s'il est sûr de trader.
        Retourne (True, None) si safe, (False, event) sinon.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Devises concernées par le symbole
        currencies = self._extract_currencies(symbol)

        # Récupérer les événements à haut impact
        events = self.fetch_events()
        high_impact = [e for e in events if e.impact == 'High' and e.country in currencies]

        window = timedelta(minutes=self.SAFETY_WINDOW_MINUTES)
        for event in high_impact:
            if abs((event.time - now).total_seconds()) < window.total_seconds():
                return False, event

        return True, None

    def _extract_currencies(self, symbol: str) -> set:
        """Extrait les devises d'un symbole (ex: EURUSD -> {EUR, USD})"""
        symbol = symbol.upper().replace('=X', '').replace('/', '')
        currencies = set()
        # Recherche de devises 3 lettres dans le symbole
        for i in range(len(symbol) - 2):
            candidate = symbol[i:i+3]
            if candidate in self.MAJOR_CURRENCIES:
                currencies.add(candidate)
        return currencies or self.MAJOR_CURRENCIES

    def get_upcoming_high_impact(self, hours_ahead: int = 24) -> List[EconomicEvent]:
        """Retourne les événements high-impact des prochaines heures"""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours_ahead)
        events = self.fetch_events()
        return sorted([
            e for e in events
            if e.impact == 'High' and now <= e.time <= cutoff
        ], key=lambda e: e.time)

    # ----- Cache -----

    def _is_cache_valid(self) -> bool:
        if not os.path.exists(self.cache_path):
            return False
        age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self.cache_path))
        return age < self.cache_duration

    def _save_cache(self, events: List[EconomicEvent]):
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump([e.to_dict() for e in events], f, indent=2)
        except IOError as e:
            logger.warning(f"Erreur cache : {e}")

    def _load_cache(self) -> List[EconomicEvent]:
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [
                EconomicEvent(
                    title=d['title'],
                    country=d['country'],
                    impact=d['impact'],
                    time=datetime.fromisoformat(d['time']),
                    forecast=d.get('forecast'),
                    previous=d.get('previous'),
                )
                for d in data
            ]
        except (IOError, json.JSONDecodeError, KeyError):
            return []


# ============================================================================
# GÉNÉRATION DE FICHIER POUR L'EA MT5
# ============================================================================

def export_for_mt5(output_path: str = 'news_blackout.csv'):
    """
    Exporte les fenêtres de blackout pour l'EA MT5.
    L'EA lit ce CSV pour savoir quand ne PAS trader.
    Format : start_timestamp,end_timestamp,event_title
    """
    calendar = EconomicCalendar()
    events = calendar.get_upcoming_high_impact(hours_ahead=7 * 24)

    window = timedelta(minutes=calendar.SAFETY_WINDOW_MINUTES)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("start_unix,end_unix,event\n")
        for e in events:
            start = int((e.time - window).timestamp())
            end = int((e.time + window).timestamp())
            # Nettoyer le titre des virgules pour le CSV
            title = re.sub(r'[,\n\r]', ' ', e.title)
            f.write(f"{start},{end},{e.country}: {title}\n")

    print(f"Fichier blackout exporté : {output_path} ({len(events)} événements)")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import sys

    calendar = EconomicCalendar()

    print("=" * 70)
    print("CALENDRIER ÉCONOMIQUE - Événements à fort impact (7 jours)")
    print("=" * 70)

    upcoming = calendar.get_upcoming_high_impact(hours_ahead=7 * 24)
    if not upcoming:
        print("Aucun événement à fort impact dans les 7 prochains jours.")
        print("(ou problème de récupération du flux RSS)")
    else:
        for event in upcoming:
            print(f"\n📅 {event.time.strftime('%Y-%m-%d %H:%M UTC')} [{event.country}]")
            print(f"   🔴 {event.title}")
            if event.forecast:
                print(f"   Prévision : {event.forecast} | Précédent : {event.previous}")

    print("\n" + "=" * 70)
    print("TEST : Peut-on trader EURUSD maintenant ?")
    print("=" * 70)
    safe, event = calendar.is_safe_to_trade('EURUSD')
    if safe:
        print("✅ Oui, aucune news majeure dans la fenêtre de sécurité")
    else:
        print(f"⛔ Non : {event.country} - {event.title} à {event.time}")

    # Export pour MT5 si demandé
    if '--export' in sys.argv:
        export_for_mt5('/home/claude/trading_bot/data/news_blackout.csv')
