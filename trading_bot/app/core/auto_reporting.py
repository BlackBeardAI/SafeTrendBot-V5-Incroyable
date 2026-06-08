"""
Reporting automatique hebdomadaire — envoie email + Telegram avec PDF.
"""
import json
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class WeeklyReport:
    week_start: str
    week_end: str
    total_trades: int
    win_rate: float
    net_pnl: float
    max_drawdown: float
    sharpe: float
    best_trade: float
    worst_trade: float
    avg_trade: float
    profit_factor: float
    regime_breakdown: Dict[str, int]
    top_symbol: str
    worst_symbol: str


class AutoReporting:
    """
    Génère et envoie des rapports hebdomadaires automatiques.
    """

    def __init__(self, engine, telegram_alerts=None, email_config=None):
        self.engine = engine
        self.telegram = telegram_alerts
        self.email_config = email_config
        self._last_report_date: Optional[datetime] = None
        self._report_file = Path(__file__).parent / '..' / '..' / 'data' / 'weekly_reports'
        self._report_file.mkdir(parents=True, exist_ok=True)

    def should_generate(self) -> bool:
        """Vrai si dimanche et pas encore envoyé cette semaine"""
        now = datetime.now()
        if now.weekday() != 6:  # Dimanche
            return False
        if self._last_report_date and self._last_report_date.date() == now.date():
            return False
        return True

    def generate(self) -> WeeklyReport:
        """Génère le rapport de la semaine"""
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday() + 1)
        week_end = now

        # Récupérer les trades de la semaine
        all_trades = self.engine.journal.get_all(only_closed=True)
        week_trades = [
            t for t in all_trades
            if t.exit_time and week_start.date() <= t.exit_time.date() <= week_end.date()
        ]

        if not week_trades:
            return WeeklyReport(
                week_start=week_start.strftime('%Y-%m-%d'),
                week_end=week_end.strftime('%Y-%m-%d'),
                total_trades=0, win_rate=0, net_pnl=0, max_drawdown=0,
                sharpe=0, best_trade=0, worst_trade=0, avg_trade=0,
                profit_factor=0, regime_breakdown={},
                top_symbol='', worst_symbol='',
            )

        profits = [t.profit for t in week_trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]

        # Par symbole
        by_symbol = {}
        for t in week_trades:
            by_symbol[t.symbol] = by_symbol.get(t.symbol, 0) + t.profit
        top_symbol = max(by_symbol.items(), key=lambda x: x[1]) if by_symbol else ('', 0)
        worst_symbol = min(by_symbol.items(), key=lambda x: x[1]) if by_symbol else ('', 0)

        # Par régime
        regimes = {}
        for t in week_trades:
            reg = t.indicators.get('regime', 'unknown') if hasattr(t, 'indicators') else 'unknown'
            regimes[reg] = regimes.get(reg, 0) + 1

        return WeeklyReport(
            week_start=week_start.strftime('%Y-%m-%d'),
            week_end=week_end.strftime('%Y-%m-%d'),
            total_trades=len(week_trades),
            win_rate=round(len(wins) / len(profits) * 100, 1),
            net_pnl=round(sum(profits), 2),
            max_drawdown=round(self.engine.performance_tracker._max_drawdown, 1),
            sharpe=round(self.engine.performance_tracker.get_metrics(0,0).sharpe, 2),
            best_trade=round(max(profits), 2),
            worst_trade=round(min(profits), 2),
            avg_trade=round(sum(profits) / len(profits), 2),
            profit_factor=round(abs(sum(wins) / sum(losses)), 2) if losses and sum(losses) != 0 else 999,
            regime_breakdown=regimes,
            top_symbol=f"{top_symbol[0]} (+{top_symbol[1]:.2f})",
            worst_symbol=f"{worst_symbol[0]} ({worst_symbol[1]:.2f})",
        )

    def send(self, report: WeeklyReport):
        """Envoie le rapport via Telegram et/ou email"""
        msg = self._format_telegram(report)
        if self.telegram:
            try:
                self.telegram.send(msg)
            except Exception as e:
                print(f"[REPORT] Erreur Telegram: {e}")

        # Sauvegarder localement
        filename = self._report_file / f"report_{report.week_end}.json"
        filename.write_text(json.dumps({
            'week_start': report.week_start, 'week_end': report.week_end,
            'total_trades': report.total_trades, 'win_rate': report.win_rate,
            'net_pnl': report.net_pnl, 'sharpe': report.sharpe,
            'profit_factor': report.profit_factor,
        }, indent=2))
        print(f"[REPORT] Rapport sauvegardé: {filename}")

    def _format_telegram(self, report: WeeklyReport) -> str:
        return (f"*📊 Rapport Hebdomadaire*\n"
                f"{report.week_start} → {report.week_end}\n\n"
                f"Trades: {report.total_trades}\n"
                f"Win Rate: {report.win_rate}%\n"
                f"P&L Net: {report.net_pnl:+.2f}\n"
                f"Max DD: {report.max_drawdown}%\n"
                f"Sharpe: {report.sharpe}\n"
                f"PF: {report.profit_factor}\n"
                f"Best: {report.best_trade:+.2f}\n"
                f"Worst: {report.worst_trade:+.2f}\n\n"
                f"🏆 {report.top_symbol}\n"
                f"💀 {report.worst_symbol}")

    def check_and_send(self):
        if self.should_generate():
            report = self.generate()
            self.send(report)
            self._last_report_date = datetime.now()
            return True
        return False
