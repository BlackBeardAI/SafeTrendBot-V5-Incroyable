"""
Journal de décision IA — enregistre pourquoi chaque trade a été pris.
Permet le diagnostic post-mortem complet.
"""
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path


@dataclass
class DecisionRecord:
    """Enregistre toutes les données de décision d'un trade"""
    ticket: int
    symbol: str
    timestamp: str
    decision: str  # 'OPEN', 'CLOSE', 'SKIP'

    # Features au moment de la décision
    regime: str
    regime_confidence: float
    strategy_weights: Dict[str, float]
    confidence_score: float
    buy_votes: int
    sell_votes: int

    # Marché
    price: float
    spread: float
    atr: float
    volatility_regime: str
    bb_position: float

    # Risk
    risk_percent: float
    lot_size: float
    stop_distance: float
    portfolio_exposure_before: float
    portfolio_exposure_after: float

    # Filtres
    circuit_breaker_level: str
    correlation_blocked: bool
    news_sentiment: Optional[float]
    triple_screen_alignment: Optional[str]

    # Résultat (rempli à la fermeture)
    exit_price: Optional[float] = None
    profit: Optional[float] = None
    exit_reason: Optional[str] = None
    max_adverse_excursion: Optional[float] = None  # Pire drawdown intra-trade

    def to_dict(self) -> Dict:
        return asdict(self)


class DecisionJournal:
    """
    Journal intelligent qui capture le contexte complet de chaque décision.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent / '..' / '..' / 'data'
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.data_dir / 'decision_journal.jsonl'
        self._records: List[DecisionRecord] = []
        self._open_decisions: Dict[int, DecisionRecord] = {}

    def record_open(self, ticket: int, symbol: str, **kwargs) -> DecisionRecord:
        """Enregistre la décision d'ouverture avec tout le contexte"""
        record = DecisionRecord(
            ticket=ticket, symbol=symbol,
            timestamp=datetime.now().isoformat(),
            decision='OPEN',
            **kwargs
        )
        self._open_decisions[ticket] = record
        self._records.append(record)
        self._append_to_file(record)
        return record

    def record_close(self, ticket: int, exit_price: float, profit: float,
                     exit_reason: str, max_adverse_excursion: Optional[float] = None):
        """Complète le record avec les données de fermeture"""
        if ticket in self._open_decisions:
            record = self._open_decisions[ticket]
            record.exit_price = exit_price
            record.profit = profit
            record.exit_reason = exit_reason
            record.max_adverse_excursion = max_adverse_excursion
            record.decision = 'CLOSE'
            self._append_to_file(record)
            del self._open_decisions[ticket]

    def record_skip(self, symbol: str, reason: str, **kwargs):
        """Enregistre pourquoi un trade a été refusé"""
        record = DecisionRecord(
            ticket=0, symbol=symbol,
            timestamp=datetime.now().isoformat(),
            decision='SKIP',
            decision_reason=reason,
            **kwargs
        )
        self._append_to_file(record)

    def _append_to_file(self, record: DecisionRecord):
        with open(self.journal_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record.to_dict(), default=str) + '\n')

    def analyze_patterns(self, symbol: Optional[str] = None) -> Dict:
        """Analyse les patterns de réussite/échec"""
        records = [r for r in self._records if r.decision == 'OPEN']
        if symbol:
            records = [r for r in records if r.symbol == symbol]
        if not records:
            return {}

        winners = [r for r in records if (r.profit or 0) > 0]
        losers = [r for r in records if (r.profit or 0) <= 0]

        def avg(key, data):
            vals = [getattr(r, key, 0) for r in data if getattr(r, key, None) is not None]
            return sum(vals) / len(vals) if vals else 0

        return {
            'total_trades': len(records),
            'win_rate': len(winners) / len(records) * 100 if records else 0,
            'avg_profit_winners': avg('profit', winners),
            'avg_loss_losers': avg('profit', losers),
            'avg_confidence_winners': avg('confidence_score', winners),
            'avg_confidence_losers': avg('confidence_score', losers),
            'best_regime': max(set(r.regime for r in winners), key=lambda x: sum(1 for r in winners if r.regime == x)) if winners else 'N/A',
            'worst_regime': max(set(r.regime for r in losers), key=lambda x: sum(1 for r in losers if r.regime == x)) if losers else 'N/A',
            'avg_exposure_before': avg('portfolio_exposure_before', records),
        }
