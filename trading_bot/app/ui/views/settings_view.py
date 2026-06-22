"""
Vue Paramètres - Configuration complète de l'application
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QTabWidget, QGroupBox, QLabel, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS
from app.core.config_manager import config_manager, SymbolConfig


class SettingsView(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = config_manager.config
        self._build()
        self._load_from_config()

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(16)

        main_layout.addWidget(PageHeader(
            "Paramètres",
            "Configuration du bot, des alertes, et des préférences"
        ))

        tabs = QTabWidget()
        tabs.addTab(self._build_strategy_tab(), "Stratégie")
        tabs.addTab(self._build_symbols_tab(), "Symboles")
        tabs.addTab(self._build_mt5_tab(), "Connexion MT5")
        tabs.addTab(self._build_telegram_tab(), "Alertes Telegram")
        tabs.addTab(self._build_news_tab(), "Filtre news")
        tabs.addTab(self._build_ui_tab(), "Interface")
        tabs.addTab(self._build_profiles_tab(), "Profils")

        main_layout.addWidget(tabs)

        # Barre d'actions
        actions = QHBoxLayout()
        reset_btn = QPushButton("Rétablir par défaut")
        reset_btn.clicked.connect(self._reset_defaults)
        actions.addWidget(reset_btn)
        actions.addStretch()

        save_btn = QPushButton("💾 Sauvegarder")
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(180)
        save_btn.clicked.connect(self._save)
        actions.addWidget(save_btn)

        main_layout.addLayout(actions)

    # ========================================================================
    # ONGLETS
    # ========================================================================

    def _build_strategy_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Gestion du risque
        risk_group = QGroupBox("Gestion du risque")
        risk_form = QFormLayout(risk_group)
        risk_form.setSpacing(10)

        self.risk_percent = QDoubleSpinBox()
        self.risk_percent.setRange(0.1, 5.0)
        self.risk_percent.setSingleStep(0.1)
        self.risk_percent.setSuffix(" %")
        risk_form.addRow("Risque par trade :", self.risk_percent)

        self.risk_reward = QDoubleSpinBox()
        self.risk_reward.setRange(1.0, 10.0)
        self.risk_reward.setSingleStep(0.1)
        risk_form.addRow("Ratio Risk:Reward (1:X) :", self.risk_reward)

        self.atr_period = QSpinBox()
        self.atr_period.setRange(5, 50)
        risk_form.addRow("Période ATR :", self.atr_period)

        self.atr_multiplier = QDoubleSpinBox()
        self.atr_multiplier.setRange(0.5, 10.0)
        self.atr_multiplier.setSingleStep(0.1)
        risk_form.addRow("Multiplicateur ATR :", self.atr_multiplier)

        self.max_consec_losses = QSpinBox()
        self.max_consec_losses.setRange(1, 10)
        risk_form.addRow("Pertes consécutives max :", self.max_consec_losses)

        self.max_daily_loss = QDoubleSpinBox()
        self.max_daily_loss.setRange(1.0, 20.0)
        self.max_daily_loss.setSingleStep(0.5)
        self.max_daily_loss.setSuffix(" %")
        risk_form.addRow("Perte journalière max :", self.max_daily_loss)

        layout.addWidget(risk_group)

        # Indicateurs techniques
        indicators_group = QGroupBox("Indicateurs techniques")
        ind_form = QFormLayout(indicators_group)
        ind_form.setSpacing(10)

        self.fast_ema = QSpinBox()
        self.fast_ema.setRange(5, 200)
        ind_form.addRow("EMA rapide :", self.fast_ema)

        self.slow_ema = QSpinBox()
        self.slow_ema.setRange(20, 500)
        ind_form.addRow("EMA lente :", self.slow_ema)

        self.rsi_period = QSpinBox()
        self.rsi_period.setRange(5, 30)
        ind_form.addRow("Période RSI :", self.rsi_period)

        self.rsi_overbought = QDoubleSpinBox()
        self.rsi_overbought.setRange(50.0, 100.0)
        ind_form.addRow("RSI sur-acheté :", self.rsi_overbought)

        self.rsi_oversold = QDoubleSpinBox()
        self.rsi_oversold.setRange(0.0, 50.0)
        ind_form.addRow("RSI sur-vendu :", self.rsi_oversold)

        layout.addWidget(indicators_group)

        # Filtres
        filter_group = QGroupBox("Filtres temporels")
        filter_form = QFormLayout(filter_group)
        filter_form.setSpacing(10)

        self.start_hour = QSpinBox()
        self.start_hour.setRange(0, 23)
        filter_form.addRow("Heure de début :", self.start_hour)

        self.end_hour = QSpinBox()
        self.end_hour.setRange(0, 23)
        filter_form.addRow("Heure de fin :", self.end_hour)

        self.trade_friday = QCheckBox("Autoriser le vendredi")
        filter_form.addRow("", self.trade_friday)

        self.min_bars = QSpinBox()
        self.min_bars.setRange(1, 100)
        filter_form.addRow("Barres min entre trades :", self.min_bars)

        self.magic_number = QSpinBox()
        self.magic_number.setRange(1, 999999999)
        filter_form.addRow("Magic number :", self.magic_number)

        layout.addWidget(filter_group)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _build_symbols_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Configurez les symboles que le bot doit surveiller. "
                     "Chaque symbole a son propre timeframe.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.setWordWrap(True)
        layout.addWidget(info)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("+ Ajouter un symbole")
        add_btn.clicked.connect(self._add_symbol)
        toolbar.addWidget(add_btn)

        remove_btn = QPushButton("- Supprimer sélectionné")
        remove_btn.clicked.connect(self._remove_symbol)
        toolbar.addWidget(remove_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.symbols_table = QTableWidget()
        self.symbols_table.setColumnCount(3)
        self.symbols_table.setHorizontalHeaderLabels(['Symbole', 'Timeframe', 'Activé'])
        self.symbols_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.symbols_table.setAlternatingRowColors(True)
        layout.addWidget(self.symbols_table)

        return widget

    def _build_mt5_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QLabel("Par défaut, l'application se connecte à MT5 lancé localement. "
                     "Renseignez les identifiants pour une connexion spécifique.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.setWordWrap(True)
        layout.addWidget(info)

        group = QGroupBox("Connexion MT5")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.mt5_auto = QCheckBox("Détection automatique (MT5 déjà lancé)")
        form.addRow("", self.mt5_auto)

        self.mt5_path = QLineEdit()
        self.mt5_path.setPlaceholderText("C:/Program Files/MetaTrader 5/terminal64.exe")
        browse_btn = QPushButton("Parcourir...")
        browse_btn.clicked.connect(self._browse_mt5)
        path_row = QHBoxLayout()
        path_row.addWidget(self.mt5_path)
        path_row.addWidget(browse_btn)
        form.addRow("Chemin MT5 :", path_row)

        self.mt5_login = QSpinBox()
        self.mt5_login.setRange(0, 999999999)
        form.addRow("Login :", self.mt5_login)

        self.mt5_password = QLineEdit()
        self.mt5_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mot de passe :", self.mt5_password)

        self.mt5_server = QLineEdit()
        form.addRow("Serveur :", self.mt5_server)

        self.broker_name = QLineEdit()
        form.addRow("Nom du broker :", self.broker_name)

        layout.addWidget(group)
        layout.addStretch()

        return widget

    def _build_telegram_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QLabel(
            "Les alertes Telegram vous notifient des événements importants. "
            "Configuration : parler à @BotFather → /newbot → copier le TOKEN. "
            "Pour le CHAT_ID : parler à @userinfobot → /start."
        )
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.setWordWrap(True)
        layout.addWidget(info)

        main_group = QGroupBox("Configuration Telegram")
        form = QFormLayout(main_group)
        form.setSpacing(10)

        self.tg_enabled = QCheckBox("Activer les alertes Telegram")
        form.addRow("", self.tg_enabled)

        self.tg_token = QLineEdit()
        self.tg_token.setPlaceholderText("123456:ABC-DEF1234...")
        form.addRow("Token Bot :", self.tg_token)

        self.tg_chat_id = QLineEdit()
        form.addRow("Chat ID :", self.tg_chat_id)

        test_btn = QPushButton("📨 Envoyer un message de test")
        test_btn.clicked.connect(self._test_telegram)
        form.addRow("", test_btn)

        layout.addWidget(main_group)

        alerts_group = QGroupBox("Types d'alertes")
        alerts_form = QFormLayout(alerts_group)

        self.alert_dd = QCheckBox("Drawdown excessif")
        self.alert_dd_threshold = QDoubleSpinBox()
        self.alert_dd_threshold.setRange(1.0, 50.0)
        self.alert_dd_threshold.setSuffix(" %")
        alerts_form.addRow(self.alert_dd, self.alert_dd_threshold)

        self.alert_losses = QCheckBox("Pertes consécutives")
        alerts_form.addRow("", self.alert_losses)

        self.alert_pos_open = QCheckBox("Ouverture de position")
        alerts_form.addRow("", self.alert_pos_open)

        self.alert_pos_close = QCheckBox("Clôture de position")
        alerts_form.addRow("", self.alert_pos_close)

        self.alert_news = QCheckBox("News à haut impact")
        alerts_form.addRow("", self.alert_news)

        self.alert_daily = QCheckBox("Rapport journalier")
        self.daily_hour = QSpinBox()
        self.daily_hour.setRange(0, 23)
        self.daily_hour.setSuffix(" h")
        alerts_form.addRow(self.alert_daily, self.daily_hour)

        layout.addWidget(alerts_group)
        layout.addStretch()

        return widget

    def _build_news_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QLabel("Le bot s'abstient de trader autour des annonces économiques "
                     "majeures pour éviter les spreads élevés et les mouvements erratiques.")
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.setWordWrap(True)
        layout.addWidget(info)

        group = QGroupBox("Filtre d'actualités économiques")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.news_enabled = QCheckBox("Activer le filtre news")
        form.addRow("", self.news_enabled)

        self.news_before = QSpinBox()
        self.news_before.setRange(0, 120)
        self.news_before.setSuffix(" minutes")
        form.addRow("Pause avant news :", self.news_before)

        self.news_after = QSpinBox()
        self.news_after.setRange(0, 120)
        self.news_after.setSuffix(" minutes")
        form.addRow("Pause après news :", self.news_after)

        self.block_high = QCheckBox("Bloquer sur news HIGH impact")
        form.addRow("", self.block_high)

        self.block_medium = QCheckBox("Bloquer sur news MEDIUM impact")
        form.addRow("", self.block_medium)

        self.news_refresh = QSpinBox()
        self.news_refresh.setRange(15, 360)
        self.news_refresh.setSuffix(" minutes")
        form.addRow("Rafraîchir le calendrier :", self.news_refresh)

        layout.addWidget(group)
        layout.addStretch()

        return widget

    def _build_ui_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        group = QGroupBox("Préférences d'interface")
        form = QFormLayout(group)
        form.setSpacing(10)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Sombre", "Clair"])
        self.theme_combo.setToolTip("Le changement de thème redémarre l'application")
        form.addRow("Thème :", self.theme_combo)

        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1, 60)
        self.refresh_interval.setSuffix(" secondes")
        form.addRow("Intervalle d'actualisation :", self.refresh_interval)

        self.minimize_tray = QCheckBox("Minimiser dans la zone de notification")
        form.addRow("", self.minimize_tray)

        self.start_minimized = QCheckBox("Démarrer minimisé")
        form.addRow("", self.start_minimized)

        self.auto_start_bot = QCheckBox("Démarrer le bot au lancement")
        form.addRow("", self.auto_start_bot)

        layout.addWidget(group)

        # Section Sécurité (PIN)
        sec_group = QGroupBox("🔐 Sécurité (PIN)")
        sec_form = QFormLayout(sec_group)
        sec_form.setSpacing(10)

        self.pin_status_label = QLabel("PIN désactivé")
        sec_form.addRow("Statut :", self.pin_status_label)

        self.pin_lock_startup = QCheckBox("Verrouiller au démarrage de l'app")
        sec_form.addRow("", self.pin_lock_startup)

        self.pin_required_trading = QCheckBox("Demander le PIN avant de démarrer le bot")
        sec_form.addRow("", self.pin_required_trading)

        pin_buttons = QHBoxLayout()
        self.pin_setup_btn = QPushButton("🔑 Définir / Changer le PIN")
        self.pin_setup_btn.clicked.connect(self._setup_pin)
        pin_buttons.addWidget(self.pin_setup_btn)

        self.pin_disable_btn = QPushButton("Désactiver le PIN")
        self.pin_disable_btn.clicked.connect(self._disable_pin)
        pin_buttons.addWidget(self.pin_disable_btn)

        pin_buttons.addStretch()
        sec_form.addRow("", pin_buttons)

        layout.addWidget(sec_group)

        layout.addStretch()

        return widget

    def _build_profiles_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        info = QLabel("Sauvegardez différentes configurations comme profils "
                     "(ex: 'Conservateur', 'Agressif', 'Demo')")
        info.setStyleSheet(f"color: {COLORS['text_secondary']};")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Liste des profils
        self.profiles_list = QTableWidget()
        self.profiles_list.setColumnCount(1)
        self.profiles_list.setHorizontalHeaderLabels(['Nom du profil'])
        self.profiles_list.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._refresh_profiles_list()
        layout.addWidget(self.profiles_list)

        # Actions profils
        actions = QHBoxLayout()

        self.new_profile_name = QLineEdit()
        self.new_profile_name.setPlaceholderText("Nom du nouveau profil")
        actions.addWidget(self.new_profile_name)

        save_profile_btn = QPushButton("Sauvegarder comme profil")
        save_profile_btn.clicked.connect(self._save_profile)
        actions.addWidget(save_profile_btn)

        load_profile_btn = QPushButton("Charger le profil sélectionné")
        load_profile_btn.clicked.connect(self._load_profile)
        actions.addWidget(load_profile_btn)

        layout.addLayout(actions)
        layout.addStretch()

        return widget

    # ========================================================================
    # CHARGEMENT / SAUVEGARDE
    # ========================================================================

    def _load_from_config(self):
        s = self.config.strategy
        self.risk_percent.setValue(int(s.risk_percent))
        self.risk_reward.setValue(int(s.risk_reward_ratio))
        self.atr_period.setValue(int(s.atr_period))
        self.atr_multiplier.setValue(int(s.atr_multiplier))
        self.max_consec_losses.setValue(int(s.max_consecutive_losses))
        self.max_daily_loss.setValue(int(s.max_daily_loss_percent))
        self.fast_ema.setValue(int(s.fast_ema))
        self.slow_ema.setValue(int(s.slow_ema))
        self.rsi_period.setValue(int(s.rsi_period))
        self.rsi_overbought.setValue(int(s.rsi_overbought))
        self.rsi_oversold.setValue(int(s.rsi_oversold))
        self.start_hour.setValue(int(s.start_hour))
        self.end_hour.setValue(int(s.end_hour))
        self.trade_friday.setChecked(s.trade_on_friday)
        self.min_bars.setValue(int(s.min_bars_between_trades))
        self.magic_number.setValue(int(s.magic_number))

        # Symboles
        self._refresh_symbols_table()

        # MT5
        m = self.config.mt5
        self.mt5_auto.setChecked(m.auto_detect)
        self.mt5_path.setText(m.terminal_path)
        self.mt5_login.setValue(m.login)
        self.mt5_password.setText(m.password)
        self.mt5_server.setText(m.server)
        self.broker_name.setText(self.config.broker_name)

        # Telegram
        t = self.config.telegram
        self.tg_enabled.setChecked(t.enabled)
        self.tg_token.setText(t.token)
        self.tg_chat_id.setText(t.chat_id)
        self.alert_dd.setChecked(t.alert_drawdown)
        self.alert_dd_threshold.setValue(t.alert_drawdown_threshold)
        self.alert_losses.setChecked(t.alert_consecutive_losses)
        self.alert_pos_open.setChecked(t.alert_position_open)
        self.alert_pos_close.setChecked(t.alert_position_close)
        self.alert_news.setChecked(t.alert_news)
        self.alert_daily.setChecked(t.alert_daily_report)
        self.daily_hour.setValue(t.daily_report_hour)

        # News
        n = self.config.news
        self.news_enabled.setChecked(n.enabled)
        self.news_before.setValue(n.blackout_minutes_before)
        self.news_after.setValue(n.blackout_minutes_after)
        self.block_high.setChecked(n.block_high_impact)
        self.block_medium.setChecked(n.block_medium_impact)
        self.news_refresh.setValue(n.refresh_interval_minutes)

        # UI
        u = self.config.ui
        self.theme_combo.setCurrentText("Sombre" if u.theme == "dark" else "Clair")
        self.refresh_interval.setValue(u.refresh_interval_seconds)
        self.minimize_tray.setChecked(u.minimize_to_tray)
        self.start_minimized.setChecked(u.start_minimized)
        self.auto_start_bot.setChecked(u.auto_start_bot)

        # Security (PIN)
        s = self.config.security
        self._refresh_pin_status()
        self.pin_lock_startup.setChecked(s.lock_on_startup)
        self.pin_required_trading.setChecked(s.require_pin_for_trading)

    def _refresh_pin_status(self):
        s = self.config.security
        if s.enabled:
            self.pin_status_label.setText("✓ PIN actif")
            self.pin_status_label.setStyleSheet(f"color: {COLORS.get('success', '#10b981')};")
            self.pin_disable_btn.setEnabled(True)
        else:
            self.pin_status_label.setText("PIN désactivé")
            self.pin_status_label.setStyleSheet(f"color: {COLORS.get('text_secondary', '#94a3b8')};")
            self.pin_disable_btn.setEnabled(False)

    def _setup_pin(self):
        from app.ui.pin_lock_dialog import PinSetupDialog
        dialog = PinSetupDialog(parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._refresh_pin_status()

    def _disable_pin(self):
        from app.ui.pin_lock_dialog import PinLockDialog
        # Demander le PIN actuel d'abord
        lock = PinLockDialog(parent=self, allow_close=True)
        lock.setWindowTitle("Confirmer avec votre PIN")
        if lock.exec() != lock.DialogCode.Accepted:
            return

        reply = QMessageBox.question(
            self, "Désactiver le PIN",
            "Êtes-vous sûr de vouloir désactiver le verrouillage par PIN ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config.security.disable()
            config_manager.save()
            self._refresh_pin_status()
            QMessageBox.information(self, "PIN désactivé", "Le verrouillage PIN a été désactivé.")

    def _save(self):
        # Stratégie
        s = self.config.strategy
        s.risk_percent = self.risk_percent.value()
        s.risk_reward_ratio = self.risk_reward.value()
        s.atr_period = self.atr_period.value()
        s.atr_multiplier = self.atr_multiplier.value()
        s.max_consecutive_losses = self.max_consec_losses.value()
        s.max_daily_loss_percent = self.max_daily_loss.value()
        s.fast_ema = self.fast_ema.value()
        s.slow_ema = self.slow_ema.value()
        s.rsi_period = self.rsi_period.value()
        s.rsi_overbought = self.rsi_overbought.value()
        s.rsi_oversold = self.rsi_oversold.value()
        s.start_hour = self.start_hour.value()
        s.end_hour = self.end_hour.value()
        s.trade_on_friday = self.trade_friday.isChecked()
        s.min_bars_between_trades = self.min_bars.value()
        s.magic_number = self.magic_number.value()

        # MT5
        m = self.config.mt5
        m.auto_detect = self.mt5_auto.isChecked()
        m.terminal_path = self.mt5_path.text()
        m.login = self.mt5_login.value()
        m.password = self.mt5_password.text()
        m.server = self.mt5_server.text()
        self.config.broker_name = self.broker_name.text()

        # Telegram
        t = self.config.telegram
        t.enabled = self.tg_enabled.isChecked()
        t.token = self.tg_token.text()
        t.chat_id = self.tg_chat_id.text()
        t.alert_drawdown = self.alert_dd.isChecked()
        t.alert_drawdown_threshold = self.alert_dd_threshold.value()
        t.alert_consecutive_losses = self.alert_losses.isChecked()
        t.alert_position_open = self.alert_pos_open.isChecked()
        t.alert_position_close = self.alert_pos_close.isChecked()
        t.alert_news = self.alert_news.isChecked()
        t.alert_daily_report = self.alert_daily.isChecked()
        t.daily_report_hour = self.daily_hour.value()

        # News
        n = self.config.news
        n.enabled = self.news_enabled.isChecked()
        n.blackout_minutes_before = self.news_before.value()
        n.blackout_minutes_after = self.news_after.value()
        n.block_high_impact = self.block_high.isChecked()
        n.block_medium_impact = self.block_medium.isChecked()
        n.refresh_interval_minutes = self.news_refresh.value()

        # UI
        u = self.config.ui
        u.theme = "dark" if self.theme_combo.currentText() == "Sombre" else "light"
        u.refresh_interval_seconds = self.refresh_interval.value()
        u.minimize_to_tray = self.minimize_tray.isChecked()
        u.start_minimized = self.start_minimized.isChecked()
        u.auto_start_bot = self.auto_start_bot.isChecked()

        # Sécurité (PIN)
        sec = self.config.security
        sec.lock_on_startup = self.pin_lock_startup.isChecked()
        sec.require_pin_for_trading = self.pin_required_trading.isChecked()

        # Symboles depuis la table
        symbols = []
        for row in range(self.symbols_table.rowCount()):
            symbol_item = self.symbols_table.item(row, 0)
            timeframe_item = self.symbols_table.item(row, 1)
            enabled_item = self.symbols_table.item(row, 2)
            if symbol_item:
                symbols.append(SymbolConfig(
                    symbol=symbol_item.text(),
                    timeframe=timeframe_item.text() if timeframe_item else "H4",
                    enabled=(enabled_item.text() == "Oui") if enabled_item else True,
                ))
        if symbols:
            self.config.symbols = symbols

        config_manager.save(self.config)
        self.settings_saved.emit()

    def _reset_defaults(self):
        reply = QMessageBox.question(
            self, "Réinitialiser",
            "Remettre tous les paramètres aux valeurs par défaut ?\n"
            "Votre configuration actuelle sera écrasée.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from app.core.config_manager import AppConfig
            self.config = AppConfig()
            config_manager.config = self.config
            self._load_from_config()

    # ========================================================================
    # SYMBOLES
    # ========================================================================

    def _refresh_symbols_table(self):
        self.symbols_table.setRowCount(len(self.config.symbols))
        for i, sym in enumerate(self.config.symbols):
            self.symbols_table.setItem(i, 0, QTableWidgetItem(sym.symbol))
            self.symbols_table.setItem(i, 1, QTableWidgetItem(sym.timeframe))
            self.symbols_table.setItem(i, 2, QTableWidgetItem("Oui" if sym.enabled else "Non"))

    def _add_symbol(self):
        from PyQt6.QtWidgets import QInputDialog
        symbol, ok = QInputDialog.getText(self, "Ajouter un symbole",
                                           "Nom du symbole (ex: GBPUSD) :")
        if ok and symbol:
            timeframes = ['M15', 'M30', 'H1', 'H4', 'D1']
            tf, ok = QInputDialog.getItem(self, "Timeframe",
                                           "Sélectionner le timeframe :",
                                           timeframes, 3, False)
            if ok:
                row = self.symbols_table.rowCount()
                self.symbols_table.insertRow(row)
                self.symbols_table.setItem(row, 0, QTableWidgetItem(symbol.upper()))
                self.symbols_table.setItem(row, 1, QTableWidgetItem(tf))
                self.symbols_table.setItem(row, 2, QTableWidgetItem("Oui"))

    def _remove_symbol(self):
        current = self.symbols_table.currentRow()
        if current >= 0:
            self.symbols_table.removeRow(current)

    # ========================================================================
    # ACTIONS
    # ========================================================================

    def _browse_mt5(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner terminal64.exe",
            "C:/Program Files", "Exécutables (*.exe)"
        )
        if path:
            self.mt5_path.setText(path)

    def _test_telegram(self):
        # Sauvegarder d'abord les valeurs
        token = self.tg_token.text()
        chat_id = self.tg_chat_id.text()
        if not token or not chat_id:
            QMessageBox.warning(self, "Test Telegram",
                              "Renseignez le token et le chat ID avant de tester.")
            return

        try:
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            from bot.telegram_alerts import AlertSystem
            alerts = AlertSystem(token=token, chat_id=chat_id)
            if alerts.test():
                QMessageBox.information(self, "Test Telegram",
                                       "Message de test envoyé avec succès !")
            else:
                QMessageBox.warning(self, "Test Telegram",
                                   "Échec de l'envoi. Vérifiez le token et le chat ID.")
        except Exception as e:
            QMessageBox.critical(self, "Test Telegram", f"Erreur : {e}")

    def _save_profile(self):
        name = self.new_profile_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Profil", "Donnez un nom au profil.")
            return
        self._save()  # Sauvegarde d'abord la config actuelle
        config_manager.save_profile(name)
        QMessageBox.information(self, "Profil", f"Profil '{name}' sauvegardé.")
        self.new_profile_name.clear()
        self._refresh_profiles_list()

    def _load_profile(self):
        current = self.profiles_list.currentRow()
        if current < 0:
            return
        item = self.profiles_list.item(current, 0)
        if item:
            name = item.text()
            if config_manager.load_profile(name):
                self.config = config_manager.config
                self._load_from_config()
                QMessageBox.information(self, "Profil", f"Profil '{name}' chargé.")

    def _refresh_profiles_list(self):
        profiles = config_manager.list_profiles()
        self.profiles_list.setRowCount(len(profiles))
        for i, name in enumerate(profiles):
            self.profiles_list.setItem(i, 0, QTableWidgetItem(name))

    def refresh(self):
        pass
