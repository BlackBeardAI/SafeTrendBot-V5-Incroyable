"""
Backtester pour la stratégie SafeTrendBot
Réplique exactement la logique du bot MT5 pour valider la stratégie
avant de risquer de l'argent réel.

Usage:
    python backtest.py --symbol EURUSD=X --start 2020-01-01 --end 2025-01-01
"""

import argparse
import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass, field
from typing import List, Optional
import matplotlib.pyplot as plt
from datetime import datetime


# ============================================================================
# CONFIGURATION DE LA STRATÉGIE (identique au bot MT5)
# ============================================================================

@dataclass
class StrategyConfig:
    # Gestion du risque
    risk_percent: float = 1.0           # Risque par trade en % du capital
    risk_reward_ratio: float = 2.0      # Take profit = stop loss * ce ratio
    atr_period: int = 14
    atr_multiplier: float = 2.0
    max_consecutive_losses: int = 3
    max_daily_loss_percent: float = 3.0

    # Stratégie
    fast_ema: int = 50
    slow_ema: int = 200
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0

    # Capital initial pour le backtest
    initial_capital: float = 10000.0
    
    # Coûts de trading réalistes
    spread_pips: float = 1.0            # Spread moyen en pips
    commission_per_lot: float = 7.0     # Commission aller-retour par lot


# ============================================================================
# CLASSES DE TRADE
# ============================================================================

@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    direction: int              # 1 = long, -1 = short
    lot_size: float
    stop_loss: float
    take_profit: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    profit: float = 0.0
    exit_reason: str = ""


# ============================================================================
# INDICATEURS TECHNIQUES
# ============================================================================

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


# ============================================================================
# BACKTESTER
# ============================================================================

class Backtester:
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.reset()

    def reset(self):
        self.balance = self.config.initial_capital
        self.equity_curve: List[float] = [self.balance]
        self.equity_times: List[pd.Timestamp] = []
        self.trades: List[Trade] = []
        self.open_trade: Optional[Trade] = None
        self.consecutive_losses = 0
        self.daily_start_balance = self.balance
        self.current_day: Optional[pd.Timestamp] = None
        self.trading_halted_today = False

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule les indicateurs nécessaires"""
        df = df.copy()
        df['fast_ema'] = calculate_ema(df['Close'], self.config.fast_ema)
        df['slow_ema'] = calculate_ema(df['Close'], self.config.slow_ema)
        df['rsi'] = calculate_rsi(df['Close'], self.config.rsi_period)
        df['atr'] = calculate_atr(df, self.config.atr_period)
        
        # Détection des croisements
        df['fast_prev'] = df['fast_ema'].shift(1)
        df['slow_prev'] = df['slow_ema'].shift(1)
        
        return df.dropna()

    def check_signal(self, row) -> int:
        """Retourne 1 pour long, -1 pour short, 0 sinon"""
        bullish_cross = (row['fast_prev'] <= row['slow_prev']) and (row['fast_ema'] > row['slow_ema'])
        bullish_trend = row['Close'] > row['slow_ema']
        rsi_ok_buy = 40 < row['rsi'] < self.config.rsi_overbought

        if bullish_cross and bullish_trend and rsi_ok_buy:
            return 1

        bearish_cross = (row['fast_prev'] >= row['slow_prev']) and (row['fast_ema'] < row['slow_ema'])
        bearish_trend = row['Close'] < row['slow_ema']
        rsi_ok_sell = self.config.rsi_oversold < row['rsi'] < 60

        if bearish_cross and bearish_trend and rsi_ok_sell:
            return -1

        return 0

    def calculate_position_size(self, stop_distance: float, price: float) -> float:
        """Calcule la taille de position selon le risque"""
        risk_amount = self.balance * self.config.risk_percent / 100
        # Pour le forex, 1 lot = 100 000 unités
        # Valeur du pip pour 1 lot standard ≈ 10 USD (approximation)
        # On calcule en termes simples : combien d'unités pour risquer risk_amount sur stop_distance
        if stop_distance == 0:
            return 0
        units = risk_amount / stop_distance
        lot_size = units / 100000
        return max(0.01, round(lot_size, 2))

    def open_trade(self, row, direction: int):
        """Ouvre une nouvelle position"""
        stop_distance = row['atr'] * self.config.atr_multiplier
        entry_price = row['Close']
        
        # Ajout du spread dans le prix d'entrée
        spread = self.config.spread_pips * 0.0001
        if direction == 1:
            entry_price += spread / 2
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + stop_distance * self.config.risk_reward_ratio
        else:
            entry_price -= spread / 2
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - stop_distance * self.config.risk_reward_ratio

        lot_size = self.calculate_position_size(stop_distance, entry_price)

        self.open_trade_obj = Trade(
            entry_time=row.name,
            entry_price=entry_price,
            direction=direction,
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    def close_trade(self, trade: Trade, exit_time: pd.Timestamp, exit_price: float, reason: str):
        """Ferme une position et calcule le P&L"""
        price_diff = (exit_price - trade.entry_price) * trade.direction
        # Profit en unités de monnaie : diff * lot_size * 100000 (pour forex)
        profit = price_diff * trade.lot_size * 100000
        # Soustraction de la commission
        profit -= self.config.commission_per_lot * trade.lot_size

        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.profit = profit
        trade.exit_reason = reason

        self.balance += profit
        self.trades.append(trade)

        if profit < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def check_exit(self, trade: Trade, row) -> bool:
        """Vérifie si le trade doit être fermé (SL, TP)"""
        if trade.direction == 1:  # Long
            if row['Low'] <= trade.stop_loss:
                self.close_trade(trade, row.name, trade.stop_loss, "SL")
                return True
            if row['High'] >= trade.take_profit:
                self.close_trade(trade, row.name, trade.take_profit, "TP")
                return True
        else:  # Short
            if row['High'] >= trade.stop_loss:
                self.close_trade(trade, row.name, trade.stop_loss, "SL")
                return True
            if row['Low'] <= trade.take_profit:
                self.close_trade(trade, row.name, trade.take_profit, "TP")
                return True
        return False

    def run(self, df: pd.DataFrame) -> dict:
        """Exécute le backtest sur les données fournies"""
        self.reset()
        df = self.prepare_data(df)
        self.open_trade_obj: Optional[Trade] = None

        for idx, row in df.iterrows():
            # Reset journalier
            day = idx.normalize()
            if self.current_day != day:
                self.current_day = day
                self.daily_start_balance = self.balance
                self.trading_halted_today = False

            # Vérifier perte journalière max
            if not self.trading_halted_today:
                daily_loss_pct = (self.daily_start_balance - self.balance) / self.daily_start_balance * 100
                if daily_loss_pct >= self.config.max_daily_loss_percent:
                    self.trading_halted_today = True

            # Gérer position ouverte
            if self.open_trade_obj:
                if self.check_exit(self.open_trade_obj, row):
                    self.open_trade_obj = None

            # Chercher nouveau signal (seulement si pas de position et pas bloqué)
            if (not self.open_trade_obj
                and not self.trading_halted_today
                and self.consecutive_losses < self.config.max_consecutive_losses):
                
                signal = self.check_signal(row)
                if signal != 0:
                    self.open_trade(row, signal)
                    self.open_trade_obj = self.open_trade_obj  # already set

            # Mise à jour courbe d'équité
            current_equity = self.balance
            if self.open_trade_obj:
                price_diff = (row['Close'] - self.open_trade_obj.entry_price) * self.open_trade_obj.direction
                unrealized = price_diff * self.open_trade_obj.lot_size * 100000
                current_equity += unrealized
            
            self.equity_curve.append(current_equity)
            self.equity_times.append(idx)

        return self.compute_statistics()

    def compute_statistics(self) -> dict:
        """Calcule les statistiques de performance"""
        if not self.trades:
            return {
                'total_trades': 0,
                'final_balance': self.balance,
                'total_return_pct': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
            }

        profits = [t.profit for t in self.trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]

        total_profit = sum(wins) if wins else 0
        total_loss = abs(sum(losses)) if losses else 0

        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / running_max * 100
        max_dd = drawdowns.min()

        # Sharpe ratio approximatif (sans taux sans risque)
        returns = np.diff(equity_array) / equity_array[:-1]
        sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0

        return {
            'total_trades': len(self.trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'final_balance': round(self.balance, 2),
            'total_return_pct': round((self.balance / self.config.initial_capital - 1) * 100, 2),
            'win_rate': round(len(wins) / len(self.trades) * 100, 2),
            'profit_factor': round(total_profit / total_loss, 2) if total_loss > 0 else float('inf'),
            'avg_win': round(np.mean(wins), 2) if wins else 0,
            'avg_loss': round(np.mean(losses), 2) if losses else 0,
            'max_drawdown_pct': round(max_dd, 2),
            'sharpe_ratio': round(sharpe, 2),
            # Courbe d'équité pour le graphique UI (sous-échantillonnée à 500 pts max)
            'equity_curve': self._sample_equity_curve(),
        }

    def _sample_equity_curve(self):
        """Retourne la courbe d'équité en (datetime, valeur) pour le graphique UI"""
        from datetime import datetime, timedelta
        curve = self.equity_curve
        if not curve:
            return []
        # Sous-échantillonner si > 500 points
        step = max(1, len(curve) // 500)
        sampled = curve[::step]
        # Générer des timestamps synthétiques
        start = datetime.now() - timedelta(hours=len(sampled))
        result = [(start + timedelta(hours=i), v) for i, v in enumerate(sampled)]
        return result

    def plot_results(self, output_path: str = 'backtest_results.png'):
        """Génère un graphique des résultats"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Courbe d'équité
        ax1.plot(self.equity_curve, color='steelblue', linewidth=1.5)
        ax1.axhline(y=self.config.initial_capital, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title('Courbe d\'équité', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Barres')
        ax1.set_ylabel('Équité')
        ax1.grid(True, alpha=0.3)
        ax1.fill_between(range(len(self.equity_curve)),
                         self.config.initial_capital,
                         self.equity_curve,
                         where=[e >= self.config.initial_capital for e in self.equity_curve],
                         color='green', alpha=0.1)
        ax1.fill_between(range(len(self.equity_curve)),
                         self.config.initial_capital,
                         self.equity_curve,
                         where=[e < self.config.initial_capital for e in self.equity_curve],
                         color='red', alpha=0.1)

        # Drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / running_max * 100
        ax2.fill_between(range(len(drawdowns)), drawdowns, 0, color='red', alpha=0.3)
        ax2.plot(drawdowns, color='darkred', linewidth=1)
        ax2.set_title('Drawdown (%)', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Barres')
        ax2.set_ylabel('Drawdown %')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()
        return output_path


# ============================================================================
# MAIN
# ============================================================================

def download_data(symbol: str, start: str, end: str, interval: str = '1h') -> pd.DataFrame:
    """Télécharge les données historiques via yfinance"""
    print(f"Téléchargement des données {symbol} du {start} au {end}...")
    df = yf.download(symbol, start=start, end=end, interval=interval, progress=False)
    if df.empty:
        raise ValueError(f"Aucune donnée pour {symbol}")
    # Gestion du multi-index colonnes de yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    print(f"  → {len(df)} bougies téléchargées")
    return df


def print_results(stats: dict, config: StrategyConfig):
    print("\n" + "=" * 60)
    print("RÉSULTATS DU BACKTEST")
    print("=" * 60)
    print(f"Capital initial      : {config.initial_capital:>12,.2f}")
    print(f"Capital final        : {stats['final_balance']:>12,.2f}")
    print(f"Rendement total      : {stats['total_return_pct']:>12.2f} %")
    print(f"Drawdown maximum     : {stats['max_drawdown_pct']:>12.2f} %")
    print("-" * 60)
    print(f"Nombre total trades  : {stats['total_trades']:>12}")
    print(f"Trades gagnants      : {stats.get('winning_trades', 0):>12}")
    print(f"Trades perdants      : {stats.get('losing_trades', 0):>12}")
    print(f"Win rate             : {stats['win_rate']:>12.2f} %")
    print(f"Profit factor        : {stats['profit_factor']:>12.2f}")
    print(f"Gain moyen           : {stats.get('avg_win', 0):>12,.2f}")
    print(f"Perte moyenne        : {stats.get('avg_loss', 0):>12,.2f}")
    print(f"Sharpe ratio         : {stats['sharpe_ratio']:>12.2f}")
    print("=" * 60)

    print("\nCRITÈRES DE VALIDATION :")
    checks = [
        ('Profit factor > 1.3', stats['profit_factor'] > 1.3),
        ('Drawdown < 20%', abs(stats['max_drawdown_pct']) < 20),
        ('Au moins 50 trades', stats['total_trades'] >= 50),
        ('Rendement positif', stats['total_return_pct'] > 0),
        ('Sharpe > 0.5', stats['sharpe_ratio'] > 0.5),
    ]
    for label, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  [{status}] {label}")

    passed_count = sum(1 for _, p in checks if p)
    if passed_count == len(checks):
        print("\n→ Stratégie validée pour test en compte démo.")
    else:
        print(f"\n→ {passed_count}/{len(checks)} critères validés. NE PAS trader en réel.")


def main():
    parser = argparse.ArgumentParser(description='Backtester SafeTrendBot')
    parser.add_argument('--symbol', default='EURUSD=X', help='Symbole Yahoo Finance')
    parser.add_argument('--start', default='2020-01-01', help='Date de début')
    parser.add_argument('--end', default='2025-01-01', help='Date de fin')
    parser.add_argument('--interval', default='1h', help='Timeframe (1h, 4h, 1d)')
    parser.add_argument('--capital', type=float, default=10000, help='Capital initial')
    parser.add_argument('--risk', type=float, default=1.0, help='Risque par trade %')
    parser.add_argument('--plot', action='store_true', help='Générer un graphique')
    args = parser.parse_args()

    config = StrategyConfig(
        initial_capital=args.capital,
        risk_percent=args.risk,
    )

    df = download_data(args.symbol, args.start, args.end, args.interval)
    backtester = Backtester(config)
    stats = backtester.run(df)
    print_results(stats, config)

    if args.plot:
        path = backtester.plot_results()
        print(f"\nGraphique généré : {path}")


if __name__ == '__main__':
    main()
