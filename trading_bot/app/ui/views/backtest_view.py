"""
Vue Backtest - Lance un backtest et affiche les résultats
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox, QTextEdit, QLabel,
    QGroupBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS


class BacktestWorker(QThread):
    """Worker thread pour exécuter le backtest sans bloquer l'UI"""
    progress = pyqtSignal(str)
    finished_with_result = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, symbol, start, end, interval, capital, risk):
        super().__init__()
        self.symbol = symbol
        self.start = start
        self.end = end
        self.interval = interval
        self.capital = capital
        self.risk = risk

    def run(self):
        try:
            self.progress.emit("Téléchargement des données historiques...")
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            from backtest.backtest import Backtester, StrategyConfig, download_data

            df = download_data(self.symbol, self.start, self.end, self.interval)
            self.progress.emit(f"Données reçues ({len(df)} bougies). Exécution du backtest...")

            config = StrategyConfig(
                initial_capital=self.capital,
                risk_percent=self.risk,
            )
            bt = Backtester(config)
            stats = bt.run(df)
            stats['_equity_curve'] = bt.equity_curve
            self.finished_with_result.emit(stats)
        except Exception as e:
            self.failed.emit(str(e))


class BacktestView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Backtest de stratégie",
            "Valider la stratégie sur données historiques avant tout trading réel"
        ))

        # Panneau paramètres
        params_card = Card("Paramètres")
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.symbol_input = QLineEdit("EURUSD=X")
        form.addRow("Symbole :", self.symbol_input)

        self.start_date = QDateEdit(QDate.currentDate().addYears(-5))
        self.start_date.setCalendarPopup(True)
        form.addRow("Date début :", self.start_date)

        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        form.addRow("Date fin :", self.end_date)

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1h", "4h", "1d"])
        self.interval_combo.setCurrentText("1h")
        form.addRow("Timeframe :", self.interval_combo)

        self.capital_input = QDoubleSpinBox()
        self.capital_input.setRange(100, 10000000)
        self.capital_input.setValue(10000)
        self.capital_input.setSuffix(" €")
        form.addRow("Capital initial :", self.capital_input)

        self.risk_input = QDoubleSpinBox()
        self.risk_input.setRange(0.1, 5.0)
        self.risk_input.setValue(1.0)
        self.risk_input.setSingleStep(0.1)
        self.risk_input.setSuffix(" %")
        form.addRow("Risque par trade :", self.risk_input)

        params_card.add_layout(form)

        # Bouton de lancement
        btn_row = QHBoxLayout()
        self.run_button = QPushButton("▶ Lancer le backtest")
        self.run_button.setMinimumHeight(42)
        self.run_button.clicked.connect(self._run_backtest)
        btn_row.addWidget(self.run_button)
        btn_row.addStretch()
        params_card.add_layout(btn_row)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        params_card.add_widget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        params_card.add_widget(self.progress_bar)

        layout.addWidget(params_card)

        # Résultats
        self.results_card = Card("Résultats")
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlainText(
            "Aucun backtest exécuté pour le moment.\n\n"
            "Conseils :\n"
            "• Utilisez au moins 5 ans de données pour des résultats fiables\n"
            "• Timeframe H1 ou H4 recommandé pour cette stratégie\n"
            "• Un bon backtest affiche : profit factor > 1.3, drawdown < 20%, "
            "min 50 trades"
        )
        self.results_text.setFont(QFont("Consolas", 10))
        self.results_text.setMaximumHeight(260)
        self.results_card.add_widget(self.results_text)
        layout.addWidget(self.results_card)

        # Courbe d'équité du backtest
        from app.ui.equity_chart import EquityChartWidget
        chart_card = Card("📈 Courbe d'équité du backtest")
        self.bt_equity_chart = EquityChartWidget()
        self.bt_equity_chart.setMinimumHeight(280)
        chart_card.add_widget(self.bt_equity_chart)
        self._chart_card = chart_card
        chart_card.setVisible(False)
        layout.addWidget(chart_card)

        layout.addStretch()

    def _run_backtest(self):
        self.run_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Préparation...")

        self._worker = BacktestWorker(
            symbol=self.symbol_input.text(),
            start=self.start_date.date().toString("yyyy-MM-dd"),
            end=self.end_date.date().toString("yyyy-MM-dd"),
            interval=self.interval_combo.currentText(),
            capital=self.capital_input.value(),
            risk=self.risk_input.value(),
        )
        self._worker.progress.connect(self.progress_label.setText)
        self._worker.finished_with_result.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_finished(self, stats):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.run_button.setEnabled(True)

        report = self._format_report(stats)
        self.results_text.setPlainText(report)

        # Afficher la courbe d'équité si des données sont disponibles
        equity_curve = stats.get('equity_curve', [])
        if equity_curve and hasattr(self, 'bt_equity_chart'):
            initial = self.capital_input.value()
            self.bt_equity_chart.update_data(equity_curve, initial)
            self._chart_card.setVisible(True)

    def _on_failed(self, error):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.run_button.setEnabled(True)
        QMessageBox.warning(self, "Erreur", f"Backtest échoué :\n{error}")

    def _format_report(self, stats):
        lines = []
        lines.append("=" * 60)
        lines.append("RÉSULTATS DU BACKTEST")
        lines.append("=" * 60)
        lines.append(f"Capital final            : {stats.get('final_balance', 0):>12,.2f}")
        lines.append(f"Rendement total          : {stats.get('total_return_pct', 0):>12.2f} %")
        lines.append(f"Drawdown maximum         : {stats.get('max_drawdown_pct', 0):>12.2f} %")
        lines.append("-" * 60)
        lines.append(f"Nombre de trades         : {stats.get('total_trades', 0):>12}")
        lines.append(f"Trades gagnants          : {stats.get('winning_trades', 0):>12}")
        lines.append(f"Trades perdants          : {stats.get('losing_trades', 0):>12}")
        lines.append(f"Win rate                 : {stats.get('win_rate', 0):>12.2f} %")
        pf = stats.get('profit_factor', 0)
        pf_str = f"{pf:.2f}" if pf != float('inf') else '∞'
        lines.append(f"Profit factor            : {pf_str:>12}")
        lines.append(f"Sharpe ratio             : {stats.get('sharpe_ratio', 0):>12.2f}")
        lines.append("=" * 60)
        lines.append("")
        lines.append("CRITÈRES DE VALIDATION :")
        checks = [
            ('Profit factor > 1.3', stats.get('profit_factor', 0) > 1.3),
            ('Drawdown < 20%', abs(stats.get('max_drawdown_pct', 0)) < 20),
            ('Au moins 50 trades', stats.get('total_trades', 0) >= 50),
            ('Rendement positif', stats.get('total_return_pct', 0) > 0),
            ('Sharpe > 0.5', stats.get('sharpe_ratio', 0) > 0.5),
        ]
        for label, passed in checks:
            mark = "[✓]" if passed else "[✗]"
            lines.append(f"  {mark} {label}")

        passed_count = sum(1 for _, p in checks if p)
        lines.append("")
        if passed_count == len(checks):
            lines.append(f"→ Stratégie validée ({passed_count}/{len(checks)} critères)")
        else:
            lines.append(f"→ {passed_count}/{len(checks)} critères validés")

        return "\n".join(lines)

    def refresh(self):
        pass
