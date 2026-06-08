"""
Vue Horaires des marchés.
Affiche en temps réel l'état des sessions forex et des bourses actions.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.core.market_hours import (
    get_all_forex_status, get_all_stocks_status, get_forex_overlaps,
    format_timedelta, MarketStatus, MarketInfo,
)
from datetime import datetime


class MarketStatusCard(QFrame):
    """Carte pour un marché individuel avec statut visuel"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MarketCard")
        self.setMinimumHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Ligne du haut : emoji + nom + indicateur de statut
        header = QHBoxLayout()
        header.setSpacing(8)

        self.emoji_label = QLabel("🌍")
        self.emoji_label.setFont(QFont("Segoe UI Emoji", 20))
        header.addWidget(self.emoji_label)

        name_col = QVBoxLayout()
        name_col.setContentsMargins(0, 0, 0, 0)
        name_col.setSpacing(0)

        self.name_label = QLabel("Marché")
        self.name_label.setObjectName("MarketName")
        self.name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        name_col.addWidget(self.name_label)

        self.hours_label = QLabel("")
        self.hours_label.setObjectName("MarketHours")
        self.hours_label.setFont(QFont("Segoe UI", 9))
        name_col.addWidget(self.hours_label)

        header.addLayout(name_col, 1)

        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.addWidget(self.status_dot)

        layout.addLayout(header)

        # Ligne du bas : statut textuel
        self.status_text = QLabel("")
        self.status_text.setObjectName("MarketStatusText")
        self.status_text.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        layout.addWidget(self.status_text)

        self.time_info = QLabel("")
        self.time_info.setObjectName("MarketTimeInfo")
        self.time_info.setFont(QFont("Segoe UI", 9))
        self.time_info.setWordWrap(True)
        layout.addWidget(self.time_info)

    def update_info(self, info: MarketInfo):
        self.emoji_label.setText(info.session.emoji)
        self.name_label.setText(info.session.name)

        # Horaires
        open_str = info.session.open_time.strftime('%H:%M')
        close_str = info.session.close_time.strftime('%H:%M')
        self.hours_label.setText(f"{open_str} - {close_str} (heure locale)")

        # Statut visuel et textuel
        local_time_str = info.local_time.strftime('%H:%M')

        if info.status == MarketStatus.OPEN:
            self.status_dot.setStyleSheet("color: #10b981;")  # Vert
            self.status_text.setText("✓ OUVERT")
            self.status_text.setStyleSheet("color: #10b981;")
            if info.closes_in:
                self.time_info.setText(
                    f"Ferme dans {format_timedelta(info.closes_in)} • "
                    f"Heure locale : {local_time_str}"
                )
        elif info.status == MarketStatus.CLOSES_SOON:
            self.status_dot.setStyleSheet("color: #f59e0b;")  # Orange
            self.status_text.setText("⏰ FERME BIENTÔT")
            self.status_text.setStyleSheet("color: #f59e0b;")
            if info.closes_in:
                self.time_info.setText(
                    f"Ferme dans {format_timedelta(info.closes_in)} • "
                    f"Heure locale : {local_time_str}"
                )
        elif info.status == MarketStatus.OPENS_SOON:
            self.status_dot.setStyleSheet("color: #f59e0b;")  # Orange
            self.status_text.setText("⏰ OUVRE BIENTÔT")
            self.status_text.setStyleSheet("color: #f59e0b;")
            if info.opens_in:
                self.time_info.setText(
                    f"Ouvre dans {format_timedelta(info.opens_in)} • "
                    f"Heure locale : {local_time_str}"
                )
        else:
            self.status_dot.setStyleSheet("color: #6b7280;")  # Gris
            if info.is_weekend:
                self.status_text.setText("✗ FERMÉ (week-end)")
            else:
                self.status_text.setText("✗ FERMÉ")
            self.status_text.setStyleSheet("color: #94a3b8;")
            if info.opens_in:
                self.time_info.setText(
                    f"Rouvre dans {format_timedelta(info.opens_in)} • "
                    f"Heure locale : {local_time_str}"
                )


class MarketHoursView(QWidget):
    """Vue des horaires de marchés"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

        # Rafraichissement toutes les 30 secondes
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(30000)
        # Premier refresh immédiat
        QTimer.singleShot(100, self.refresh)

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Horaires des marchés",
            "Statut en temps réel des sessions forex et des bourses actions"
        ))

        # Heure actuelle Paris + UTC
        self.time_card = Card("Heure actuelle")
        self.time_display = QLabel("—")
        self.time_display.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.time_card.add_widget(self.time_display)
        layout.addWidget(self.time_card)

        # Résumé des sessions ouvertes
        self.summary_card = Card("Sessions forex actives")
        self.summary_label = QLabel("Chargement...")
        self.summary_label.setWordWrap(True)
        self.summary_label.setFont(QFont("Segoe UI", 11))
        self.summary_card.add_widget(self.summary_label)

        self.overlap_label = QLabel("")
        self.overlap_label.setWordWrap(True)
        self.overlap_label.setFont(QFont("Segoe UI", 10))
        self.summary_card.add_widget(self.overlap_label)
        layout.addWidget(self.summary_card)

        # Sessions Forex (4 grandes sessions)
        forex_card = Card("Sessions Forex (24/5)")
        forex_grid = QGridLayout()
        forex_grid.setSpacing(12)

        self.forex_cards = []
        for i in range(4):
            card = MarketStatusCard()
            card.setStyleSheet("""
                QFrame#MarketCard {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                }
            """)
            row, col = divmod(i, 2)
            forex_grid.addWidget(card, row, col)
            self.forex_cards.append(card)

        forex_card.add_layout(forex_grid)
        layout.addWidget(forex_card)

        # Bourses actions
        stocks_card = Card("Bourses actions")
        stocks_grid = QGridLayout()
        stocks_grid.setSpacing(12)

        self.stock_cards = []
        for i in range(7):  # 7 bourses définies
            card = MarketStatusCard()
            card.setStyleSheet("""
                QFrame#MarketCard {
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                }
            """)
            row, col = divmod(i, 2)
            stocks_grid.addWidget(card, row, col)
            self.stock_cards.append(card)

        stocks_card.add_layout(stocks_grid)
        layout.addWidget(stocks_card)

        # Explication pédagogique
        info_card = Card("💡 À savoir")
        info_text = QLabel(
            "<b>Sessions forex</b> : le marché des changes tourne 24h/24 du lundi au vendredi. "
            "Les sessions se chevauchent : c'est pendant ces périodes que la liquidité et la "
            "volatilité sont les plus élevées.<br><br>"
            "<b>Meilleurs moments pour trader</b> :<br>"
            "• <b>13h-17h (heure de Paris)</b> : chevauchement Londres / New York — le plus actif<br>"
            "• <b>9h-11h (heure de Paris)</b> : chevauchement Tokyo / Londres<br>"
            "• <b>Nuit et week-end</b> : liquidité faible, spreads élevés, à éviter<br><br>"
            "<b>Bourses actions</b> : ouvertes uniquement aux heures indiquées (environ 7-8h par jour), "
            "fermées week-end et jours fériés locaux."
        )
        info_text.setWordWrap(True)
        info_text.setTextFormat(Qt.TextFormat.RichText)
        info_text.setFont(QFont("Segoe UI", 9))
        info_card.add_widget(info_text)
        layout.addWidget(info_card)

        layout.addStretch()

    def refresh(self):
        try:
            now_utc = datetime.now()

            # Heure Paris + UTC
            try:
                import zoneinfo
                paris_tz = zoneinfo.ZoneInfo("Europe/Paris")
                paris_time = now_utc.astimezone(paris_tz)
                self.time_display.setText(
                    f"🇫🇷 Paris : {paris_time.strftime('%A %d %B · %H:%M:%S')}"
                )
            except Exception:
                self.time_display.setText(now_utc.strftime('%H:%M:%S'))

            # Forex
            forex_infos = get_all_forex_status()
            for card, info in zip(self.forex_cards, forex_infos):
                card.update_info(info)

            # Stocks
            stock_infos = get_all_stocks_status()
            for card, info in zip(self.stock_cards, stock_infos):
                card.update_info(info)

            # Résumé
            open_forex = [
                info for info in forex_infos
                if info.status in (MarketStatus.OPEN, MarketStatus.CLOSES_SOON)
            ]
            if not open_forex:
                next_open = min(
                    (info for info in forex_infos if info.opens_in),
                    key=lambda x: x.opens_in,
                    default=None
                )
                if next_open:
                    self.summary_label.setText(
                        f"⏸ Tous les marchés forex sont fermés. "
                        f"Le prochain ({next_open.session.emoji} {next_open.session.name}) "
                        f"ouvre dans {format_timedelta(next_open.opens_in)}."
                    )
                else:
                    self.summary_label.setText("⏸ Tous les marchés forex sont fermés.")
                self.overlap_label.setText("")
            else:
                names = [f"{info.session.emoji} {info.session.name}" for info in open_forex]
                self.summary_label.setText(
                    f"🟢 {len(open_forex)} session{'s' if len(open_forex) > 1 else ''} "
                    f"active{'s' if len(open_forex) > 1 else ''} : " + ", ".join(names)
                )
                if len(open_forex) >= 2:
                    self.overlap_label.setText(
                        "💥 Chevauchement en cours — liquidité et volatilité élevées, "
                        "moment favorable pour trader."
                    )
                    self.overlap_label.setStyleSheet("color: #10b981;")
                else:
                    self.overlap_label.setText(
                        "Session unique active — liquidité modérée."
                    )
                    self.overlap_label.setStyleSheet("")
        except Exception as e:
            print(f"Erreur refresh market hours : {e}")
