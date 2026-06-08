"""
Vue Watchlist — surveille des symboles et déclenche des alertes de prix.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QScrollArea, QComboBox, QDoubleSpinBox, QLineEdit,
    QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS


POPULAR_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "NZDUSD", "USDCHF", "EURJPY", "GBPJPY", "XAUUSD",
    "BTCUSD", "ETHUSD", "SP500", "NASDAQ",
]


class AddAlertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter une alerte de prix")
        self.setMinimumWidth(380)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()

        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        for s in POPULAR_SYMBOLS:
            self.symbol_combo.addItem(s)
        form.addRow("Symbole :", self.symbol_combo)

        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Prix monte au-dessus de", "Prix descend en-dessous de"])
        form.addRow("Condition :", self.direction_combo)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 9999999)
        self.price_spin.setDecimals(5)
        self.price_spin.setSingleStep(0.0001)
        form.addRow("Prix seuil :", self.price_spin)

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Note optionnelle...")
        form.addRow("Note :", self.note_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {
            'symbol': self.symbol_combo.currentText().strip().upper(),
            'above': self.direction_combo.currentIndex() == 0,
            'price': self.price_spin.value(),
            'note': self.note_edit.text().strip(),
        }


class WatchlistView(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._alerts = []   # list of dicts
        self._build()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_alerts)
        self.timer.start(15_000)  # vérification toutes les 15s

    def _build(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        main.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Watchlist",
            "Surveillez des prix et recevez des alertes"
        ))

        # Boutons
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Ajouter une alerte")
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(self._add_alert)
        btn_row.addWidget(add_btn)

        del_btn = QPushButton("Supprimer sélection")
        del_btn.setMinimumHeight(36)
        del_btn.clicked.connect(self._delete_alert)
        del_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS.get('error','#ef4444')}; }}"
        )
        btn_row.addWidget(del_btn)
        btn_row.addStretch()

        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.refresh_btn.setMinimumHeight(36)
        self.refresh_btn.clicked.connect(self._check_alerts)
        btn_row.addWidget(self.refresh_btn)

        layout.addLayout(btn_row)

        # Table des alertes
        alert_card = Card("Alertes de prix")

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Symbole', 'Condition', 'Seuil', 'Prix actuel', 'Statut', 'Note'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(250)
        alert_card.add_widget(self.table)
        layout.addWidget(alert_card)

        # Explication
        info_card = Card("💡 Comment utiliser")
        info = QLabel(
            "Ajoutez des alertes pour surveiller des niveaux de prix importants.\n\n"
            "• Prix monte au-dessus de X : déclenche quand le prix dépasse le seuil\n"
            "• Prix descend en-dessous de X : déclenche quand le prix passe sous le seuil\n\n"
            "Les alertes sont vérifiées toutes les 15 secondes.\n"
            "Si Telegram est configuré, vous recevrez une notification."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS.get('text_secondary','#94a3b8')};")
        info_card.add_widget(info)
        layout.addWidget(info_card)

        layout.addStretch()

    def _add_alert(self):
        dlg = AddAlertDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        v = dlg.get_values()
        if not v['symbol']:
            return
        if v['price'] <= 0:
            QMessageBox.warning(self, "Prix invalide", "Le prix seuil doit être positif.")
            return

        self._alerts.append({
            'symbol': v['symbol'],
            'above': v['above'],
            'price': v['price'],
            'note': v['note'],
            'current': None,
            'triggered': False,
        })
        self._refresh_table()

    def _delete_alert(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._alerts):
            return
        del self._alerts[row]
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(len(self._alerts))
        for i, a in enumerate(self._alerts):
            condition = (f"↑ Monte au-dessus de {a['price']:.5f}"
                         if a['above'] else
                         f"↓ Descend sous {a['price']:.5f}")
            current_str = f"{a['current']:.5f}" if a['current'] else "—"
            status = "✅ Déclenché" if a['triggered'] else "⏳ En attente"
            status_color = (COLORS.get('success', '#10b981') if a['triggered']
                            else COLORS.get('text_secondary', '#94a3b8'))

            row_data = [a['symbol'], condition, f"{a['price']:.5f}",
                        current_str, status, a['note']]
            for j, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                if j == 4:
                    item.setForeground(QColor(status_color))
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table.setItem(i, j, item)

    def _check_alerts(self):
        """Vérifie chaque alerte et récupère le prix actuel"""
        if not self._alerts:
            return

        for alert in self._alerts:
            if alert['triggered']:
                continue
            price = self._get_price(alert['symbol'])
            if price is None:
                continue
            alert['current'] = price

            triggered = (alert['above'] and price >= alert['price']) or \
                        (not alert['above'] and price <= alert['price'])

            if triggered and not alert['triggered']:
                alert['triggered'] = True
                self._on_alert_triggered(alert)

        self._refresh_table()

    def _get_price(self, symbol: str):
        """Récupère le prix depuis le broker ou yfinance"""
        if (self.engine and hasattr(self.engine, 'broker')
                and self.engine.broker and self.engine.broker.is_connected()):
            try:
                tick = self.engine.broker.get_tick(symbol)
                if tick:
                    return (tick.bid + tick.ask) / 2
            except Exception:
                pass
        # Fallback via yfinance
        try:
            import yfinance as yf
            from app.core.historical_data import _to_yfinance_symbol
            sym = _to_yfinance_symbol(symbol)
            data = yf.Ticker(sym).history(period="1d", interval="1m")
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception:
            pass
        return None

    def _on_alert_triggered(self, alert: dict):
        """Notification quand une alerte est déclenchée"""
        direction = "au-dessus de" if alert['above'] else "en-dessous de"
        msg = (f"🔔 Alerte {alert['symbol']}\n"
               f"Le prix est passé {direction} {alert['price']:.5f}\n"
               f"Prix actuel : {alert['current']:.5f}")

        # Notification dans l'app
        QMessageBox.information(self, f"Alerte {alert['symbol']}", msg)

        # Notification Telegram si disponible
        if self.engine and hasattr(self.engine, '_telegram_alerts'):
            try:
                if self.engine._telegram_alerts:
                    self.engine._telegram_alerts.send(msg)
            except Exception:
                pass
