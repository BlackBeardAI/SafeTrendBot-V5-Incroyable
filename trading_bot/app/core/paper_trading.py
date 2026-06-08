"""
Mode Paper Trading : simulation en temps réel avec vraies données de marché
mais sans exécuter les ordres sur le broker.

Utile pour :
- Tester de nouveaux paramètres en live sans risque
- Valider une stratégie avant passage en réel
- Entraînement personnel
"""

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path


@dataclass
class PaperTrade:
    """Trade simulé"""
    ticket: int
    symbol: str
    direction: int                      # 1 = long, -1 = short
    volume: float
    entry_price: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: str = ""
    profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0

    def to_dict(self):
        d = asdict(self)
        d['entry_time'] = self.entry_time.isoformat()
        if self.exit_time:
            d['exit_time'] = self.exit_time.isoformat()
        return d


@dataclass
class PaperAccount:
    """Compte paper trading"""
    initial_balance: float
    balance: float
    equity: float
    currency: str = "USD"
    leverage: int = 100
    margin: float = 0.0
    free_margin: float = 0.0


class PaperTradingEngine:
    """
    Moteur de simulation - trade en mémoire sans toucher au vrai compte.
    Les trades sont persistés sur disque.
    """

    def __init__(self, initial_balance: float = 10000.0,
                 data_dir: Optional[Path] = None,
                 commission_per_lot: float = 7.0):
        self.account = PaperAccount(
            initial_balance=initial_balance,
            balance=initial_balance,
            equity=initial_balance,
        )
        self.open_trades: Dict[int, PaperTrade] = {}
        self.closed_trades: List[PaperTrade] = []
        self.commission_per_lot = commission_per_lot
        self._next_ticket = 1000000

        # Persistance
        if data_dir:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.trades_file = self.data_dir / 'paper_trades.json'
            self.account_file = self.data_dir / 'paper_account.json'
            self._load()
        else:
            self.data_dir = None
            self.trades_file = None
            self.account_file = None

    # ========================================================================
    # OUVERTURE / FERMETURE
    # ========================================================================

    def open_trade(self, symbol: str, direction: int, volume: float,
                   entry_price: float, stop_loss: float, take_profit: float) -> PaperTrade:
        """Ouvre un trade simulé"""
        ticket = self._next_ticket
        self._next_ticket += 1

        trade = PaperTrade(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            volume=volume,
            entry_price=entry_price,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=self.commission_per_lot * volume,
        )
        self.open_trades[ticket] = trade
        self._save()
        return trade

    def close_trade(self, ticket: int, exit_price: float, reason: str = "Manual"):
        """Ferme un trade simulé"""
        if ticket not in self.open_trades:
            return None
        trade = self.open_trades.pop(ticket)
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.exit_reason = reason

        # Calcul du profit (forex : 1 lot = 100k unités)
        price_diff = (exit_price - trade.entry_price) * trade.direction
        trade.profit = price_diff * trade.volume * 100000 - trade.commission

        self.account.balance += trade.profit
        self.closed_trades.append(trade)
        self._save()
        return trade

    def update_prices(self, prices: Dict[str, tuple]):
        """
        Met à jour les prix et vérifie les SL/TP.

        Args:
            prices: Dict {symbol: (bid, ask)}
        """
        closed_this_tick = []

        for ticket, trade in list(self.open_trades.items()):
            if trade.symbol not in prices:
                continue

            bid, ask = prices[trade.symbol]

            if trade.direction == 1:  # Long
                # Prix actuel = bid (on vend pour clôturer)
                current = bid
                if current <= trade.stop_loss:
                    self.close_trade(ticket, trade.stop_loss, "SL")
                    closed_this_tick.append(trade)
                elif current >= trade.take_profit:
                    self.close_trade(ticket, trade.take_profit, "TP")
                    closed_this_tick.append(trade)
            else:  # Short
                current = ask
                if current >= trade.stop_loss:
                    self.close_trade(ticket, trade.stop_loss, "SL")
                    closed_this_tick.append(trade)
                elif current <= trade.take_profit:
                    self.close_trade(ticket, trade.take_profit, "TP")
                    closed_this_tick.append(trade)

        # Mettre à jour l'équité
        self._update_equity(prices)
        return closed_this_tick

    def _update_equity(self, prices: Dict[str, tuple]):
        """Calcule l'équité = balance + P&L ouvert"""
        unrealized = 0.0
        for trade in self.open_trades.values():
            if trade.symbol not in prices:
                continue
            bid, ask = prices[trade.symbol]
            current = bid if trade.direction == 1 else ask
            diff = (current - trade.entry_price) * trade.direction
            unrealized += diff * trade.volume * 100000

        self.account.equity = self.account.balance + unrealized

    def modify_stop_loss(self, ticket: int, new_sl: float) -> bool:
        """Modifie le SL d'un trade ouvert"""
        if ticket in self.open_trades:
            self.open_trades[ticket].stop_loss = new_sl
            self._save()
            return True
        return False

    # ========================================================================
    # STATISTIQUES
    # ========================================================================

    def get_stats(self) -> dict:
        """Calcule les statistiques complètes"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'return_pct': 0,
                'balance': self.account.balance,
                'equity': self.account.equity,
                'open_trades': len(self.open_trades),
            }

        wins = [t for t in self.closed_trades if t.profit > 0]
        losses = [t for t in self.closed_trades if t.profit < 0]

        total_wins = sum(t.profit for t in wins)
        total_losses = abs(sum(t.profit for t in losses))

        return_pct = (self.account.balance / self.account.initial_balance - 1) * 100

        return {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(self.closed_trades) * 100 if self.closed_trades else 0,
            'total_profit': total_wins,
            'total_loss': total_losses,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf'),
            'avg_win': total_wins / len(wins) if wins else 0,
            'avg_loss': -total_losses / len(losses) if losses else 0,
            'balance': self.account.balance,
            'equity': self.account.equity,
            'return_pct': return_pct,
            'open_trades': len(self.open_trades),
        }

    def reset(self):
        """Réinitialise le compte paper"""
        self.account.balance = self.account.initial_balance
        self.account.equity = self.account.initial_balance
        self.open_trades.clear()
        self.closed_trades.clear()
        self._next_ticket = 1000000
        self._save()

    # ========================================================================
    # PERSISTANCE
    # ========================================================================

    def _save(self):
        if not self.trades_file:
            return
        try:
            data = {
                'account': asdict(self.account),
                'open_trades': [t.to_dict() for t in self.open_trades.values()],
                'closed_trades': [t.to_dict() for t in self.closed_trades],
                'next_ticket': self._next_ticket,
            }
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except IOError:
            pass

    def _load(self):
        if not self.trades_file or not self.trades_file.exists():
            return
        try:
            with open(self.trades_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'account' in data:
                a = data['account']
                self.account = PaperAccount(**a)

            self._next_ticket = data.get('next_ticket', 1000000)

            for t_data in data.get('closed_trades', []):
                self.closed_trades.append(self._trade_from_dict(t_data))
            for t_data in data.get('open_trades', []):
                trade = self._trade_from_dict(t_data)
                self.open_trades[trade.ticket] = trade
        except (IOError, json.JSONDecodeError, KeyError):
            pass

    def _trade_from_dict(self, d: dict) -> PaperTrade:
        t = PaperTrade(
            ticket=d['ticket'],
            symbol=d['symbol'],
            direction=d['direction'],
            volume=d['volume'],
            entry_price=d['entry_price'],
            entry_time=datetime.fromisoformat(d['entry_time']),
            stop_loss=d['stop_loss'],
            take_profit=d['take_profit'],
            commission=d.get('commission', 0),
            swap=d.get('swap', 0),
        )
        if d.get('exit_time'):
            t.exit_time = datetime.fromisoformat(d['exit_time'])
        if d.get('exit_price') is not None:
            t.exit_price = d['exit_price']
        t.exit_reason = d.get('exit_reason', '')
        t.profit = d.get('profit', 0)
        return t
