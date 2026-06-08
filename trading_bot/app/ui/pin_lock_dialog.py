"""
Dialog modal de verrouillage par PIN.
Affiché au démarrage si PIN activé, ou pour déverrouiller après inactivité.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import time

from app.ui.theme import COLORS
from app.core.config_manager import config_manager


class PinLockDialog(QDialog):
    """Dialog modal pour entrer le PIN."""

    unlocked = pyqtSignal()

    def __init__(self, parent=None, allow_close=False):
        super().__init__(parent)
        self.allow_close = allow_close
        self.attempts = 0
        self._build()

        # Empêcher la fermeture par X si pas autorisé
        if not allow_close:
            self.setWindowFlags(
                Qt.WindowType.Dialog |
                Qt.WindowType.CustomizeWindowHint |
                Qt.WindowType.WindowTitleHint
            )

        self.setModal(True)
        self.setMinimumWidth(360)

    def _build(self):
        self.setWindowTitle("🔒 SafeTrendBot verrouillé")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # Titre
        title = QLabel("🔒 Verrouillé")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Entrez votre code PIN pour déverrouiller")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Champ PIN
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setMaxLength(12)
        self.pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pin_input.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.pin_input.setMinimumHeight(44)
        self.pin_input.setPlaceholderText("●●●●")
        self.pin_input.returnPressed.connect(self._check_pin)
        layout.addWidget(self.pin_input)

        # Pavé numérique
        keypad = QGridLayout()
        keypad.setSpacing(8)

        digits = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('⌫', 3, 0), ('0', 3, 1), ('✓', 3, 2),
        ]
        for label, row, col in digits:
            btn = QPushButton(label)
            btn.setMinimumHeight(44)
            btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            if label == '⌫':
                btn.clicked.connect(self._backspace)
            elif label == '✓':
                btn.clicked.connect(self._check_pin)
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {COLORS.get('success', '#10b981')}; "
                    f"color: white; }}"
                )
            else:
                btn.clicked.connect(lambda checked, d=label: self._add_digit(d))
            keypad.addWidget(btn, row, col)

        layout.addLayout(keypad)

        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Bouton fermer si autorisé
        if self.allow_close:
            close_btn = QPushButton("Annuler")
            close_btn.clicked.connect(self.reject)
            layout.addWidget(close_btn)

    def _add_digit(self, digit: str):
        current = self.pin_input.text()
        if len(current) < 12:
            self.pin_input.setText(current + digit)

    def _backspace(self):
        self.pin_input.setText(self.pin_input.text()[:-1])

    def _check_pin(self):
        pin = self.pin_input.text().strip()
        if not pin:
            return

        cfg = config_manager.config.security
        if cfg.verify_pin(pin):
            self.unlocked.emit()
            self.accept()
        else:
            self.attempts += 1
            self.pin_input.clear()

            if self.attempts >= cfg.max_attempts:
                # Délai de pénalité
                delay = min(60, 5 * (self.attempts - cfg.max_attempts + 1))
                self.status_label.setText(
                    f"❌ Trop d'essais. Attente {delay}s..."
                )
                self.status_label.setStyleSheet(
                    f"color: {COLORS.get('error', '#ef4444')};"
                )
                self.pin_input.setEnabled(False)
                # Réactiver après délai (on reste simple)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(delay * 1000, self._reset_after_delay)
            else:
                remaining = cfg.max_attempts - self.attempts
                self.status_label.setText(
                    f"❌ PIN incorrect. {remaining} essai(s) restant(s)."
                )
                self.status_label.setStyleSheet(
                    f"color: {COLORS.get('error', '#ef4444')};"
                )

    def _reset_after_delay(self):
        self.pin_input.setEnabled(True)
        self.status_label.setText("Vous pouvez réessayer.")
        self.attempts = 0


class PinSetupDialog(QDialog):
    """Dialog de configuration initiale du PIN."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurer le PIN")
        self.setMinimumWidth(400)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("🔐 Définir un code PIN")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        info = QLabel(
            "Entrez un code PIN de 4 à 12 chiffres.\n"
            "Vous devrez l'entrer pour ouvrir l'application "
            "et avant les opérations de trading."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addWidget(QLabel("PIN (4-12 chiffres) :"))
        self.pin1 = QLineEdit()
        self.pin1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin1.setMaxLength(12)
        self.pin1.setMinimumHeight(36)
        layout.addWidget(self.pin1)

        layout.addWidget(QLabel("Confirmer le PIN :"))
        self.pin2 = QLineEdit()
        self.pin2.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin2.setMaxLength(12)
        self.pin2.setMinimumHeight(36)
        layout.addWidget(self.pin2)

        warning = QLabel(
            "⚠️ Si vous perdez ce PIN, vous devrez supprimer le fichier de "
            "configuration et reconfigurer entièrement le bot. Notez-le !"
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            f"color: {COLORS.get('warning', '#f59e0b')}; padding: 8px;"
        )
        layout.addWidget(warning)

        buttons = QHBoxLayout()
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        save_btn = QPushButton("Activer le PIN")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS.get('success', '#10b981')}; "
            f"color: white; font-weight: bold; }}"
        )
        buttons.addWidget(save_btn)

        layout.addLayout(buttons)

    def _save(self):
        pin1 = self.pin1.text().strip()
        pin2 = self.pin2.text().strip()

        if pin1 != pin2:
            QMessageBox.warning(self, "Erreur", "Les deux PIN ne correspondent pas.")
            return

        if not pin1.isdigit() or not (4 <= len(pin1) <= 12):
            QMessageBox.warning(
                self, "Erreur",
                "Le PIN doit être composé de 4 à 12 chiffres uniquement."
            )
            return

        try:
            config_manager.config.security.set_pin(pin1)
            config_manager.save()
            QMessageBox.information(
                self, "PIN activé",
                "Le PIN a été activé avec succès.\n"
                "Il sera demandé au prochain démarrage."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur : {e}")
