"""
Module de calcul des horaires d'ouverture des marchés financiers.
Gère les sessions forex (24/5) et les bourses actions principales.
"""

from datetime import datetime, time, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import zoneinfo


class MarketStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    OPENS_SOON = "opens_soon"    # Ouvre dans < 1h
    CLOSES_SOON = "closes_soon"  # Ferme dans < 30min


@dataclass
class MarketSession:
    """Session de marché"""
    name: str                    # "Tokyo", "London", ...
    emoji: str                   # 🇯🇵 🇬🇧 🇺🇸 🇦🇺
    timezone: str                # "Asia/Tokyo"
    open_time: time              # Heure d'ouverture locale
    close_time: time             # Heure de fermeture locale
    is_forex: bool = True        # True = forex 24/5, False = bourse actions
    weekdays_only: bool = True   # True = fermé WE


# ============================================================================
# SESSIONS FOREX (4 grandes sessions 24/5)
# ============================================================================
FOREX_SESSIONS = [
    MarketSession(
        name="Sydney",
        emoji="🇦🇺",
        timezone="Australia/Sydney",
        open_time=time(7, 0),
        close_time=time(16, 0),
    ),
    MarketSession(
        name="Tokyo",
        emoji="🇯🇵",
        timezone="Asia/Tokyo",
        open_time=time(9, 0),
        close_time=time(18, 0),
    ),
    MarketSession(
        name="Londres",
        emoji="🇬🇧",
        timezone="Europe/London",
        open_time=time(8, 0),
        close_time=time(17, 0),
    ),
    MarketSession(
        name="New York",
        emoji="🇺🇸",
        timezone="America/New_York",
        open_time=time(8, 0),
        close_time=time(17, 0),
    ),
]

# ============================================================================
# BOURSES ACTIONS PRINCIPALES
# ============================================================================
STOCK_EXCHANGES = [
    MarketSession(
        name="NYSE (New York)",
        emoji="🇺🇸",
        timezone="America/New_York",
        open_time=time(9, 30),
        close_time=time(16, 0),
        is_forex=False,
    ),
    MarketSession(
        name="NASDAQ",
        emoji="🇺🇸",
        timezone="America/New_York",
        open_time=time(9, 30),
        close_time=time(16, 0),
        is_forex=False,
    ),
    MarketSession(
        name="Euronext Paris",
        emoji="🇫🇷",
        timezone="Europe/Paris",
        open_time=time(9, 0),
        close_time=time(17, 30),
        is_forex=False,
    ),
    MarketSession(
        name="LSE (Londres)",
        emoji="🇬🇧",
        timezone="Europe/London",
        open_time=time(8, 0),
        close_time=time(16, 30),
        is_forex=False,
    ),
    MarketSession(
        name="Xetra (Francfort)",
        emoji="🇩🇪",
        timezone="Europe/Berlin",
        open_time=time(9, 0),
        close_time=time(17, 30),
        is_forex=False,
    ),
    MarketSession(
        name="Tokyo (TSE)",
        emoji="🇯🇵",
        timezone="Asia/Tokyo",
        open_time=time(9, 0),
        close_time=time(15, 0),
        is_forex=False,
    ),
    MarketSession(
        name="Hong Kong",
        emoji="🇭🇰",
        timezone="Asia/Hong_Kong",
        open_time=time(9, 30),
        close_time=time(16, 0),
        is_forex=False,
    ),
]


@dataclass
class MarketInfo:
    """État courant d'un marché"""
    session: MarketSession
    status: MarketStatus
    local_time: datetime         # Heure locale du marché
    opens_in: Optional[timedelta]   # Temps avant ouverture (si fermé)
    closes_in: Optional[timedelta]  # Temps avant fermeture (si ouvert)
    is_weekend: bool = False


def get_market_status(session: MarketSession,
                      reference_time: Optional[datetime] = None) -> MarketInfo:
    """
    Détermine le statut actuel d'un marché.

    Args:
        session: La session à évaluer
        reference_time: Temps de référence (par défaut maintenant UTC)
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    # Convertir en heure locale du marché
    try:
        tz = zoneinfo.ZoneInfo(session.timezone)
    except Exception:
        tz = timezone.utc
    local_time = reference_time.astimezone(tz)
    weekday = local_time.weekday()  # 0=lundi, 6=dimanche
    is_weekend = weekday >= 5

    # Heure actuelle en minutes depuis minuit
    now_minutes = local_time.hour * 60 + local_time.minute
    open_minutes = session.open_time.hour * 60 + session.open_time.minute
    close_minutes = session.close_time.hour * 60 + session.close_time.minute

    # Cas spécial forex : si session chevauche minuit (ex: Sydney)
    # Pour simplifier on considère que toutes les sessions sont dans la journée

    opens_in = None
    closes_in = None

    if session.weekdays_only and is_weekend:
        # Week-end : marché fermé
        # Calculer quand il rouvrira (lundi à l'ouverture)
        days_until_monday = (7 - weekday) if weekday > 0 else 0
        if weekday == 5:
            days_until_monday = 2
        elif weekday == 6:
            days_until_monday = 1
        next_open = local_time.replace(
            hour=session.open_time.hour,
            minute=session.open_time.minute,
            second=0, microsecond=0
        ) + timedelta(days=days_until_monday)
        opens_in = next_open - local_time
        return MarketInfo(
            session=session,
            status=MarketStatus.CLOSED,
            local_time=local_time,
            opens_in=opens_in,
            closes_in=None,
            is_weekend=True,
        )

    # Semaine : vérifier si dans la plage horaire
    if open_minutes <= now_minutes < close_minutes:
        # Ouvert
        status = MarketStatus.OPEN
        closes_in = timedelta(minutes=close_minutes - now_minutes)
        if closes_in < timedelta(minutes=30):
            status = MarketStatus.CLOSES_SOON
    else:
        # Fermé
        status = MarketStatus.CLOSED
        if now_minutes < open_minutes:
            opens_in = timedelta(minutes=open_minutes - now_minutes)
        else:
            # Fermé ce soir, rouvre demain
            opens_in = timedelta(minutes=(24 * 60 - now_minutes) + open_minutes)
            # Si demain est un week-end
            tomorrow = local_time + timedelta(days=1)
            if tomorrow.weekday() == 5 and session.weekdays_only:
                opens_in += timedelta(days=2)
        if opens_in < timedelta(hours=1):
            status = MarketStatus.OPENS_SOON

    return MarketInfo(
        session=session,
        status=status,
        local_time=local_time,
        opens_in=opens_in,
        closes_in=closes_in,
        is_weekend=is_weekend,
    )


def get_all_forex_status(reference_time: Optional[datetime] = None) -> List[MarketInfo]:
    """Retourne le statut de toutes les sessions forex"""
    return [get_market_status(s, reference_time) for s in FOREX_SESSIONS]


def get_all_stocks_status(reference_time: Optional[datetime] = None) -> List[MarketInfo]:
    """Retourne le statut de toutes les bourses actions"""
    return [get_market_status(s, reference_time) for s in STOCK_EXCHANGES]


def get_forex_overlaps(reference_time: Optional[datetime] = None) -> List[str]:
    """Retourne les chevauchements de sessions forex actuellement en cours"""
    open_sessions = [
        info.session.name for info in get_all_forex_status(reference_time)
        if info.status in (MarketStatus.OPEN, MarketStatus.CLOSES_SOON)
    ]
    return open_sessions


def format_timedelta(td: timedelta) -> str:
    """Formate un timedelta en 'Xh Ym'"""
    total_seconds = int(td.total_seconds())
    if total_seconds < 0:
        return "—"
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        if hours >= 24:
            days = hours // 24
            remaining_hours = hours % 24
            return f"{days}j {remaining_hours}h"
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"
