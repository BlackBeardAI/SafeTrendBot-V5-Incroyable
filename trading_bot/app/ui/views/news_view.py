"""
Vue Actualités - Flux RSS de sources financières légitimes
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QPushButton, QLineEdit, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QCursor
from datetime import datetime, timezone

from app.ui.widgets import PageHeader
from app.ui.theme import COLORS


class NewsWorker(QThread):
    """Worker pour récupérer les news"""
    finished_with_data = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self):
        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            from bot.news_feed import NewsFeed
            feed = NewsFeed()
            articles = feed.fetch_all(max_per_source=8)
            self.finished_with_data.emit(articles)
        except Exception as e:
            self.failed.emit(str(e))


class NewsCard(QFrame):
    """Carte cliquable pour un article"""
    def __init__(self, article, parent=None):
        super().__init__(parent)
        self.article = article
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setStyleSheet(f"""
            NewsCard {{
                background-color: {COLORS['card_bg']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                border-left: 3px solid {COLORS['accent']};
            }}
            NewsCard:hover {{
                background-color: {COLORS['hover']};
                border-left: 3px solid {COLORS['accent_hover']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Header : source + date
        header = QHBoxLayout()
        source = QLabel(article.source)
        source.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        source.setStyleSheet(f"color: {COLORS['accent']};")

        age = datetime.now(timezone.utc) - article.published
        if age.total_seconds() < 3600:
            age_str = f"il y a {int(age.total_seconds() / 60)} min"
        elif age.total_seconds() < 86400:
            age_str = f"il y a {int(age.total_seconds() / 3600)}h"
        else:
            age_str = f"il y a {age.days}j"

        age_label = QLabel(age_str)
        age_label.setFont(QFont("Segoe UI", 8))
        age_label.setStyleSheet(f"color: {COLORS['text_muted']};")

        header.addWidget(source)
        header.addStretch()
        header.addWidget(age_label)
        layout.addLayout(header)

        # Titre
        title = QLabel(article.title)
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Résumé
        if article.summary:
            summary = QLabel(article.summary[:200] + "...")
            summary.setFont(QFont("Segoe UI", 9))
            summary.setStyleSheet(f"color: {COLORS['text_secondary']};")
            summary.setWordWrap(True)
            layout.addWidget(summary)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            QDesktopServices.openUrl(QUrl(self.article.link))


class NewsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._articles = []
        self._worker = None
        self._build()
        self.refresh()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Actualités financières",
            "Flux RSS de sources légitimes - Pour lecture humaine uniquement"
        ))

        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher dans les actualités...")
        self.search_input.setMinimumHeight(36)
        self.search_input.textChanged.connect(self._update_display)
        toolbar.addWidget(self.search_input)

        self.source_filter = QComboBox()
        self.source_filter.setMinimumHeight(36)
        self.source_filter.addItem("Toutes les sources")
        self.source_filter.currentTextChanged.connect(self._update_display)
        toolbar.addWidget(self.source_filter)

        refresh_btn = QPushButton("↻ Actualiser")
        refresh_btn.setMinimumHeight(36)
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        self.count_label = QLabel("Chargement...")
        self.count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self.count_label)

        # Zone de scroll pour les cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

    def refresh(self):
        self.count_label.setText("Chargement...")
        self._worker = NewsWorker()
        self._worker.finished_with_data.connect(self._on_data)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_data(self, articles):
        self._articles = articles

        # Remplir les sources
        sources = sorted(set(a.source for a in articles))
        current = self.source_filter.currentText()
        self.source_filter.clear()
        self.source_filter.addItem("Toutes les sources")
        self.source_filter.addItems(sources)
        if current in sources:
            self.source_filter.setCurrentText(current)

        self._update_display()

    def _on_failed(self, error):
        self.count_label.setText(f"Erreur : {error}")

    def _update_display(self):
        # Nettoyer les cards existantes
        while self.cards_layout.count() > 1:  # Garder le stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Filtrer
        search = self.search_input.text().lower()
        source_filter = self.source_filter.currentText()

        filtered = self._articles
        if search:
            filtered = [a for a in filtered
                       if search in a.title.lower() or search in a.summary.lower()]
        if source_filter != "Toutes les sources":
            filtered = [a for a in filtered if a.source == source_filter]

        self.count_label.setText(f"{len(filtered)} article(s)")

        # Ajouter les cards
        for article in filtered[:100]:
            card = NewsCard(article)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
