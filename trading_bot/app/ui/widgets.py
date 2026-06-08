"""
Widgets réutilisables de l'application.
AUCUN stylesheet inline ici : tout est géré par le stylesheet GLOBAL via objectName.
Cela garantit que le changement de thème s'applique correctement.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QFont


class Card(QFrame):
    """Carte stylisée pour afficher du contenu"""
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 16, 20, 16)
        self._layout.setSpacing(12)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("CardTitle")
            title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self._layout.addWidget(title_label)

    def add_widget(self, widget: QWidget):
        self._layout.addWidget(widget)

    def add_layout(self, layout):
        self._layout.addLayout(layout)


class KPICard(QFrame):
    """Carte KPI : titre + valeur + sous-titre"""
    def __init__(self, title: str, value: str = "—", subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("KPICard")
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("KPITitle")
        self.title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))

        self.value_label = QLabel(value)
        self.value_label.setObjectName("KPIValue")
        self.value_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("KPISubtitle")
        self.subtitle_label.setFont(QFont("Segoe UI", 9))

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)

    def set_value(self, value: str, color: str = None):
        """Met à jour la valeur. Si color est fourni, override (ex: vert/rouge pour P&L)."""
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; background: transparent;")
        else:
            # Reset - laisse le stylesheet global s'appliquer
            self.value_label.setStyleSheet("")

    def set_subtitle(self, text: str, color: str = None):
        self.subtitle_label.setText(text)
        if color:
            self.subtitle_label.setStyleSheet(f"color: {color}; background: transparent;")
        else:
            self.subtitle_label.setStyleSheet("")


class PageHeader(QWidget):
    """En-tête de page avec titre et description"""
    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("PageHeader")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("PageDescription")
            desc_label.setFont(QFont("Segoe UI", 10))
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
