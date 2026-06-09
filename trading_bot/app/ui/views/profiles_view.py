"""
Vue de sélection du profil de trading.
Permet de choisir entre Safe / Normal / Aggressive / EXTREME et 3 stratégies pures.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QFrame, QScrollArea, QGridLayout, QLineEdit, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS
from app.core.config_manager import config_manager
from app.core.trading_profiles import (
    list_profiles, get_profile, TradingProfile, TradingMode,
)


class ProfileCard(QFrame):
    """Carte de présentation d'un profil de trading"""

    selected = pyqtSignal(str)  # ID du profil

    def __init__(self, profile: TradingProfile, profile_id: str,
                 is_active: bool = False, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.profile_id = profile_id
        self.is_active = is_active
        self.setObjectName("ProfileCard")
        self.setMinimumHeight(320)
        self._build()

    def _build(self):
        # Couleur du bord selon le mode
        mode_colors = {
            TradingMode.SAFE: '#10b981',        # Vert
            TradingMode.NORMAL: '#2563eb',      # Bleu
            TradingMode.AGGRESSIVE: '#ef4444',  # Rouge
            TradingMode.EXTREME: '#7c3aed',     # Violet 🔥🔥
        }
        border_color = mode_colors.get(self.profile.mode, '#6b7280')

        if self.is_active:
            self.setStyleSheet(f"""
                QFrame#ProfileCard {{
                    background-color: {COLORS.get('card_bg', '#1a2028')};
                    border: 2px solid {border_color};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#ProfileCard {{
                    background-color: {COLORS.get('card_bg', '#1a2028')};
                    border: 1px solid {COLORS.get('border', '#1e293b')};
                    border-radius: 8px;
                }}
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Titre
        title = QLabel(self.profile.name)
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(title)

        # Badge actif
        if self.is_active:
            active_badge = QLabel("✓ ACTIF")
            active_badge.setStyleSheet(
                f"color: {border_color}; font-weight: bold; "
                f"background: rgba(16, 185, 129, 0.1); "
                f"padding: 2px 8px; border-radius: 3px;"
            )
            active_badge.setMaximumWidth(80)
            layout.addWidget(active_badge)

        # Description
        desc = QLabel(self.profile.description)
        desc.setWordWrap(True)
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet(f"color: {COLORS.get('text_secondary', '#94a3b8')};")
        layout.addWidget(desc)

        # Métriques clés
        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(4)

        metrics = [
            ("Risque par trade", f"{self.profile.risk_per_trade_pct}%"),
            ("Positions max", str(self.profile.max_concurrent_positions)),
            ("Perte max/jour", f"{self.profile.max_daily_loss_pct}%"),
            ("R:R", f"{self.profile.risk_reward_ratio}:1"),
            ("Confiance min", f"{self.profile.min_confidence:.0%}"),
            ("Stratégies à confirmer", str(self.profile.min_strategies_agreement)),
        ]

        for i, (label, value) in enumerate(metrics):
            row, col = divmod(i, 2)
            l = QLabel(f"{label} :")
            l.setFont(QFont("Segoe UI", 9))
            l.setStyleSheet(f"color: {COLORS.get('text_secondary', '#94a3b8')};")
            v = QLabel(value)
            v.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            metrics_layout.addWidget(l, row, col * 2)
            metrics_layout.addWidget(v, row, col * 2 + 1)

        layout.addLayout(metrics_layout)

        # Sécurités EXTREME
        if self.profile.mode == TradingMode.EXTREME:
            sec_layout = QGridLayout()
            sec_layout.setSpacing(4)
            secs = [
                ("Max pertes consécutives", str(self.profile.max_consecutive_losses)),
                ("Max trades/jour", str(self.profile.max_trades_per_day)),
                ("Cooldown", f"{self.profile.cooldown_between_trades_min} min"),
                ("Levier max", f"x{self.profile.leverage_cap}"),
                ("Auto-off", f"{self.profile.time_limit_hours}h"),
            ]
            for i, (label, value) in enumerate(secs):
                row, col = divmod(i, 2)
                l = QLabel(f"{label} :")
                l.setFont(QFont("Segoe UI", 8))
                l.setStyleSheet(f"color: #a855f7;")
                v = QLabel(value)
                v.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                v.setStyleSheet(f"color: #a855f7;")
                sec_layout.addWidget(l, row, col * 2)
                sec_layout.addWidget(v, row, col * 2 + 1)
            layout.addLayout(sec_layout)

        # Avertissements importants
        if self.profile.warnings:
            warn_text = "\n".join(f"• {w}" for w in self.profile.warnings[:4])
            if len(self.profile.warnings) > 4:
                warn_text += f"\n• ... ({len(self.profile.warnings) - 4} avertissements supplémentaires)"
            warn_label = QLabel(warn_text)
            warn_label.setWordWrap(True)
            warn_label.setFont(QFont("Segoe UI", 8))
            warn_label.setStyleSheet(
                f"color: {COLORS.get('warning', '#f59e0b')}; "
                f"padding: 8px; background: rgba(245, 158, 11, 0.08); "
                f"border-radius: 4px;"
            )
            layout.addWidget(warn_label)

        layout.addStretch()

        # Bouton activer
        if not self.is_active:
            select_btn = QPushButton(f"Activer ce profil")
            select_btn.setMinimumHeight(36)
            select_btn.setStyleSheet(
                f"QPushButton {{ background-color: {border_color}; "
                f"color: white; font-weight: bold; border-radius: 4px; }}"
            )
            select_btn.clicked.connect(lambda: self.selected.emit(self.profile_id))
            layout.addWidget(select_btn)


class TradingProfilesView(QWidget):
    """Vue des profils de trading"""

    profile_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

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
            "Profils de trading",
            "Choisissez votre niveau de risque et votre stratégie"
        ))

        # Avertissement général
        warning = Card("⚠️ À lire avant de choisir")
        warning_text = QLabel(
            "Le choix d'un profil affecte le NOMBRE de trades, le RISQUE par trade, "
            "et la STRATÉGIE utilisée. Aucun profil ne garantit un gain.\n\n"
            "<b>Recommandation :</b> commencez TOUJOURS par 'Safe' en mode Paper Trading "
            "pendant 2-3 semaines avant de passer en réel ou en mode plus agressif.\n\n"
            "<b>Important :</b> les profils 'Aggressive', 'EXTREME' et 'pure' "
            "sont réservés aux utilisateurs expérimentés. Ils peuvent générer des pertes "
            "importantes en conditions de marché défavorables.\n\n"
            "<b>🔥🔥 EXTREME :</b> Mode à haut risque avec sécurités automatiques. "
            "PIN requis. Désactivation auto après 48h."
        )
        warning_text.setWordWrap(True)
        warning_text.setTextFormat(Qt.TextFormat.RichText)
        warning.add_widget(warning_text)
        layout.addWidget(warning)

        # Section : 4 modes de risque
        modes_card = Card("4 modes de risque (recommandés)")
        modes_grid = QGridLayout()
        modes_grid.setSpacing(12)

        active_id = config_manager.config.strategy.active_profile

        risk_modes = ['safe', 'normal', 'aggressive', 'extreme']
        for i, profile_id in enumerate(risk_modes):
            profile = get_profile(profile_id)
            card = ProfileCard(
                profile, profile_id,
                is_active=(profile_id == active_id),
            )
            card.selected.connect(self._activate_profile)
            modes_grid.addWidget(card, 0, i)

        modes_card.add_layout(modes_grid)
        layout.addWidget(modes_card)

        # Section : Stratégies pures
        pures_card = Card("Stratégies pures (avancé)")
        pures_grid = QGridLayout()
        pures_grid.setSpacing(12)

        for i, profile_id in enumerate(['trend_pure', 'mean_reversion_pure', 'breakout_pure']):
            profile = get_profile(profile_id)
            card = ProfileCard(
                profile, profile_id,
                is_active=(profile_id == active_id),
            )
            card.selected.connect(self._activate_profile)
            pures_grid.addWidget(card, 0, i)

        pures_card.add_layout(pures_grid)
        layout.addWidget(pures_card)

        layout.addStretch()

    def _activate_profile(self, profile_id: str):
        profile = get_profile(profile_id)

        # ─── EXTREME MODE : Double confirmation + PIN ───
        if profile.mode == TradingMode.EXTREME:
            # Étape 1 : Avertissement avec checkbox
            warnings_str = "\n".join(profile.warnings)
            reply = QMessageBox.critical(
                self,
                "🔥🔥 ACTIVATION EXTREME — CONFIRMATION FINALE",
                f"Vous activez le mode {profile.name}.\n\n"
                f"{'='*50}\n"
                f"{warnings_str}\n"
                f"{'='*50}\n\n"
                f"Ce mode est CONÇU pour maximiser les rendements à COURT TERME.\n"
                f"Votre compte peut perdre jusqu'à 30% AVANT l'arrêt automatique.\n\n"
                f"Êtes-vous ABSOLUMENT SÛR ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # Étape 2 : PIN requis
            pin, ok = QInputDialog.getText(
                self,
                "PIN requis",
                "Entrez le code PIN pour déverrouiller le mode EXTREME :\n"
                "(Le PIN par défaut est '0000' — changez-le dans les paramètres)",
                QLineEdit.EchoMode.Password
            )
            if not ok or not pin:
                return

            # Vérifier le PIN (stocké dans la config ou défaut)
            expected_pin = getattr(
                config_manager.config.strategy, 'extreme_pin', '0000'
            )
            if pin != expected_pin:
                QMessageBox.critical(
                    self, "PIN incorrect",
                    "Le code PIN est incorrect. Mode EXTREME non activé."
                )
                return

        # ─── AGGRESSIVE MODE : Confirmation simple ───
        elif profile.mode == TradingMode.AGGRESSIVE:
            warnings_str = "\n".join(profile.warnings)
            reply = QMessageBox.warning(
                self, "Confirmer le mode Aggressive",
                f"Vous activez le mode {profile.name}.\n\n"
                f"AVERTISSEMENTS :\n{warnings_str}\n\n"
                "Êtes-vous SÛR de vouloir activer ce mode ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # ─── Appliquer le profil à la config ───
        cfg = config_manager.config
        cfg.strategy.active_profile = profile_id
        cfg.strategy.risk_per_trade = profile.risk_per_trade_pct
        cfg.strategy.max_positions = profile.max_concurrent_positions
        cfg.strategy.daily_loss_limit_pct = profile.max_daily_loss_pct
        cfg.strategy.max_drawdown_pct = profile.max_drawdown_pct
        cfg.strategy.min_strategies_agreement = profile.min_strategies_agreement
        cfg.strategy.min_confidence = profile.min_confidence
        cfg.strategy.risk_reward_ratio = profile.risk_reward_ratio
        cfg.strategy.atr_multiplier_sl = profile.atr_multiplier_sl
        cfg.strategy.use_volatility_filter = profile.use_volatility_filter
        cfg.strategy.use_correlation_filter = profile.use_correlation_filter
        cfg.strategy.use_news_filter = profile.use_news_filter
        cfg.strategy.enable_trailing_stop = profile.enable_trailing_stop
        cfg.strategy.enable_breakeven = profile.enable_breakeven

        # EXTREME : sécurités supplémentaires
        if profile.mode == TradingMode.EXTREME:
            cfg.strategy.extreme_pin = getattr(cfg.strategy, 'extreme_pin', '0000')
            cfg.strategy.extreme_max_consecutive_losses = profile.max_consecutive_losses
            cfg.strategy.extreme_max_trades_per_day = profile.max_trades_per_day
            cfg.strategy.extreme_time_limit_hours = profile.time_limit_hours
            cfg.strategy.extreme_cooldown_min = profile.cooldown_between_trades_min
            cfg.strategy.extreme_leverage_cap = profile.leverage_cap
            cfg.strategy.extreme_enable_circuit_breaker = profile.enable_circuit_breaker

        # Heures de trading : forex tourne 24h/5
        cfg.strategy.start_hour = 0
        cfg.strategy.end_hour = 24
        # Timeframe H1 pour plus de signaux
        cfg.strategy.timeframe = "H1"
        for sym in cfg.symbols:
            sym.timeframe = "H1"

        config_manager.save()
        self.profile_changed.emit(profile_id)

        QMessageBox.information(
            self, "Profil activé",
            f"Le profil {profile.name} est maintenant actif.\n\n"
            "Si le bot tourne, redémarrez-le pour appliquer les changements."
        )

        # Rafraîchir
        self._refresh_view()

    def _refresh_view(self):
        # Reconstruire la vue
        layout = self.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._build()
