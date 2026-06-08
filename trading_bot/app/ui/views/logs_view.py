"""
Vue Logs - Journal des événements du bot
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor, QColor
from datetime import datetime

from app.ui.widgets import PageHeader
from app.ui.theme import COLORS


class LogsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log_entries = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Journal d'événements",
            "Historique des actions du bot, signaux, ordres et erreurs"
        ))

        # Toolbar
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Niveau :"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["Tous", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self._rebuild_display)
        toolbar.addWidget(self.level_combo)

        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        toolbar.addWidget(self.auto_scroll)

        toolbar.addStretch()

        clear_btn = QPushButton("🗑 Effacer")
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)

        export_btn = QPushButton("💾 Exporter")
        export_btn.clicked.connect(self._export_logs)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # Zone de logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_secondary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self.log_text)

        self.count_label = QLabel("0 entrée")
        self.count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.count_label)

    @pyqtSlot(str, str)
    def add_log(self, level: str, message: str):
        """Ajoute une entrée de log (appelé par le moteur)"""
        entry = {
            'time': datetime.now(),
            'level': level.upper(),
            'message': message,
        }
        self._log_entries.append(entry)
        # Limiter à 5000 entrées en mémoire
        if len(self._log_entries) > 5000:
            self._log_entries = self._log_entries[-5000:]

        # Ajouter seulement si correspond au filtre actuel
        filter_level = self.level_combo.currentText()
        if filter_level == "Tous" or entry['level'] == filter_level:
            self._append_entry(entry)

        self.count_label.setText(f"{len(self._log_entries)} entrée(s)")

    def _append_entry(self, entry):
        level_colors = {
            'INFO': COLORS['text_primary'],
            'WARNING': COLORS['warning'],
            'ERROR': COLORS['error'],
            'DEBUG': COLORS['text_muted'],
        }
        color = level_colors.get(entry['level'], COLORS['text_primary'])
        time_str = entry['time'].strftime('%H:%M:%S')
        html = (f'<span style="color: {COLORS["text_muted"]};">{time_str}</span> '
                f'<span style="color: {color}; font-weight: bold;">[{entry["level"]}]</span> '
                f'<span style="color: {COLORS["text_primary"]};">{entry["message"]}</span>')

        self.log_text.append(html)

        if self.auto_scroll.isChecked():
            self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def _rebuild_display(self):
        """Reconstruit l'affichage avec le filtre actuel"""
        self.log_text.clear()
        filter_level = self.level_combo.currentText()
        for entry in self._log_entries:
            if filter_level == "Tous" or entry['level'] == filter_level:
                self._append_entry(entry)

    def _clear_logs(self):
        self._log_entries.clear()
        self.log_text.clear()
        self.count_label.setText("0 entrée")

    def _export_logs(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exporter les logs",
            f"safetrendbot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Texte (*.txt);;Tous les fichiers (*)"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for entry in self._log_entries:
                        f.write(f"{entry['time'].isoformat()} [{entry['level']}] "
                               f"{entry['message']}\n")
            except IOError as e:
                print(f"Erreur export : {e}")

    def refresh(self):
        pass
