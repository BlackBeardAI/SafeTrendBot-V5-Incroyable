"""
Vue Calendrier économique - Prochains événements à haut impact
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from datetime import datetime, timezone

from app.ui.widgets import PageHeader, Card, KPICard
from app.ui.theme import COLORS


class CalendarWorker(QThread):
    """Worker pour récupérer le calendrier sans bloquer l'UI"""
    finished_with_data = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self):
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            from bot.economic_calendar import EconomicCalendar
            cal = EconomicCalendar()
            events = cal.get_upcoming_high_impact(hours_ahead=7 * 24)
            self.finished_with_data.emit(events)
        except Exception as e:
            self.failed.emit(str(e))


class CalendarView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []
        self._worker = None
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Calendrier économique",
            "Événements à fort impact - Le bot s'abstient de trader ±30 min autour"
        ))

        # Toolbar
        toolbar = QHBoxLayout()
        self.count_label = QLabel("Chargement...")
        self.count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Tous", "Prochaines 24h", "Prochaines 48h", "Cette semaine"])
        self.filter_combo.currentTextChanged.connect(self._update_display)
        toolbar.addWidget(QLabel("Filtre :"))
        toolbar.addWidget(self.filter_combo)

        refresh_btn = QPushButton("↻ Actualiser")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Dans', 'Date / Heure (UTC)', 'Pays', 'Événement', 'Prévision', 'Précédent'
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def refresh(self):
        self.count_label.setText("Chargement...")
        self._worker = CalendarWorker()
        self._worker.finished_with_data.connect(self._on_data)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_data(self, events):
        self._events = events
        self._update_display()

    def _on_failed(self, error):
        self.count_label.setText(f"Erreur : {error}")

    def _update_display(self):
        # Filtrer
        filter_text = self.filter_combo.currentText()
        now = datetime.now(timezone.utc)
        filtered = self._events

        if filter_text == "Prochaines 24h":
            filtered = [e for e in self._events
                       if 0 <= (e.time - now).total_seconds() <= 86400]
        elif filter_text == "Prochaines 48h":
            filtered = [e for e in self._events
                       if 0 <= (e.time - now).total_seconds() <= 172800]
        elif filter_text == "Cette semaine":
            filtered = [e for e in self._events
                       if 0 <= (e.time - now).total_seconds() <= 604800]

        self.count_label.setText(f"{len(filtered)} événement(s) affiché(s)")
        self.table.setRowCount(len(filtered))

        for i, event in enumerate(filtered):
            delta = event.time - now
            total_seconds = delta.total_seconds()
            if total_seconds < 0:
                time_until = "Passé"
                color = COLORS['text_muted']
            elif total_seconds < 3600:
                time_until = f"< 1h"
                color = COLORS['error']
            elif total_seconds < 86400:
                hours = int(total_seconds / 3600)
                time_until = f"{hours}h"
                color = COLORS['warning']
            else:
                days = int(total_seconds / 86400)
                time_until = f"{days}j"
                color = COLORS['text_primary']

            items = [
                time_until,
                event.time.strftime('%Y-%m-%d %H:%M'),
                event.country,
                event.title,
                event.forecast or "—",
                event.previous or "—",
            ]

            for j, text in enumerate(items):
                item = QTableWidgetItem(text)
                if j == 0:
                    item.setForeground(QColor(color))
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                if j == 2:  # Pays
                    item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.table.setItem(i, j, item)
