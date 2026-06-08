"""
Journal de trading automatique.
Enregistre chaque trade avec son contexte complet pour analyse ultérieure.
"""

import json
import csv
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path


@dataclass
class TradeJournalEntry:
    """Entrée complète du journal de trading"""
    # Identification
    ticket: int
    symbol: str
    timeframe: str

    # Trade
    direction: str                      # "BUY" / "SELL"
    volume: float
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float

    # Contexte à l'entrée
    entry_balance: float
    entry_equity: float
    atr_value: float
    volatility_regime: str
    confidence_score: float
    strategies_agreed: List[str]        # Noms des stratégies qui ont voté pour
    buy_votes: int
    sell_votes: int
    
    # Indicateurs techniques
    indicators: Dict[str, float] = field(default_factory=dict)
    
    # Résultat (rempli à la clôture)
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: str = ""              # "TP", "SL", "Manual", "Trailing", etc.
    profit: float = 0.0
    profit_pct: float = 0.0            # Par rapport au capital
    duration_minutes: int = 0
    
    # Notes manuelles (pour revue a posteriori)
    user_notes: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            d['exit_time'] = self.exit_time.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'TradeJournalEntry':
        d = dict(d)
        d['entry_time'] = datetime.fromisoformat(d['entry_time'])
        if d.get('exit_time'):
            d['exit_time'] = datetime.fromisoformat(d['exit_time'])
        return cls(**d)


class TradeJournal:
    """Journal persistant de trades avec contexte et analyse"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.data_dir / 'trade_journal.json'
        self.entries: Dict[int, TradeJournalEntry] = {}
        self._load()

    def record_entry(self, entry: TradeJournalEntry):
        """Enregistre une nouvelle entrée"""
        self.entries[entry.ticket] = entry
        self._save()

    def record_exit(self, ticket: int, exit_price: float, exit_reason: str,
                    profit: float, capital: float):
        """Met à jour une entrée avec les infos de sortie"""
        if ticket not in self.entries:
            return
        entry = self.entries[ticket]
        entry.exit_price = exit_price
        entry.exit_time = datetime.now()
        entry.exit_reason = exit_reason
        entry.profit = profit
        entry.profit_pct = (profit / capital * 100) if capital > 0 else 0
        if entry.entry_time:
            delta = entry.exit_time - entry.entry_time
            entry.duration_minutes = int(delta.total_seconds() / 60)
        self._save()

    def add_note(self, ticket: int, note: str):
        """Ajoute une note utilisateur à un trade"""
        if ticket in self.entries:
            self.entries[ticket].user_notes = note
            self._save()

    def add_tags(self, ticket: int, tags: List[str]):
        """Ajoute des tags à un trade"""
        if ticket in self.entries:
            self.entries[ticket].tags.extend(tags)
            self.entries[ticket].tags = list(set(self.entries[ticket].tags))
            self._save()

    # ========================================================================
    # ANALYSES
    # ========================================================================

    def get_all(self, only_closed: bool = False) -> List[TradeJournalEntry]:
        entries = list(self.entries.values())
        if only_closed:
            entries = [e for e in entries if e.exit_time is not None]
        return sorted(entries, key=lambda e: e.entry_time, reverse=True)

    def analyze_by_strategy(self) -> Dict[str, dict]:
        """Performance par stratégie (celles qui ont voté)"""
        stats = {}
        for entry in self.entries.values():
            if entry.exit_time is None:
                continue
            for strategy in entry.strategies_agreed:
                if strategy not in stats:
                    stats[strategy] = {'count': 0, 'wins': 0, 'profit': 0.0}
                stats[strategy]['count'] += 1
                stats[strategy]['profit'] += entry.profit
                if entry.profit > 0:
                    stats[strategy]['wins'] += 1

        # Calculer les ratios
        for s, d in stats.items():
            d['win_rate'] = d['wins'] / d['count'] * 100 if d['count'] > 0 else 0
            d['avg_profit'] = d['profit'] / d['count'] if d['count'] > 0 else 0
        return stats

    def analyze_by_symbol(self) -> Dict[str, dict]:
        """Performance par symbole"""
        stats = {}
        for entry in self.entries.values():
            if entry.exit_time is None:
                continue
            s = entry.symbol
            if s not in stats:
                stats[s] = {'count': 0, 'wins': 0, 'profit': 0.0}
            stats[s]['count'] += 1
            stats[s]['profit'] += entry.profit
            if entry.profit > 0:
                stats[s]['wins'] += 1
        for d in stats.values():
            d['win_rate'] = d['wins'] / d['count'] * 100 if d['count'] > 0 else 0
            d['avg_profit'] = d['profit'] / d['count'] if d['count'] > 0 else 0
        return stats

    def analyze_by_volatility(self) -> Dict[str, dict]:
        """Performance par régime de volatilité"""
        stats = {}
        for entry in self.entries.values():
            if entry.exit_time is None:
                continue
            v = entry.volatility_regime
            if v not in stats:
                stats[v] = {'count': 0, 'wins': 0, 'profit': 0.0}
            stats[v]['count'] += 1
            stats[v]['profit'] += entry.profit
            if entry.profit > 0:
                stats[v]['wins'] += 1
        for d in stats.values():
            d['win_rate'] = d['wins'] / d['count'] * 100 if d['count'] > 0 else 0
            d['avg_profit'] = d['profit'] / d['count'] if d['count'] > 0 else 0
        return stats

    def analyze_by_hour(self) -> Dict[int, dict]:
        """Performance par heure de la journée"""
        stats = {h: {'count': 0, 'wins': 0, 'profit': 0.0} for h in range(24)}
        for entry in self.entries.values():
            if entry.exit_time is None:
                continue
            h = entry.entry_time.hour
            stats[h]['count'] += 1
            stats[h]['profit'] += entry.profit
            if entry.profit > 0:
                stats[h]['wins'] += 1
        for d in stats.values():
            d['win_rate'] = d['wins'] / d['count'] * 100 if d['count'] > 0 else 0
        return stats

    def analyze_by_confidence(self) -> dict:
        """Performance par niveau de confiance"""
        buckets = {
            'Low (0.4-0.5)': [],
            'Medium (0.5-0.7)': [],
            'High (0.7-1.0)': [],
        }
        for entry in self.entries.values():
            if entry.exit_time is None:
                continue
            if entry.confidence_score < 0.5:
                buckets['Low (0.4-0.5)'].append(entry)
            elif entry.confidence_score < 0.7:
                buckets['Medium (0.5-0.7)'].append(entry)
            else:
                buckets['High (0.7-1.0)'].append(entry)

        stats = {}
        for bucket, entries in buckets.items():
            if not entries:
                stats[bucket] = {'count': 0, 'win_rate': 0, 'profit': 0, 'avg_profit': 0}
                continue
            wins = sum(1 for e in entries if e.profit > 0)
            profit = sum(e.profit for e in entries)
            stats[bucket] = {
                'count': len(entries),
                'wins': wins,
                'win_rate': wins / len(entries) * 100,
                'profit': profit,
                'avg_profit': profit / len(entries),
            }
        return stats

    # ========================================================================
    # EXPORTS
    # ========================================================================

    def export_csv(self, filepath: Path):
        """Exporte tout le journal en CSV"""
        if not self.entries:
            return
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Ticket', 'Symbole', 'Direction', 'Volume',
                'Date entrée', 'Prix entrée', 'SL', 'TP',
                'Date sortie', 'Prix sortie', 'Raison sortie',
                'Profit', 'Profit %', 'Durée (min)',
                'Confiance', 'Stratégies', 'Régime volatilité',
                'Notes', 'Tags',
            ])
            for entry in self.get_all():
                writer.writerow([
                    entry.ticket, entry.symbol, entry.direction, entry.volume,
                    entry.entry_time.strftime('%Y-%m-%d %H:%M'),
                    entry.entry_price, entry.stop_loss, entry.take_profit,
                    entry.exit_time.strftime('%Y-%m-%d %H:%M') if entry.exit_time else '',
                    entry.exit_price or '', entry.exit_reason,
                    entry.profit, entry.profit_pct, entry.duration_minutes,
                    entry.confidence_score, ','.join(entry.strategies_agreed),
                    entry.volatility_regime, entry.user_notes, ','.join(entry.tags),
                ])

    # ========================================================================
    # PERSISTANCE
    # ========================================================================

    def _save(self):
        try:
            data = {t: e.to_dict() for t, e in self.entries.items()}
            with open(self.journal_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except IOError:
            pass

    def _load(self):
        if not self.journal_file.exists():
            return
        try:
            with open(self.journal_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for ticket_str, entry_data in data.items():
                entry = TradeJournalEntry.from_dict(entry_data)
                self.entries[int(ticket_str)] = entry
        except (IOError, json.JSONDecodeError, KeyError, ValueError):
            pass
