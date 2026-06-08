"""
Gestionnaire de la barre des tâches (System Tray).
Mini dashboard rapide accessible depuis l'icône.
"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidgetAction, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal


class TrayDashboard(QWidget):
    """Mini popup affiché au clic sur le tray"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self.title = QLabel("SafeTrendBot V5")
        self.title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(self.title)

        self.status = QLabel("● Arrêté")
        layout.addWidget(self.status)

        self.regime = QLabel("Régime : —")
        layout.addWidget(self.regime)

        self.pnl = QLabel("P&L Jour : —")
        layout.addWidget(self.pnl)

        self.positions = QLabel("Positions : —")
        layout.addWidget(self.positions)

        self.sharpe = QLabel("Sharpe : —")
        layout.addWidget(self.sharpe)

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                border-radius: 12px;
                border: 1px solid #313244;
            }
            QLabel {
                color: #cdd6f4;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QLabel#title {
                color: #cba6f7;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def update_data(self, status):
        state_colors = {
            "running": "#a6e3a1", "stopped": "#f38ba8", "paused": "#f9e2af",
            "halted": "#f38ba8", "error": "#f38ba8", "starting": "#89b4fa",
        }
        color = state_colors.get(status.state.value, "#cdd6f4")
        self.status.setText(f'<span style="color:{color}">●</span> {status.state.value.upper()}')
        self.regime.setText(f"Régime : {status.current_regime} ({status.regime_confidence:.0%})")
        self.pnl.setText(f"P&L Jour : {status.today_pnl:+.2f}")
        self.positions.setText(f"Positions : {status.open_positions}")
        self.sharpe.setText(f"Sharpe : {status.sharpe}")


class SystemTrayManager(QSystemTrayIcon):
    """Tray icon avec mini dashboard et contrôles rapides"""

    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    show_window_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(self._create_tray_icon())
        self.setToolTip("SafeTrendBot V5")
        self.activated.connect(self._on_activated)

        self.menu = QMenu(parent)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                color: #cdd6f4;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #313244;
            }
            QMenu::separator {
                height: 1px;
                background-color: #313244;
                margin: 4px 8px;
            }
        """)

        self._build_menu()
        self.setContextMenu(self.menu)

        self._dashboard = TrayDashboard()

    def _create_tray_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor('#cba6f7'))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
        painter.setPen(QColor('#1e1e2e'))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")
        painter.end()
        return QIcon(pixmap)

    def _build_menu(self):
        self.status_action = QAction("● Arrêté", self)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()

        self.start_action = QAction("▶ Démarrer", self)
        self.start_action.triggered.connect(self.start_requested.emit)
        self.menu.addAction(self.start_action)

        self.stop_action = QAction("⏹ Arrêter", self)
        self.stop_action.triggered.connect(self.stop_requested.emit)
        self.stop_action.setVisible(False)
        self.menu.addAction(self.stop_action)

        self.pause_action = QAction("⏸ Pause", self)
        self.pause_action.triggered.connect(self.pause_requested.emit)
        self.pause_action.setVisible(False)
        self.menu.addAction(self.pause_action)

        self.resume_action = QAction("▶ Reprendre", self)
        self.resume_action.triggered.connect(self.resume_requested.emit)
        self.resume_action.setVisible(False)
        self.menu.addAction(self.resume_action)

        self.menu.addSeparator()
        show_action = QAction("🪟 Ouvrir la fenêtre", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        self.menu.addAction(show_action)

        quit_action = QAction("❌ Quitter", self)
        quit_action.triggered.connect(lambda: self.parent().close() if self.parent() else None)
        self.menu.addAction(quit_action)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Clic gauche : afficher le mini dashboard
            geo = self.geometry()
            self._dashboard.move(geo.x() - 150, geo.y() - 200)
            self._dashboard.show()

    def update_status(self, status):
        state = status.state.value
        self.status_action.setText(f"● {state.upper()}")
        self._dashboard.update_data(status)

        running = state == "running"
        paused = state == "paused"
        stopped = state == "stopped"
        halted = state == "halted"

        self.start_action.setVisible(stopped or halted)
        self.stop_action.setVisible(running or paused)
        self.pause_action.setVisible(running)
        self.resume_action.setVisible(paused or halted)

        # Tooltip enrichi
        tooltip = (f"SafeTrendBot V5\n"
                   f"État : {state.upper()}\n"
                   f"Régime : {status.current_regime}\n"
                   f"P&L : {status.today_pnl:+.2f}\n"
                   f"Positions : {status.open_positions}")
        self.setToolTip(tooltip)
