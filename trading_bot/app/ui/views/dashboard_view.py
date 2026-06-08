"""
Vue Dashboard - Vue d'ensemble du bot et des performances
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.ui.widgets import KPICard, Card, PageHeader
from app.ui.theme import COLORS
from app.core.trading_engine import BotState


class DashboardView(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()

    def _build(self):
        # Scroll area pour supporter les petits écrans
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # Header
        layout.addWidget(PageHeader(
            "Tableau de bord",
            "Vue d'ensemble du bot et des performances"
        ))

        # Ligne 1 : État du bot
        status_row = QHBoxLayout()
        status_row.setSpacing(16)

        self.state_card = KPICard("État", "Arrêté", "En attente")
        self.symbols_card = KPICard("Symboles actifs", "0", "Aucun symbole")
        self.positions_card = KPICard("Positions ouvertes", "0", "")
        self.today_trades_card = KPICard("Trades aujourd'hui", "0", "")

        status_row.addWidget(self.state_card)
        status_row.addWidget(self.symbols_card)
        status_row.addWidget(self.positions_card)
        status_row.addWidget(self.today_trades_card)
        layout.addLayout(status_row)

        # Ligne 2 : Compte
        account_row = QHBoxLayout()
        account_row.setSpacing(16)

        self.balance_card = KPICard("Balance", "—", "")
        self.equity_card = KPICard("Équité", "—", "")
        self.profit_card = KPICard("P&L ouvert", "—", "")
        self.today_pnl_card = KPICard("P&L du jour", "—", "")

        account_row.addWidget(self.balance_card)
        account_row.addWidget(self.equity_card)
        account_row.addWidget(self.profit_card)
        account_row.addWidget(self.today_pnl_card)
        layout.addLayout(account_row)

        # Ligne 3 : Infos compte détaillées
        info_card = Card("Informations du compte")
        info_grid = QGridLayout()
        info_grid.setSpacing(12)

        labels = [
            ('Serveur', 'server_label'),
            ('Compte', 'account_name_label'),
            ('Levier', 'leverage_label'),
            ('Marge utilisée', 'margin_used_label'),
            ('Marge libre', 'margin_free_label'),
            ('Niveau de marge', 'margin_level_label'),
        ]
        for i, (label, attr) in enumerate(labels):
            row = i // 3
            col = (i % 3) * 2
            l = QLabel(label + " :")
            l.setStyleSheet(f"color: {COLORS['text_secondary']};")
            v = QLabel("—")
            v.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            info_grid.addWidget(l, row, col)
            info_grid.addWidget(v, row, col + 1)
            setattr(self, attr, v)

        info_card.add_layout(info_grid)
        layout.addWidget(info_card)

        # Graphique d'équité temps réel
        from app.ui.equity_chart import EquityChartWidget
        equity_chart_card = Card("📈 Courbe d'équité")
        self.equity_chart = EquityChartWidget()
        equity_chart_card.add_widget(self.equity_chart)
        layout.addWidget(equity_chart_card)

        # Panneau de diagnostic - pourquoi le bot ne trade pas
        from app.ui.widgets_status import TradingStatusPanel
        self.diagnostic_panel = TradingStatusPanel(engine=self.engine)
        layout.addWidget(self.diagnostic_panel)

        # Moniteur de signaux temps réel
        from app.ui.signal_monitor import SignalMonitorWidget
        self.signal_monitor = SignalMonitorWidget(engine=self.engine)
        layout.addWidget(self.signal_monitor)

        # Ligne 4 : Avertissements
        warning_card = Card("Indicateurs de santé")
        self.warnings_layout = QVBoxLayout()
        self.warnings_layout.setSpacing(8)
        self.warnings_label = QLabel("Tout va bien ✓")
        self.warnings_label.setStyleSheet(f"color: {COLORS['success']};")
        self.warnings_layout.addWidget(self.warnings_label)
        warning_card.add_layout(self.warnings_layout)
        layout.addWidget(warning_card)

        layout.addStretch()

    def update_status(self, status):
        # État du bot
        state_texts = {
            BotState.STOPPED: ("Arrêté", "#6c757d"),
            BotState.STARTING: ("Démarrage", "#f59e0b"),
            BotState.RUNNING: ("Actif", "#10b981"),
            BotState.PAUSED: ("En pause", "#f59e0b"),
            BotState.ERROR: ("Erreur", "#ef4444"),
        }
        text, color = state_texts.get(status.state, ("—", COLORS['text_primary']))
        self.state_card.set_value(text, color)

        self.symbols_card.set_value(str(len(status.active_symbols)))
        if status.active_symbols:
            self.symbols_card.set_subtitle(", ".join(status.active_symbols[:3]))

        self.positions_card.set_value(str(status.open_positions))
        self.today_trades_card.set_value(str(status.today_trades))

        pnl_color = COLORS['success'] if status.today_pnl >= 0 else COLORS['error']
        self.today_pnl_card.set_value(f"{status.today_pnl:+,.2f}", pnl_color)

        # Warnings
        self._update_warnings(status)

    def update_account(self, info):
        currency = info.get('currency', '')
        equity = info.get('equity', 0)
        balance = info.get('balance', 0)

        self.balance_card.set_value(f"{balance:,.2f} {currency}")
        self.equity_card.set_value(f"{equity:,.2f} {currency}")

        profit = info.get('profit', 0)
        profit_color = COLORS['success'] if profit >= 0 else COLORS['error']
        self.profit_card.set_value(f"{profit:+,.2f} {currency}", profit_color)

        self.server_label.setText(info.get('server', '—'))
        self.account_name_label.setText(info.get('name', '—'))
        self.leverage_label.setText(f"1:{info.get('leverage', '—')}")
        self.margin_used_label.setText(f"{info.get('margin', 0):,.2f}")
        self.margin_free_label.setText(f"{info.get('margin_free', 0):,.2f}")
        level = info.get('margin_level', 0)
        self.margin_level_label.setText(f"{level:.0f} %" if level > 0 else "—")

        # Mettre à jour le graphique d'équité
        if equity > 0 and hasattr(self, 'equity_chart'):
            from datetime import datetime
            if not hasattr(self, '_equity_history'):
                self._equity_history = []
            # Ajouter un point toutes les 30s max
            now = datetime.now()
            if not self._equity_history or (now - self._equity_history[-1][0]).seconds >= 30:
                self._equity_history.append((now, equity))
                if len(self._equity_history) > 500:
                    self._equity_history = self._equity_history[-500:]
                initial = info.get('initial_capital', self._equity_history[0][1])
                self.equity_chart.update_data(self._equity_history, initial)

    def _update_warnings(self, status):
        # Nettoyer les anciens
        while self.warnings_layout.count():
            item = self.warnings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        warnings = []
        if status.consecutive_losses >= 2:
            warnings.append((f"⚠️ {status.consecutive_losses} pertes consécutives",
                           COLORS['warning']))
        if status.state == BotState.ERROR:
            warnings.append(("🚨 Bot en état d'erreur", COLORS['error']))

        if not warnings:
            label = QLabel("✓ Tout va bien")
            label.setStyleSheet(f"color: {COLORS['success']};")
            self.warnings_layout.addWidget(label)
        else:
            for text, color in warnings:
                label = QLabel(text)
                label.setStyleSheet(f"color: {color};")
                self.warnings_layout.addWidget(label)

    def refresh(self):
        """Appelé périodiquement par le parent"""
        pass
