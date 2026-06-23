"""
Fenêtre principale de l'application SafeTrendBot.
Interface desktop complète avec sidebar et 6 vues.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QFrame, QSystemTrayIcon, QMenu,
    QStatusBar, QMessageBox, QApplication, QDialog, QDialogButtonBox,
    QTextEdit
)
from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont, QKeySequence, QShortcut

from app.core.config_manager import config_manager
from app.core.bot_types import BotState, BotStatus
from app.core.trading_engine_v4 import TradingEngineV4
from app.core.system_tray_manager import SystemTrayManager
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.positions_view import PositionsView
from app.ui.views.backtest_view import BacktestView
from app.ui.views.calendar_view import CalendarView
from app.ui.views.news_view import NewsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.logs_view import LogsView
from app.ui.views.analytics_view import AnalyticsView
from app.ui.views.paper_trading_view import PaperTradingView
from app.ui.views.broker_view import BrokerView
from app.ui.views.telegram_view import TelegramView
from app.ui.views.market_hours_view import MarketHoursView
from app.ui.views.profiles_view import TradingProfilesView
from app.ui.views.trend_analysis_view import TrendAnalysisView
from app.ui.views.tools_view import ToolsView
from app.ui.views.watchlist_view import WatchlistView
from app.ui.views.recommendations_view import RecommendationsView
from app.ui.views.strategy_params_view import StrategyParamsView
from app.ui.theme import apply_dark_theme, apply_light_theme, COLORS
import logging

logger = logging.getLogger("main_window")


class SidebarButton(QPushButton):
    """Bouton de la sidebar avec icône et texte"""
    def __init__(self, icon_char: str, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarButton")
        self.setCheckable(True)
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Texte avec icône à l'intérieur du bouton
        self.setText(f"  {icon_char}   {text}")
        self.setFont(QFont("Segoe UI", 10))


class StatusIndicator(QLabel):
    """Indicateur visuel de l'état du bot (pastille colorée)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor(COLORS['text_secondary'])

    def set_state(self, state: BotState):
        colors = {
            BotState.STOPPED: QColor("#6c757d"),
            BotState.STARTING: QColor("#ffc107"),
            BotState.RUNNING: QColor("#28a745"),
            BotState.PAUSED: QColor("#ffc107"),
            BotState.ERROR: QColor("#dc3545"),
        }
        self._color = colors.get(state, QColor("#6c757d"))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self._color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self.width() - 1, self.height() - 1)


class MainWindow(QMainWindow):
    def __init__(self, engine_version='v4'):
        super().__init__()
        self.engine_version = engine_version
        self.setWindowTitle("SafeTrendBot V5 — Trading Automation Platform")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        # Application du thème
        if config_manager.config.ui.theme == 'dark':
            apply_dark_theme(QApplication.instance())
        else:
            apply_light_theme(QApplication.instance())

        # Moteur de trading V4
        if engine_version == 'v4':
            self.engine = TradingEngineV4()
        else:
            self.engine = TradingEngineV4()
        
        self.engine.status_changed.connect(self._on_status_changed)
        self.engine.log_message.connect(self._on_log_message)
        self.engine.error_occurred.connect(self._on_error)

        # Construction de l'UI
        self._build_ui()
        self._build_system_tray()
        self._build_status_bar()

        # Raccourcis clavier
        self._setup_shortcuts()

        # Timer de rafraîchissement global
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_views)
        self._refresh_timer.start(config_manager.config.ui.refresh_interval_seconds * 1000)

        # Démarrage auto si configuré
        if config_manager.config.ui.auto_start_bot:
            QTimer.singleShot(1000, self.start_bot)

    # ========================================================================
    # RACCOURCIS CLAVIER
    # ========================================================================

    def _setup_shortcuts(self):
        """Configure les raccourcis clavier globaux de la fenêtre."""
        # Ctrl+S : Démarrer le bot
        sc_start = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_start.activated.connect(self.start_bot)
        sc_start.setWhatsThis("Démarrer le bot")

        # Ctrl+X : Arrêter le bot
        sc_stop = QShortcut(QKeySequence("Ctrl+X"), self)
        sc_stop.activated.connect(self.stop_bot)
        sc_stop.setWhatsThis("Arrêter le bot")

        # Ctrl+P : Pause / Resume (toggle)
        sc_pause = QShortcut(QKeySequence("Ctrl+P"), self)
        sc_pause.activated.connect(self._toggle_pause)
        sc_pause.setWhatsThis("Pause/Resume le bot")

        # Ctrl+B : Ouvrir vue backtest
        sc_backtest = QShortcut(QKeySequence("Ctrl+B"), self)
        sc_backtest.activated.connect(lambda: self._switch_view(7))
        sc_backtest.setWhatsThis("Ouvrir la vue Backtest")

        # Ctrl+D : Ouvrir vue dashboard
        sc_dashboard = QShortcut(QKeySequence("Ctrl+D"), self)
        sc_dashboard.activated.connect(lambda: self._switch_view(0))
        sc_dashboard.setWhatsThis("Ouvrir la vue Tableau de bord")

        # F1 : Aide
        sc_help = QShortcut(QKeySequence("F1"), self)
        sc_help.activated.connect(self._show_help)
        sc_help.setWhatsThis("Afficher l'aide")

    def _toggle_pause(self):
        """Bascule entre pause et resume selon l'état courant du bot."""
        if not hasattr(self, 'engine') or self.engine is None:
            return
        state = getattr(self.engine, 'state', None)
        if state == BotState.RUNNING:
            self.engine.pause()
            self.statusBar().showMessage("Bot mis en pause (Ctrl+P pour reprendre)", 3000)
        elif state == BotState.PAUSED:
            self.engine.resume()
            self.statusBar().showMessage("Bot repris (Ctrl+P pour pause)", 3000)
        else:
            self.statusBar().showMessage(
                f"Le bot doit être actif pour basculer pause/resume (état: {state})", 3000
            )

    def _show_help(self):
        """Affiche la fenêtre d'aide avec la liste des raccourcis."""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("SafeTrendBot V5 — Aide & Raccourcis")
        help_dialog.setMinimumSize(520, 420)

        layout = QVBoxLayout(help_dialog)

        title = QLabel("⌨️  Raccourcis clavier")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        shortcuts_text.setHtml("""
        <h3>Raccourcis clavier</h3>
        <table cellpadding='6'>
        <tr><td><b>Ctrl+S</b></td><td>Démarrer le bot</td></tr>
        <tr><td><b>Ctrl+X</b></td><td>Arrêter le bot</td></tr>
        <tr><td><b>Ctrl+P</b></td><td>Pause / Resume le bot</td></tr>
        <tr><td><b>Ctrl+B</b></td><td>Ouvrir la vue Backtest</td></tr>
        <tr><td><b>Ctrl+D</b></td><td>Ouvrir la vue Tableau de bord</td></tr>
        <tr><td><b>F1</b></td><td>Afficher cette aide</td></tr>
        </table>
        <br>
        <h3>Navigation</h3>
        <p>Utilisez la sidebar à gauche pour naviguer entre les vues.</p>
        <br>
        <h3>Sécurité</h3>
        <p>Par défaut, le bot démarre en mode <b>Paper Trading</b> (simulation).<br>
        Pour passer en mode <b>Live</b>, configurez votre broker dans la vue Broker
        puis changez le mode dans les Paramètres.</p>
        <br>
        <h3>Astuces</h3>
        <p>• L'icône système permet de contrôler le bot sans ouvrir la fenêtre.<br>
        • Les profils de trading permettent de basculer rapidement entre configurations.<br>
        • Le backtest permet de tester votre stratégie sur données historiques.</p>
        """)
        layout.addWidget(shortcuts_text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(help_dialog.accept)
        layout.addWidget(buttons)

        help_dialog.exec()

    # ========================================================================
    # CONSTRUCTION UI
    # ========================================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_content())

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 12)
        layout.setSpacing(4)

        # Logo / titre avec bouton thème
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(0)

        title = QLabel("SafeTrendBot")
        title.setObjectName("SidebarTitle")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_box.addWidget(title)

        subtitle = QLabel("Trading Platform")
        subtitle.setObjectName("SidebarSubtitle")
        subtitle.setFont(QFont("Segoe UI", 9))
        title_box.addWidget(subtitle)

        title_row.addLayout(title_box, 1)

        # Bouton bascule thème
        current_theme = config_manager.config.ui.theme or "dark"
        self.theme_btn = QPushButton("☀" if current_theme == "dark" else "🌙")
        self.theme_btn.setObjectName("ThemeButton")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setToolTip("Changer de thème (clair/sombre)")
        self.theme_btn.clicked.connect(self._toggle_theme)
        title_row.addWidget(self.theme_btn, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(title_row)

        # Contrôles bot
        self.btn_start = QPushButton("▶  Démarrer le bot")
        self.btn_start.setObjectName("StartButton")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_bot)
        layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■  Arrêter")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_bot)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_stop)

        layout.addSpacing(24)

        # Navigation
        nav_label = QLabel("NAVIGATION")
        nav_label.setObjectName("SidebarSection")
        nav_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        layout.addWidget(nav_label)
        layout.addSpacing(8)

        self.nav_buttons = []
        nav_items = [
            ("📊", "Tableau de bord",       0),
            ("💡", "Recommandations",       1),
            ("📈", "Positions",             2),
            ("📑", "Analyses",              3),
            ("🎯", "Profils trading",       4),
            ("🔧", "Params stratégie",      5),
            ("📉", "Tendances 5 ans",       6),
            ("🧪", "Backtest",              7),
            ("🎮", "Paper Trading",         8),
            ("🛠️", "Outils",                9),
            ("👁️", "Watchlist",            10),
            ("🏦", "Broker",               11),
            ("📱", "Telegram",             12),
            ("🕐", "Horaires marchés",     13),
            ("📅", "Calendrier éco",       14),
            ("📰", "Actualités",           15),
            ("📋", "Journaux",             16),
            ("⚙️", "Paramètres",           17),
        ]
        for icon, text, idx in nav_items:
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda checked, i=idx: self._switch_view(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        # Sélectionner le premier
        self.nav_buttons[0].setChecked(True)

        layout.addStretch()

        # Indicateur de statut broker (toujours visible)
        from app.ui.widgets_status import BrokerStatusIndicator
        self.broker_indicator = BrokerStatusIndicator(engine=self.engine)
        self.broker_indicator.setStyleSheet(f"""
            BrokerStatusIndicator {{
                background-color: {COLORS['bg_secondary']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        layout.addWidget(self.broker_indicator)

        # Mise à jour du numéro de version pour V5
        version = QLabel("Version 5.0.0")
        version.setFont(QFont("Segoe UI", 8))
        version.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 12px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        return sidebar

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        # Création des vues
        self.dashboard_view       = DashboardView(self.engine)
        self.recommendations_view = RecommendationsView(self.engine)
        self.positions_view       = PositionsView(self.engine)
        self.analytics_view       = AnalyticsView(self.engine)
        self.profiles_view        = TradingProfilesView()
        self.strategy_params_view = StrategyParamsView()
        self.trend_view           = TrendAnalysisView()
        self.backtest_view        = BacktestView()
        self.paper_trading_view   = PaperTradingView(self.engine)
        self.tools_view           = ToolsView(self.engine)
        self.watchlist_view       = WatchlistView(self.engine)
        self.broker_view          = BrokerView()
        self.telegram_view        = TelegramView(self.engine)
        self.market_hours_view    = MarketHoursView()
        self.calendar_view        = CalendarView()
        self.news_view            = NewsView()
        self.logs_view            = LogsView()
        self.settings_view        = SettingsView()

        self.engine.log_message.connect(self.logs_view.add_log)
        self.settings_view.settings_saved.connect(self._on_settings_saved)
        self.recommendations_view.navigate_to.connect(self._navigate_from_recommendation)

        self.stack.addWidget(self.dashboard_view)        #  0
        self.stack.addWidget(self.recommendations_view)  #  1
        self.stack.addWidget(self.positions_view)        #  2
        self.stack.addWidget(self.analytics_view)        #  3
        self.stack.addWidget(self.profiles_view)         #  4
        self.stack.addWidget(self.strategy_params_view)  #  5
        self.stack.addWidget(self.trend_view)            #  6
        self.stack.addWidget(self.backtest_view)         #  7
        self.stack.addWidget(self.paper_trading_view)    #  8
        self.stack.addWidget(self.tools_view)            #  9
        self.stack.addWidget(self.watchlist_view)        # 10
        self.stack.addWidget(self.broker_view)           # 11
        self.stack.addWidget(self.telegram_view)         # 12
        self.stack.addWidget(self.market_hours_view)     # 13
        self.stack.addWidget(self.calendar_view)         # 14
        self.stack.addWidget(self.news_view)             # 15
        self.stack.addWidget(self.logs_view)             # 16
        self.stack.addWidget(self.settings_view)         # 17

        layout.addWidget(self.stack)
        return container

    def _build_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Indicateur d'état
        self.status_indicator = StatusIndicator()
        status_bar.addWidget(self.status_indicator)

        self.status_label = QLabel("Bot arrêté")
        self.status_label.setFont(QFont("Segoe UI", 9))
        status_bar.addWidget(self.status_label)

        status_bar.addPermanentWidget(QLabel(""))  # spacer

        self.account_label = QLabel("")
        self.account_label.setFont(QFont("Segoe UI", 9))
        status_bar.addPermanentWidget(self.account_label)

        # Connexion à l'update du compte
        self.engine.account_updated.connect(self._on_account_updated)

    def _build_system_tray(self):
        """Icône système V5 avec mini dashboard et contrôles rapides"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = SystemTrayManager(self)
        self.tray.show()
        
        # Connexions V5
        self.tray.start_requested.connect(self.start_bot)
        self.tray.stop_requested.connect(self.stop_bot)
        self.tray.pause_requested.connect(self.engine.pause)
        self.tray.resume_requested.connect(self.engine.resume)
        self.tray.show_window_requested.connect(self.show_window)
        
        # Connecter les nouveaux signaux V4 au tray
        if hasattr(self.engine, 'regime_changed'):
            self.engine.regime_changed.connect(self._on_regime_changed)
        if hasattr(self.engine, 'performance_updated'):
            self.engine.performance_updated.connect(self._on_performance_updated)
        if hasattr(self.engine, 'status_changed'):
            self.engine.status_changed.connect(self.tray.update_status)

    def _on_regime_changed(self, regime, confidence, reasons):
        if hasattr(self, 'tray') and self.tray:
            self.tray.setToolTip(f"SafeTrendBot V5\nRégime: {regime} ({confidence:.0%})")

    def _on_performance_updated(self, perf):
        pass

    # ========================================================================
    # NAVIGATION
    # ========================================================================

    def _switch_view(self, index: int):
        """Change la vue active"""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)

    def _navigate_from_recommendation(self, target: str):
        target_map = {
            "dashboard": 0,  "recs": 1,      "positions": 2,
            "analytics": 3,  "profiles": 4,  "strategy": 5,
            "trend":     6,  "backtest": 7,  "paper": 8,
            "tools":     9,  "watchlist":10, "broker": 11,
            "telegram": 12,  "hours": 13,    "calendar": 14,
            "news":     15,  "logs": 16,     "settings": 17,
        }
        if target == "start":
            self.start_bot()
        elif target in target_map:
            self._switch_view(target_map[target])

    def _toggle_theme(self):
        """Bascule entre clair et sombre - redémarre l'application"""
        current = config_manager.config.ui.theme or "dark"
        new_theme = "light" if current == "dark" else "dark"

        reply = QMessageBox.question(
            self, "Changer de thème",
            f"Passer en thème {'clair' if new_theme == 'light' else 'sombre'} ?\n\n"
            "L'application va redémarrer pour appliquer le nouveau thème.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        config_manager.config.ui.theme = new_theme
        config_manager.save()

        # Redémarrer l'application
        import sys, os
        try:
            # Arrêter le bot si en cours
            if self.engine and self.engine.state != BotState.STOPPED:
                self.engine.stop()

            python = sys.executable
            # Fermer proprement puis relancer
            QTimer.singleShot(100, lambda: os.execl(python, python, *sys.argv))
            self.close()
        except Exception as e:
            QMessageBox.information(
                self, "Redémarrage requis",
                f"Fermez et relancez l'application pour appliquer le thème {new_theme}.\n\n"
                f"(Erreur redémarrage auto : {e})"
            )

    # ========================================================================
    # CONTRÔLE DU BOT
    # ========================================================================

    def start_bot(self):
        # Vérification PIN si trading verrouillé
        sec = config_manager.config.security
        if sec.enabled and sec.require_pin_for_trading:
            from app.ui.pin_lock_dialog import PinLockDialog
            lock = PinLockDialog(parent=self, allow_close=True)
            lock.setWindowTitle("PIN requis pour démarrer le bot")
            if lock.exec() != lock.DialogCode.Accepted:
                return  # PIN annulé/incorrect

        self.btn_start.setEnabled(False)
        if self.engine.start():
            self.btn_stop.setEnabled(True)
            if self.tray:
                self.tray.showMessage(
                    "SafeTrendBot", "Bot démarré",
                    QSystemTrayIcon.MessageIcon.Information, 3000
                )
        else:
            self.btn_start.setEnabled(True)

    def stop_bot(self):
        reply = QMessageBox.question(
            self, "Arrêt du bot",
            "Êtes-vous sûr de vouloir arrêter le bot ?\n"
            "Les positions ouvertes ne seront pas fermées automatiquement.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.stop()
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

    # ========================================================================
    # SLOTS
    # ========================================================================

    @pyqtSlot(object)
    def _on_status_changed(self, status: BotStatus):
        """Met à jour l'indicateur d'état"""
        self.status_indicator.set_state(status.state)
        messages = {
            BotState.STOPPED: "Bot arrêté",
            BotState.STARTING: "Démarrage...",
            BotState.RUNNING: f"Bot actif — {len(status.active_symbols)} symboles surveillés",
            BotState.PAUSED: "Bot en pause",
            BotState.ERROR: "Erreur",
        }
        self.status_label.setText(messages.get(status.state, ""))
        self.dashboard_view.update_status(status)

    @pyqtSlot(dict)
    def _on_account_updated(self, info: dict):
        balance = info.get('balance', 0)
        equity = info.get('equity', 0)
        currency = info.get('currency', '')
        self.account_label.setText(
            f"Balance: {balance:,.2f} {currency}  │  "
            f"Équité: {equity:,.2f} {currency}"
        )
        self.dashboard_view.update_account(info)

    @pyqtSlot(str, str)
    def _on_log_message(self, level: str, message: str):
        """Les logs sont déjà reliés à logs_view directement"""
        pass

    @pyqtSlot(str)
    def _on_error(self, error: str):
        QMessageBox.warning(self, "Erreur", error)

    @pyqtSlot()
    def _on_settings_saved(self):
        # Recharger la config
        config_manager.config = config_manager.load()
        self.engine.config = config_manager.config
        QMessageBox.information(self, "Paramètres", "Paramètres sauvegardés. "
                                "Certains changements nécessitent un redémarrage du bot.")

    # ========================================================================
    # RAFRAÎCHISSEMENT
    # ========================================================================

    def _refresh_views(self):
        """Appelle le refresh sur la vue active"""
        current = self.stack.currentWidget()
        if hasattr(current, 'refresh'):
            try:
                current.refresh()
            except Exception as e:
                logger.warning(f"Erreur refresh : {e}")

    # ========================================================================
    # SYSTEM TRAY / FERMETURE
    # ========================================================================

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if config_manager.config.ui.minimize_to_tray and self.tray:
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "SafeTrendBot",
                "L'application continue de tourner. Clic droit sur l'icône pour quitter.",
                QSystemTrayIcon.MessageIcon.Information, 3000
            )
        else:
            self._quit_application()

    def _quit_application(self):
        if self.engine.state != BotState.STOPPED:
            self.engine.stop()
        if self.tray:
            self.tray.hide()
        QApplication.quit()
