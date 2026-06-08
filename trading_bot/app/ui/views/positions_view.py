"""
Vue Positions - Positions ouvertes et historique des trades
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QTabWidget, QPushButton, QMessageBox, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class PositionsView(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Positions",
            "Positions ouvertes et historique des trades exécutés par le bot"
        ))

        # Tabs : ouvertes / historique
        tabs = QTabWidget()

        # Onglet positions ouvertes
        open_widget = QWidget()
        open_layout = QVBoxLayout(open_widget)
        open_layout.setContentsMargins(0, 12, 0, 0)

        # Toolbar
        toolbar = QHBoxLayout()
        self.open_count_label = QLabel("0 position ouverte")
        self.open_count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        toolbar.addWidget(self.open_count_label)
        toolbar.addStretch()

        refresh_btn = QPushButton("↻ Actualiser")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        close_all_btn = QPushButton("Fermer toutes les positions")
        close_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['error']};
                color: white;
            }}
            QPushButton:hover {{
                background-color: #dc2626;
            }}
        """)
        close_all_btn.clicked.connect(self._close_all_positions)
        toolbar.addWidget(close_all_btn)

        open_layout.addLayout(toolbar)

        # Table des positions ouvertes
        self.open_table = QTableWidget()
        self.open_table.setColumnCount(10)
        self.open_table.setHorizontalHeaderLabels([
            'Ticket', 'Symbole', 'Type', 'Volume', 'Prix entrée',
            'Prix actuel', 'SL', 'TP', 'Profit', 'Heure'
        ])
        self.open_table.setAlternatingRowColors(True)
        self.open_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.open_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.open_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.open_table.verticalHeader().setVisible(False)
        open_layout.addWidget(self.open_table)

        tabs.addTab(open_widget, "Positions ouvertes")

        # Onglet historique
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 12, 0, 0)

        history_toolbar = QHBoxLayout()
        self.history_count_label = QLabel("0 trade dans l'historique")
        self.history_count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        history_toolbar.addWidget(self.history_count_label)
        history_toolbar.addStretch()

        refresh_h_btn = QPushButton("↻ Actualiser")
        refresh_h_btn.clicked.connect(self._refresh_history)
        history_toolbar.addWidget(refresh_h_btn)

        history_layout.addLayout(history_toolbar)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            'Ticket', 'Date', 'Symbole', 'Type', 'Volume', 'Prix', 'Profit', 'Commentaire'
        ])
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        history_layout.addWidget(self.history_table)

        tabs.addTab(history_widget, "Historique (30j)")

        layout.addWidget(tabs)

    def refresh(self):
        """Rafraîchit les positions ouvertes"""
        if not MT5_AVAILABLE:
            return
        try:
            positions = mt5.positions_get()
            if positions is None:
                positions = []
            # Filtrer par magic
            positions = [p for p in positions
                        if p.magic == self.engine.config.strategy.magic_number]

            self.open_table.setRowCount(len(positions))
            for i, p in enumerate(positions):
                from datetime import datetime
                pos_type = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
                type_color = QColor(COLORS['success']) if pos_type == "BUY" else QColor(COLORS['error'])

                items = [
                    str(p.ticket),
                    p.symbol,
                    pos_type,
                    f"{p.volume:.2f}",
                    f"{p.price_open:.5f}",
                    f"{p.price_current:.5f}",
                    f"{p.sl:.5f}" if p.sl else "—",
                    f"{p.tp:.5f}" if p.tp else "—",
                    f"{p.profit:+.2f}",
                    datetime.fromtimestamp(p.time).strftime('%H:%M:%S'),
                ]
                for j, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    if j == 2:  # Type
                        item.setForeground(type_color)
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    if j == 8:  # Profit
                        profit_color = QColor(COLORS['success']) if p.profit >= 0 else QColor(COLORS['error'])
                        item.setForeground(profit_color)
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.open_table.setItem(i, j, item)

            self.open_count_label.setText(f"{len(positions)} position(s) ouverte(s)")
        except Exception as e:
            print(f"Erreur refresh positions : {e}")

    def _refresh_history(self):
        """Rafraîchit l'historique"""
        if not MT5_AVAILABLE:
            return
        try:
            from datetime import datetime, timedelta
            from_date = datetime.now() - timedelta(days=30)
            deals = mt5.history_deals_get(from_date, datetime.now())
            if deals is None:
                deals = []
            deals = [d for d in deals if d.magic == self.engine.config.strategy.magic_number]

            self.history_table.setRowCount(len(deals))
            for i, d in enumerate(deals):
                type_str = "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL"
                items = [
                    str(d.ticket),
                    datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M'),
                    d.symbol,
                    type_str,
                    f"{d.volume:.2f}",
                    f"{d.price:.5f}",
                    f"{d.profit:+.2f}",
                    d.comment or "—",
                ]
                for j, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    if j == 6:  # Profit
                        color = QColor(COLORS['success']) if d.profit >= 0 else QColor(COLORS['error'])
                        item.setForeground(color)
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                    self.history_table.setItem(i, j, item)

            self.history_count_label.setText(f"{len(deals)} trade(s) dans l'historique")
        except Exception as e:
            print(f"Erreur refresh historique : {e}")

    def _close_all_positions(self):
        """Ferme toutes les positions du bot"""
        reply = QMessageBox.question(
            self, "Fermer toutes les positions",
            "Voulez-vous vraiment fermer toutes les positions ouvertes par le bot ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if not MT5_AVAILABLE:
            return
        try:
            positions = mt5.positions_get()
            if not positions:
                return
            closed = 0
            for p in positions:
                if p.magic != self.engine.config.strategy.magic_number:
                    continue
                # Préparer ordre de clôture
                tick = mt5.symbol_info_tick(p.symbol)
                order_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask

                request = {
                    'action': mt5.TRADE_ACTION_DEAL,
                    'symbol': p.symbol,
                    'volume': p.volume,
                    'type': order_type,
                    'position': p.ticket,
                    'price': price,
                    'deviation': 20,
                    'magic': self.engine.config.strategy.magic_number,
                    'comment': 'Manual close',
                    'type_time': mt5.ORDER_TIME_GTC,
                    'type_filling': mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    closed += 1

            QMessageBox.information(self, "Fermeture", f"{closed} position(s) fermée(s)")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))
