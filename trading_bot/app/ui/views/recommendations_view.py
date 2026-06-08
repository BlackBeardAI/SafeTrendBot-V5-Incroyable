"""
Vue Recommandations.
Affiche des conseils contextuels basés sur l'état réel du bot,
les performances, la configuration et les conditions de marché.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader
from app.ui.theme import COLORS
from app.core.recommendations import (
    RecommendationEngine, Recommendation,
    RecommendationPriority, RecommendationCategory,
)


def c(k, d='#888'):
    return COLORS.get(k, d)


# Couleurs et icônes par priorité
PRIORITY_STYLE = {
    RecommendationPriority.CRITICAL: {
        'border': '#ef4444',
        'bg': 'rgba(239,68,68,0.10)',
        'badge_bg': '#ef4444',
        'badge_text': 'CRITIQUE',
    },
    RecommendationPriority.HIGH: {
        'border': '#f59e0b',
        'bg': 'rgba(245,158,11,0.10)',
        'badge_bg': '#f59e0b',
        'badge_text': 'IMPORTANT',
    },
    RecommendationPriority.MEDIUM: {
        'border': '#2563eb',
        'bg': 'rgba(37,99,235,0.08)',
        'badge_bg': '#2563eb',
        'badge_text': 'CONSEIL',
    },
    RecommendationPriority.INFO: {
        'border': c('border', '#1e293b'),
        'bg': 'rgba(100,116,139,0.08)',
        'badge_bg': c('text_muted', '#64748b'),
        'badge_text': 'INFO',
    },
}

CATEGORY_LABEL = {
    RecommendationCategory.CONNEXION:   '🔌 Connexion',
    RecommendationCategory.RISQUE:      '🛡️ Risque',
    RecommendationCategory.PERFORMANCE: '📊 Performance',
    RecommendationCategory.MARCHE:      '📈 Marché',
    RecommendationCategory.CONFIG:      '⚙️ Configuration',
    RecommendationCategory.EDUCATION:   '🎓 Éducation',
}


class RecommendationCard(QFrame):
    """Carte pour une seule recommandation"""

    action_clicked = pyqtSignal(str)  # action_target

    def __init__(self, rec: Recommendation, parent=None):
        super().__init__(parent)
        self.rec = rec
        self._build()

    def _build(self):
        style = PRIORITY_STYLE.get(self.rec.priority, PRIORITY_STYLE[RecommendationPriority.INFO])
        self.setStyleSheet(f"""
            RecommendationCard {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-left: 4px solid {style['border']};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # ── En-tête ──────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_label = QLabel(self.rec.icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 16))
        icon_label.setFixedWidth(28)
        header.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title_label = QLabel(self.rec.title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_col.addWidget(title_label)

        cat_label = QLabel(CATEGORY_LABEL.get(self.rec.category, ''))
        cat_label.setFont(QFont("Segoe UI", 8))
        cat_label.setStyleSheet(f"color: {c('text_muted')};")
        title_col.addWidget(cat_label)

        header.addLayout(title_col, 1)

        # Badge priorité
        badge = QLabel(style['badge_text'])
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet(f"""
            background-color: {style['badge_bg']};
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(badge)

        layout.addLayout(header)

        # ── Détail ───────────────────────────────────────────────────
        detail = QLabel(self.rec.detail)
        detail.setWordWrap(True)
        detail.setFont(QFont("Segoe UI", 9))
        detail.setStyleSheet(f"color: {c('text_secondary')};")
        layout.addWidget(detail)

        # ── Action ───────────────────────────────────────────────────
        if self.rec.action and self.rec.action_target:
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn = QPushButton(f"→  {self.rec.action}")
            btn.setFixedHeight(32)
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {style['border']};
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 0 16px;
                }}
                QPushButton:hover {{
                    opacity: 0.85;
                }}
            """)
            target = self.rec.action_target
            btn.clicked.connect(lambda: self.action_clicked.emit(target))
            btn_row.addWidget(btn)
            layout.addLayout(btn_row)


class RecommendationsView(QWidget):
    """Vue principale des recommandations"""

    # Signal pour naviguer vers un autre onglet
    navigate_to = pyqtSignal(str)

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._rec_engine = RecommendationEngine()
        self._build()

        # Rafraîchissement toutes les 60 secondes
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(60_000)
        QTimer.singleShot(500, self.refresh)

    def _build(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        main.addWidget(scroll)

        self._content = QWidget()
        scroll.setWidget(self._content)

        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(32, 24, 32, 24)
        self._layout.setSpacing(12)

        self._layout.addWidget(PageHeader(
            "Recommandations",
            "Conseils personnalisés basés sur l'état de votre bot"
        ))

        # Barre de résumé + bouton refresh
        top_row = QHBoxLayout()
        self._summary_label = QLabel("Analyse en cours...")
        self._summary_label.setFont(QFont("Segoe UI", 10))
        top_row.addWidget(self._summary_label, 1)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setFixedHeight(30)
        refresh_btn.clicked.connect(self.refresh)
        top_row.addWidget(refresh_btn)
        self._layout.addLayout(top_row)

        # Zone des cartes
        self._cards_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._layout.addWidget(self._cards_widget)

        self._layout.addStretch()

    def refresh(self):
        """Régénère toutes les recommandations"""
        try:
            from app.core.config_manager import config_manager
            recs = self._rec_engine.generate(self.engine, config_manager.config)
            self._render(recs)
        except Exception as e:
            self._summary_label.setText(f"Erreur : {e}")

    def _render(self, recs: list):
        # Vider les anciennes cartes
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not recs:
            no_rec = QLabel("✅ Tout va bien — aucune recommandation en ce moment.")
            no_rec.setFont(QFont("Segoe UI", 11))
            no_rec.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_rec.setStyleSheet(f"color: {c('success')}; padding: 40px;")
            self._cards_layout.addWidget(no_rec)
            self._summary_label.setText("✅ Aucune recommandation")
            return

        # Résumé
        critical = sum(1 for r in recs if r.priority == RecommendationPriority.CRITICAL)
        high = sum(1 for r in recs if r.priority == RecommendationPriority.HIGH)
        total = len(recs)

        if critical:
            self._summary_label.setText(
                f"🔴 {critical} critique(s) · {high} important(s) · {total} au total"
            )
            self._summary_label.setStyleSheet(f"color: {c('error')};")
        elif high:
            self._summary_label.setText(
                f"⚠️ {high} important(s) · {total} au total"
            )
            self._summary_label.setStyleSheet(f"color: {c('warning')};")
        else:
            self._summary_label.setText(f"💡 {total} conseil(s)")
            self._summary_label.setStyleSheet(f"color: {c('text_secondary')};")

        # Créer les cartes
        for rec in recs:
            card = RecommendationCard(rec)
            card.action_clicked.connect(self._on_action)
            self._cards_layout.addWidget(card)

    def _on_action(self, target: str):
        """Naviguer vers l'onglet correspondant"""
        self.navigate_to.emit(target)
