"""
Vue Paper Trading - Gestion du mode simulation
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QGroupBox, QFormLayout, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from app.ui.widgets import PageHeader, Card, KPICard
from app.ui.theme import COLORS
import logging

logger = logging.getLogger("paper_trading_view")


class PaperTradingView(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Paper Trading",
            "Mode simulation — trade avec les vraies données de marché sans risque réel"
        ))

        # Mode actuel
        mode_card = Card("Mode actuel")
        mode_layout = QHBoxLayout()

        self.mode_label = QLabel("Mode : LIVE")
        self.mode_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        mode_layout.addWidget(self.mode_label)
        mode_layout.addStretch()

        self.switch_btn = QPushButton("→ Basculer en mode PAPER")
        self.switch_btn.setMinimumHeight(40)
        self.switch_btn.clicked.connect(self._switch_mode)
        mode_layout.addWidget(self.switch_btn)

        mode_card.add_layout(mode_layout)

        info = QLabel(
            "⚠️ Le changement de mode nécessite que le bot soit arrêté.\n"
            "En mode PAPER : les trades sont simulés, aucun ordre n'est envoyé au broker.\n"
            "Utile pour tester de nouveaux paramètres ou s'entraîner."
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.setWordWrap(True)
        mode_card.add_widget(info)

        layout.addWidget(mode_card)

        # KPI paper
        kpi_row = QHBoxLayout()
        self.balance_kpi = KPICard("Balance virtuelle", "—")
        self.equity_kpi = KPICard("Équité virtuelle", "—")
        self.return_kpi = KPICard("Rendement", "—")
        self.trades_kpi = KPICard("Trades simulés", "—")
        kpi_row.addWidget(self.balance_kpi)
        kpi_row.addWidget(self.equity_kpi)
        kpi_row.addWidget(self.return_kpi)
        kpi_row.addWidget(self.trades_kpi)
        layout.addLayout(kpi_row)

        # Config initial capital
        config_card = Card("Configuration du compte paper")
        config_form = QFormLayout()
        self.initial_balance_spin = QDoubleSpinBox()
        self.initial_balance_spin.setRange(100, 10000000)
        self.initial_balance_spin.setValue(10000)
        self.initial_balance_spin.setSuffix(" EUR")
        config_form.addRow("Capital de départ :", self.initial_balance_spin)

        config_buttons = QHBoxLayout()
        reset_btn = QPushButton("🔄 Réinitialiser le compte paper")
        reset_btn.clicked.connect(self._reset_paper)
        reset_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['warning']}; color: white; }}
            QPushButton:hover {{ background-color: #d97706; }}
        """)
        config_buttons.addWidget(reset_btn)
        config_buttons.addStretch()

        config_card.add_layout(config_form)
        config_card.add_layout(config_buttons)
        layout.addWidget(config_card)

        # Trades ouverts paper
        self.open_trades_table = QTableWidget()
        self.open_trades_table.setColumnCount(8)
        self.open_trades_table.setHorizontalHeaderLabels([
            'Ticket', 'Symbole', 'Direction', 'Volume',
            'Entrée', 'SL', 'TP', 'P&L estimé'
        ])
        self.open_trades_table.setAlternatingRowColors(True)
        self.open_trades_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.open_trades_table.verticalHeader().setVisible(False)

        trades_card = Card("Positions ouvertes (paper)")
        trades_card.add_widget(self.open_trades_table)
        layout.addWidget(trades_card)

        # Historique trades fermés
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            'Symbole', 'Direction', 'Volume', 'Entrée', 'Sortie', 'P&L', 'Résultat'
        ])
        self.history_table.setAlternatingRowColors(True)
        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.history_table.verticalHeader().setVisible(False)

        history_card = Card("Historique des trades fermés (paper)")
        history_card.add_widget(self.history_table)
        layout.addWidget(history_card)

        self.refresh()

    def _switch_mode(self):
        current = self.engine.mode
        new_mode = "paper" if current == "live" else "live"
        if self.engine.set_mode(new_mode):
            self.refresh()
        else:
            QMessageBox.warning(self, "Impossible",
                               "Arrêtez le bot avant de changer de mode.")

    def _reset_paper(self):
        reply = QMessageBox.question(
            self, "Réinitialiser",
            "Remettre le compte paper à zéro ?\n"
            "Tous les trades simulés seront effacés.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            new_balance = self.initial_balance_spin.value()
            self.engine.paper_engine.account.initial_balance = new_balance
            self.engine.paper_engine.reset()
            self.refresh()
            QMessageBox.information(self, "Reset", "Compte paper réinitialisé.")

    def refresh(self):
        # Mode label
        current_mode = self.engine.mode
        if current_mode == "live":
            self.mode_label.setText("Mode : LIVE")
            self.mode_label.setStyleSheet(f"color: {COLORS['error']};")
            self.switch_btn.setText("→ Basculer en mode PAPER")
        else:
            self.mode_label.setText("Mode : PAPER (simulation)")
            self.mode_label.setStyleSheet(f"color: {COLORS['warning']};")
            self.switch_btn.setText("→ Basculer en mode LIVE")

        try:
            pe = self.engine.paper_engine
            stats = pe.get_stats()
            currency = pe.account.currency

            self.balance_kpi.set_value(f"{stats['balance']:,.2f} {currency}")
            self.equity_kpi.set_value(f"{stats['equity']:,.2f} {currency}")
            ret = stats.get('return_pct', 0)
            color = COLORS['success'] if ret >= 0 else COLORS['error']
            self.return_kpi.set_value(f"{ret:+.2f}%", color)
            self.trades_kpi.set_value(str(stats['total_trades']))

            # Trades ouverts
            trades = list(pe.open_trades.values())
            self.open_trades_table.setRowCount(len(trades))
            for i, t in enumerate(trades):
                # P&L estimé
                pnl = t.unrealized_pnl if hasattr(t, 'unrealized_pnl') else 0.0
                pnl_str = f"{pnl:+.2f}" if pnl != 0 else "—"
                items = [
                    str(t.ticket), t.symbol,
                    "BUY" if t.direction == 1 else "SELL",
                    f"{t.volume:.2f}", f"{t.entry_price:.5f}",
                    f"{t.stop_loss:.5f}", f"{t.take_profit:.5f}",
                    pnl_str,
                ]
                for j, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    if j == 2:  # Direction
                        clr = QColor(COLORS['success'] if t.direction == 1
                                     else COLORS['error'])
                        item.setForeground(clr)
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    elif j == 7 and pnl != 0:  # P&L
                        clr = QColor(COLORS['success'] if pnl >= 0 else COLORS['error'])
                        item.setForeground(clr)
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.open_trades_table.setItem(i, j, item)

            # Historique trades fermés
            closed = pe.closed_trades if hasattr(pe, 'closed_trades') else []
            self.history_table.setRowCount(len(closed))
            for i, t in enumerate(reversed(closed)):  # Plus récent en haut
                pnl = getattr(t, 'profit', 0) or 0
                items = [
                    getattr(t, 'symbol', ''),
                    "BUY" if getattr(t, 'direction', 1) == 1 else "SELL",
                    f"{getattr(t, 'volume', 0):.2f}",
                    f"{getattr(t, 'entry_price', 0):.5f}",
                    f"{getattr(t, 'exit_price', 0):.5f}",
                    f"{pnl:+.2f} {currency}",
                    "✓ Gain" if pnl >= 0 else "✗ Perte",
                ]
                for j, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    if j in (1, 5, 6):
                        is_positive = (j == 1 and getattr(t, 'direction', 1) == 1) or (
                            j in (5, 6) and pnl >= 0)
                        clr = QColor(COLORS['success'] if is_positive else COLORS['error'])
                        item.setForeground(clr)
                        if j == 6:
                            item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.history_table.setItem(i, j, item)

        except Exception as e:
            logger.warning(f"Erreur refresh paper : {e}")
