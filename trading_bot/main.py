"""
Point d'entrée de SafeTrendBot
Application desktop Windows/Linux pour trading automatisé
"""

import sys
import os
from pathlib import Path

# Ajout du répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor


def check_dependencies():
    """Vérifie les dépendances critiques"""
    missing = []
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        import requests
    except ImportError:
        missing.append("requests")

    # MT5 n'est pas critique pour lancer l'UI (on vérifie à l'utilisation)
    if missing:
        return False, missing
    return True, []


def create_app_icon() -> QIcon:
    """Crée une icône simple par programmation"""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor('#2563eb'))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(QColor('white'))
    painter.setBrush(QColor('white'))
    # Dessiner un "S" stylisé ou juste un graphique simple
    from PyQt6.QtGui import QFont
    painter.setFont(QFont("Arial", 28, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")
    painter.end()
    return QIcon(pixmap)


def main():
    # Configuration high-DPI
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

    app = QApplication(sys.argv)
    app.setApplicationName("SafeTrendBot")
    app.setOrganizationName("SafeTrendBot")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(False)  # Important pour le system tray
    app.setWindowIcon(create_app_icon())

    # Vérifier les dépendances
    ok, missing = check_dependencies()
    if not ok:
        QMessageBox.critical(
            None, "Dépendances manquantes",
            f"Les modules suivants sont requis :\n\n"
            f"{', '.join(missing)}\n\n"
            f"Installez-les avec :\n"
            f"pip install {' '.join(missing)}"
        )
        return 1

    # Afficher un avertissement si MT5 non dispo sur Windows
    try:
        import MetaTrader5  # noqa
    except ImportError:
        if sys.platform == 'win32':
            QMessageBox.warning(
                None, "MetaTrader5 non détecté",
                "Le package MetaTrader5 n'est pas installé.\n\n"
                "Le bot ne pourra pas exécuter de trades tant qu'il n'est pas installé.\n"
                "Les autres fonctions (backtest, news, calendrier) restent disponibles.\n\n"
                "Installer avec : pip install MetaTrader5"
            )

    from app.core.config_manager import config_manager
    from app.ui.theme import apply_dark_theme, apply_light_theme

    # Appliquer le thème AVANT de créer la fenêtre
    theme = (config_manager.config.ui.theme or "dark").lower()
    if theme == "light":
        apply_light_theme(app)
    else:
        apply_dark_theme(app)

    # Verrouillage PIN au démarrage si activé
    if (config_manager.config.security.enabled and
            config_manager.config.security.lock_on_startup):
        from app.ui.pin_lock_dialog import PinLockDialog
        lock = PinLockDialog(allow_close=False)
        if lock.exec() != lock.DialogCode.Accepted:
            return 1  # PIN annulé = on quitte

    # Import APRÈS l'application du thème
    from app.ui.main_window import MainWindow
    window = MainWindow(engine_version='v4')

    if config_manager.config.ui.start_minimized:
        window.hide()
    else:
        window.show()

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
