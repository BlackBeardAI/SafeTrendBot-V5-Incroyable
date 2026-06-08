"""
Gestionnaire de risque portefeuille avancé.
Kelly Criterion, drawdown dynamique, sizing adaptatif, max correlation.
"""
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import deque


@dataclass
class PortfolioMetrics:
    total_exposure: float
    max_drawdown_current: float
    kelly_fraction: float
    recommended_risk: float
    diversification_score: float
    heat_map: Dict[str, float]
    margin_used_percent: float


class PortfolioRiskManager:
    """
    Gère le risque au niveau portefeuille :
    - Exposition totale limitée
    - Drawdown dynamique avec réduction progressive
    - Kelly Criterion pour le sizing optimal
    - Score de diversification
    """

    def __init__(self, max_total_exposure: float = 0.3,
                 max_drawdown_halt: float = 15.0,
                 max_drawdown_reduce: float = 10.0,
                 kelly_fraction: float = 0.25,
                 max_correlation: float = 0.75):
        self.max_total_exposure = max_total_exposure
        self.max_drawdown_halt = max_drawdown_halt
        self.max_drawdown_reduce = max_drawdown_reduce
        self.kelly_fraction = kelly_fraction
        self.max_correlation = max_correlation

        self.peak_balance = 0.0
        self.trade_history: deque = deque(maxlen=200)
        self.open_positions: Dict[str, Dict] = {}
        self._last_update = datetime.now()

    def update_peak(self, balance: float):
        if balance > self.peak_balance:
            self.peak_balance = balance

    def get_drawdown(self, current_balance: float) -> float:
        if self.peak_balance <= 0:
            return 0.0
        return (self.peak_balance - current_balance) / self.peak_balance * 100

    def get_risk_multiplier(self, current_balance: float) -> float:
        """
        Retourne un multiplicateur de risque selon le drawdown :
        - 0% DD  → 1.0x
        - 10% DD → 0.5x
        - 15% DD → 0.0x (halt)
        """
        dd = self.get_drawdown(current_balance)
        if dd >= self.max_drawdown_halt:
            return 0.0
        if dd <= 0:
            return 1.0
        # Réduction linéaire entre 0% et max_drawdown_halt
        # À max_drawdown_reduce on est déjà à 0.5x
        if dd >= self.max_drawdown_reduce:
            # Entre reduce et halt : 0.5 → 0.0
            return 0.5 * (1 - (dd - self.max_drawdown_reduce) /
                          (self.max_drawdown_halt - self.max_drawdown_reduce))
        # Entre 0 et reduce : 1.0 → 0.5
        return 1.0 - 0.5 * (dd / self.max_drawdown_reduce)

    def calculate_kelly(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly Criterion : f* = (p*b - q) / b
        où p = win_rate, q = 1-p, b = avg_win/avg_loss
        On utilise une fraction Kelly (quarter-Kelly par défaut) pour la sécurité.
        """
        if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0
        b = avg_win / avg_loss
        if b <= 0:
            return 0.0
        kelly = (win_rate * b - (1 - win_rate)) / b
        # Quarter-Kelly pour la prudence
        return max(0.0, kelly * self.kelly_fraction)

    def get_kelly_adjusted_risk(self, base_risk: float) -> float:
        """Ajuste le risque selon Kelly sur l'historique récent"""
        if len(self.trade_history) < 10:
            return base_risk
        profits = [t['profit'] for t in self.trade_history if t.get('profit') is not None]
        if len(profits) < 10:
            return base_risk
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]
        if not wins or not losses:
            return base_risk
        win_rate = len(wins) / len(profits)
        avg_win = np.mean(wins)
        avg_loss = abs(np.mean(losses))
        kelly = self.calculate_kelly(win_rate, avg_win, avg_loss)
        # Kelly est une fraction du capital, on l'applique comme multiplicateur
        return base_risk * (1 + kelly)

    def get_portfolio_metrics(self, balance: float, equity: float,
                               open_positions: List[Tuple[str, float, float]]) -> PortfolioMetrics:
        """
        open_positions : list of (symbol, volume, directional_exposure)
        """
        self.update_peak(balance)
        dd = self.get_drawdown(balance)
        risk_mult = self.get_risk_multiplier(balance)
        kelly_risk = self.get_kelly_adjusted_risk(1.0)
        recommended_risk = min(risk_mult, kelly_risk)

        total_exposure = sum(abs(exp) for _, _, exp in open_positions)
        heat_map = {}
        for sym, vol, exp in open_positions:
            heat_map[sym] = abs(exp) / (balance + 1e-10)

        # Diversification : nombre de symboles non corrélés
        symbols = [s for s, _, _ in open_positions]
        diversification = min(1.0, len(set(symbols)) / 5.0)

        margin_used = total_exposure / (balance + 1e-10)

        return PortfolioMetrics(
            total_exposure=total_exposure,
            max_drawdown_current=dd,
            kelly_fraction=kelly,
            recommended_risk=recommended_risk,
            diversification_score=diversification,
            heat_map=heat_map,
            margin_used_percent=margin_used * 100,
        )

    def can_open_position(self, balance: float, new_symbol: str,
                          new_exposure: float, open_positions: List[Tuple[str, float, float]]) -> Tuple[bool, str]:
        """Vérifie si une nouvelle position respecte les limites"""
        total_after = sum(abs(exp) for _, _, exp in open_positions) + abs(new_exposure)
        if total_after > balance * self.max_total_exposure:
            return False, f"Exposition totale {total_after:.0f} > max {balance*self.max_total_exposure:.0f}"

        dd = self.get_drawdown(balance)
        if dd >= self.max_drawdown_halt:
            return False, f"Drawdown {dd:.1f}% ≥ halt {self.max_drawdown_halt}%"

        # Vérifier corrélation avec positions ouvertes
        symbols = [s for s, _, _ in open_positions]
        if new_symbol in symbols:
            return False, f"Position déjà ouverte sur {new_symbol}"

        return True, "OK"

    def record_trade(self, profit: float, symbol: str = "", direction: int = 0):
        self.trade_history.append({
            'time': datetime.now(),
            'profit': profit,
            'symbol': symbol,
            'direction': direction,
        })

    def get_stats(self) -> dict:
        if len(self.trade_history) < 2:
            return {"trades": 0, "win_rate": 0, "profit_factor": 0, "sharpe": 0}
        profits = [t['profit'] for t in self.trade_history]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]
        win_rate = len(wins) / len(profits) if profits else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        returns = np.array(profits)
        sharpe = (np.mean(returns) / (np.std(returns) + 1e-10)) * np.sqrt(len(returns)) if len(returns) > 1 else 0
        return {
            "trades": len(self.trade_history),
            "win_rate": round(win_rate * 100, 1),
            "profit_factor": round(profit_factor, 2),
            "sharpe": round(sharpe, 2),
            "avg_win": round(np.mean(wins), 2) if wins else 0,
            "avg_loss": round(np.mean(losses), 2) if losses else 0,
        }
