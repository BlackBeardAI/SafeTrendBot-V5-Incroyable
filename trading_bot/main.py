"""
SafeTrendBot V5 — Point d'entrée principal
=========================================

Bot de trading automatisé avec système de licence à usage unique,
chiffrement AES-256, watermark, et mises à jour automatiques.

Sécurité intégrée:
- Licence pré-injectée, hardware-locked (1 PC = 1 licence)
- Anti-tamper (détecte debug/VM)
- Chiffrement AES-256 des données
- Watermark invisible dans les résultats
- Auto-update depuis le serveur admin
- Messages broadcast de l'admin
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG DU DASHBOARD ADMIN (pour broadcast et updates)
# ─────────────────────────────────────────────────────────────────────────────

# URL du dashboard admin (à configurer lors du build)
ADMIN_DASHBOARD_URL = os.environ.get("SAFETRENDBOT_ADMIN_URL", "https://217.160.191.107:8443")


# ─────────────────────────────────────────────────────────────────────────────
# VÉRIFICATION LICENCE V2 (obligatoire)
# ─────────────────────────────────────────────────────────────────────────────

def check_license_v2():
    """
    Vérifie la licence V2 pré-injectée dans le build.
    Cette licence est liée au hardware (1 PC uniquement).
    """
    from app.core.license_manager_v2 import LicenseManagerV2, LicenseStatus
    from app.core.anti_tamper import AntiTamper

    # 1. Anti-tamper
    try:
        at = AntiTamper()
        at.raise_if_tampered()
    except RuntimeError as e:
        QMessageBox.critical(None, "🛡️ Sécurité", str(e))
        sys.exit(1)

    # 2. License Manager V2
    lm = LicenseManagerV2()
    status = lm.check_license()

    if status == LicenseStatus.VALID:
        print(f"[LICENSE] ✅ Licence validée: {lm.license_key[:12]}...")
        return lm

    elif status == LicenseStatus.FIRST_USE:
        print(f"[LICENSE] 🆓 Première activation: {lm.license_key}")
        reply = QMessageBox.question(
            None, "Première activation",
            f"Bienvenue dans SafeTrendBot V5!\n\n"
            f"Licence: {lm.license_key}\n"
            f"Hardware: {lm.hardware_id[:20]}...\n\n"
            f"Ce bot sera activé sur CET ordinateur uniquement.\n"
            f"Le fichier d'installation sera supprimé après activation.\n\n"
            f"Continuer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = lm.activate()
            if ok:
                QMessageBox.information(
                    None, "✅ Activation réussie",
                    "SafeTrendBot est maintenant activé!\n\n"
                    "Ce bot ne fonctionnera que sur cet ordinateur.\n"
                    "En cas de réinstallation, contactez le support."
                )
                return lm
            else:
                QMessageBox.critical(None, "❌ Échec", "L'activation a échoué.")
                sys.exit(1)
        else:
            sys.exit(0)

    elif status == LicenseStatus.ALREADY_USED:
        QMessageBox.critical(
            None, "❌ Licence déjà utilisée",
            "Cette licence a déjà été activée sur un autre ordinateur.\n\n"
            "Chaque licence est à usage unique et liée au matériel.\n"
            "Contactez le support pour obtenir une nouvelle licence."
        )
        sys.exit(1)

    elif status == LicenseStatus.INVALID:
        QMessageBox.critical(
            None, "❌ Licence invalide",
            "Ce build de SafeTrendBot n'est pas autorisé.\n\n"
            "Assurez-vous d'utiliser un build officiel."
        )
        sys.exit(1)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# CHIFFREMENT DES DONNÉES
# ─────────────────────────────────────────────────────────────────────────────

def init_encryption():
    """Initialise le chiffrement des données locales."""
    try:
        from app.core.encryption import get_vault_password, encrypt_sensitive_data
        password = get_vault_password()
        print(f"[CRYPTO] 🔐 Vault initialisé")
        return True
    except Exception as e:
        print(f"[CRYPTO] ⚠️ Chiffrement non disponible: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# WATERMARK
# ─────────────────────────────────────────────────────────────────────────────

def init_watermark(license_key: str, tier: str):
    """Initialise le watermark pour les rapports."""
    try:
        from app.core.watermark import WatermarkManager
        wm = WatermarkManager(license_key, tier=tier)
        print(f"[WATERMARK] 🏷️ Traçage activé: {wm._watermark_hash}")
        return wm
    except Exception as e:
        print(f"[WATERMARK] ⚠️ Non disponible: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# BROADCAST CLIENT (messages admin)
# ─────────────────────────────────────────────────────────────────────────────

def check_broadcasts(tier: str):
    """Vérifie les messages broadcast de l'admin."""
    try:
        from app.core.broadcast_client import BroadcastClient
        bc = BroadcastClient(tier)
        messages = bc.get_active_broadcasts()
        if messages:
            for msg in messages:
                bc.show_notification(msg)
    except Exception as e:
        print(f"[BROADCAST] ⚠️ {e}")


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-UPDATE
# ─────────────────────────────────────────────────────────────────────────────

def check_for_updates(current_version: str, tier: str):
    """Vérifie les mises à jour disponibles."""
    try:
        from app.core.auto_updater import AutoUpdater
        updater = AutoUpdater(current_version, tier)
        if updater.check_update():
            print(f"[UPDATE] 📢 Nouvelle version: v{updater.new_version}")
            # En mode GUI, afficher une notification
            # Ici on log seulement, l'update se fait avec --update
    except Exception as e:
        print(f"[UPDATE] ⚠️ {e}")


# ─────────────────────────────────────────────────────────────────────────────
# ICÔNE
# ─────────────────────────────────────────────────────────────────────────────

def create_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor('#2563eb'))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
    painter.setPen(QColor('white'))
    painter.setFont(QFont("Arial", 28, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")
    painter.end()
    return QIcon(pixmap)


# ─────────────────────────────────────────────────────────────────────────────
# DÉPENDANCES
# ─────────────────────────────────────────────────────────────────────────────

def check_dependencies():
    missing = []
    for mod in ["PyQt6", "numpy", "requests"]:
        try:
            __import__(mod.lower())
        except ImportError:
            missing.append(mod)
    return len(missing) == 0, missing


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'

    app = QApplication(sys.argv)
    app.setApplicationName("SafeTrendBot")
    app.setOrganizationName("SafeTrendBot")
    app.setApplicationVersion("5.3.0")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(create_app_icon())

    print("=" * 50)
    print("🤖 SafeTrendBot V5 — Démarrage")
    print("=" * 50)

    # 1. Vérification licence (bloquant)
    lm = check_license_v2()
    if not lm:
        sys.exit(1)

    # 2. Chiffrement
    init_encryption()

    # 3. Watermark
    wm = init_watermark(lm.license_key, "basic")

    # 4. Broadcasts admin
    check_broadcasts("basic")

    # 5. Mise à jour
    check_for_updates("5.3.0", "basic")

    # 6. Dépendances
    ok, missing = check_dependencies()
    if not ok:
        QMessageBox.critical(
            None, "Dépendances manquantes",
            f"Modules requis: {', '.join(missing)}\n\n"
            f"pip install {' '.join(missing)}"
        )
        return 1

    # 7. Theme
    from app.core.config_manager import config_manager
    from app.ui.theme import apply_dark_theme
    apply_dark_theme(app)

    # 8. PIN lock
    if (config_manager.config.security.enabled and
            config_manager.config.security.lock_on_startup):
        from app.ui.pin_lock_dialog import PinLockDialog
        lock = PinLockDialog(allow_close=False)
        if lock.exec() != lock.DialogCode.Accepted:
            return 1

    # 9. Main window
    from app.ui.main_window import MainWindow
    window = MainWindow(engine_version='v4')
    window.show()

    print("✅ SafeTrendBot V5 prêt!")
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
