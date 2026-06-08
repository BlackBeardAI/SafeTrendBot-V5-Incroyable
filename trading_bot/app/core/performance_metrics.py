"""
Métriques de performance temps réel.
Sharpe, Sortino, Calmar, Expectancy, Win Rate dynamique.
"""
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from collections import deque


@dataclass
class PerformanceSnapshot:
    timestamp: datetime
    equity: float
    balance: float
    open_pnl: float
    daily_pnl: float
    trades_count: int
    win_rate: float
    profit_factor: float
    sharpe: float
    sortino: float
    max_drawdown: float
    expectancy: float
    avg_trade: float
    consecutive_wins: int
    consecutive_losses: int


class PerformanceTracker:
    """
    Suit les métriques de performance en temps réel.
    Calcule Sharpe, Sortino, Calmar, Expectancy sur fenêtre glissante.
    """

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.trades: deque = deque(maxlen=window_size)
        self.equity_curve: deque = deque(maxlen=500)
        self.snapshots: deque = deque(maxlen=100)
        self._consecutive_wins = 0
        self._consecutive_losses = 0
        self._peak_equity = 0.0
        self._max_drawdown = 0.0

    def add_trade(self, profit: float, symbol: str = "", direction: int = 0,
                  entry_time: Optional[datetime] = None):
        trade = {
            'profit': profit,
            'symbol': symbol,
            'direction': direction,
            'time': entry_time or datetime.now(),
        }
        self.trades.append(trade)
        if profit > 0:
            self._consecutive_wins += 1
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1
            self._consecutive_wins = 0

    def add_equity_point(self, equity: float):
        self.equity_curve.append({'time': datetime.now(), 'equity': equity})
        if equity > self._peak_equity:
            self._peak_equity = equity
        dd = (self._peak_equity - equity) / (self._peak_equity + 1e-10) * 100
        if dd > self._max_drawdown:
            self._max_drawdown = dd

    def get_metrics(self, current_balance: float, current_equity: float) -> PerformanceSnapshot:
        profits = [t['profit'] for t in self.trades]
        n = len(profits)

        if n == 0:
            return PerformanceSnapshot(
                timestamp=datetime.now(), equity=current_equity, balance=current_balance,
                open_pnl=current_equity - current_balance, daily_pnl=0,
                trades_count=0, win_rate=0, profit_factor=0, sharpe=0,
                sortino=0, max_drawdown=self._max_drawdown, expectancy=0, avg_trade=0,
                consecutive_wins=0, consecutive_losses=0,
            )

        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]
        win_rate = len(wins) / n
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        avg_trade = np.mean(profits)
        expectancy = (win_rate * (np.mean(wins) if wins else 0) -
                      (1 - win_rate) * (abs(np.mean(losses)) if losses else 0))

        returns = np.array(profits)
        sharpe = self._sharpe(returns)
        sortino = self._sortino(returns)

        # Daily PnL (last 24h)
        cutoff = datetime.now() - timedelta(hours=24)
        daily_trades = [t for t in self.trades if t['time'] > cutoff]
        daily_pnl = sum(t['profit'] for t in daily_trades)

        return PerformanceSnapshot(
            timestamp=datetime.now(),
            equity=current_equity,
            balance=current_balance,
            open_pnl=current_equity - current_balance,
            daily_pnl=daily_pnl,
            trades_count=n,
            win_rate=round(win_rate * 100, 1),
            profit_factor=round(profit_factor, 2),
            sharpe=round(sharpe, 2),
            sortino=round(sortino, 2),
            max_drawdown=round(self._max_drawdown, 2),
            expectancy=round(expectancy, 2),
            avg_trade=round(avg_trade, 2),
            consecutive_wins=self._consecutive_wins,
            consecutive_losses=self._consecutive_losses,
        )

    def _sharpe(self, returns: np.ndarray) -> float:
        if len(returns) < 2:
            return 0.0
        mean = np.mean(returns)
        std = np.std(returns)
        if std == 0:
            return 0.0
        return (mean / std) * np.sqrt(len(returns))

    def _sortino(self, returns: np.ndarray) -> float:
        if len(returns) < 2:
            return 0.0
        downside = returns[returns < 0]
        downside_std = np.std(downside) if len(downside) > 0 else 0.0
        if downside_std == 0:
            return 0.0
        return (np.mean(returns) / downside_std) * np.sqrt(len(returns))

    def get_equity_curve(self) -> List[Dict]:
        return list(self.equity_curve)

    def get_heatmap_by_hour(self) -> Dict[int, dict]:
        """Heatmap des performances par heure"""
        hours = {h: {'trades': 0, 'profit': 0, 'wins': 0} for h in range(24)}
        for t in self.trades:
            h = t['time'].hour
            hours[h]['trades'] += 1
            hours[h]['profit'] += t['profit']
            if t['profit'] > 0:
                hours[h]['wins'] += 1
        for h in hours:
            t = hours[h]['trades']
            hours[h]['win_rate'] = round(hours[h]['wins'] / t * 100, 1) if t > 0 else 0
        return hours
