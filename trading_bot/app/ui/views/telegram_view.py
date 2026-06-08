"""
Vue de configuration des notifications Telegram.
Permet de configurer le token, le chat ID, les alertes actives,
et de tester l'envoi.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QGroupBox, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QTextBrowser
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS
from app.core.config_manager import config_manager


GUIDE_TEXT = """
<h3>Comment configurer les notifications Telegram</h3>

<p><b>Étape 1 : Créer un bot Telegram</b></p>
<ol>
  <li>Ouvrez Telegram (application ou <a href="https://web.telegram.org">web.telegram.org</a>)</li>
  <li>Recherchez le contact <b>@BotFather</b></li>
  <li>Démarrez une conversation avec lui</li>
  <li>Envoyez la commande <code>/newbot</code></li>
  <li>Choisissez un nom pour votre bot (ex: "Mon SafeTrendBot")</li>
  <li>Choisissez un identifiant unique finissant par "bot" (ex: <code>mon_safetrend_bot</code>)</li>
  <li>BotFather vous donnera un <b>TOKEN</b> de la forme :<br>
      <code>1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ1234567890</code></li>
  <li>Copiez ce token dans le champ ci-dessous</li>
</ol>

<p><b>Étape 2 : Obtenir votre Chat ID</b></p>
<ol>
  <li>Dans Telegram, recherchez le bot que vous venez de créer</li>
  <li>Démarrez une conversation avec lui (envoyez <code>/start</code>)</li>
  <li>Sans fermer cette conversation, recherchez le contact <b>@userinfobot</b></li>
  <li>Envoyez-lui n'importe quel message (ex: <code>hi</code>)</li>
  <li>Il vous répondra avec votre <b>ID</b>, un nombre comme <code>123456789</code></li>
  <li>Copiez ce nombre dans le champ Chat ID ci-dessous</li>
</ol>

<p><b>Étape 3 : Tester</b></p>
<p>Cliquez sur <b>"Envoyer un message de test"</b>. Vous devriez recevoir une notification sur Telegram dans les 2 secondes. Si oui, c'est bon !</p>

<p><b>Que se passe-t-il ensuite ?</b></p>
<p>Une fois configuré, le bot vous enverra automatiquement des notifications Telegram pour :</p>
<ul>
  <li>Ouverture de position (silencieux)</li>
  <li>Clôture de position avec P&L</li>
  <li>Drawdown excessif</li>
  <li>Pertes consécutives approchant la limite</li>
  <li>Activation du circuit breaker</li>
  <li>News économiques à haut impact imminentes</li>
  <li>Rapport journalier (à 22h par défaut)</li>
  <li>Perte de connexion au broker</li>
</ul>
"""


class TelegramView(QWidget):
    """Vue de configuration des notifications Telegram"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()
        self._load_config()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Notifications Telegram",
            "Recevez des alertes en temps réel sur votre téléphone"
        ))

        # Activation
        activation_card = Card("Activation")
        act_layout = QVBoxLayout()

        self.enabled_check = QCheckBox("Activer les notifications Telegram")
        self.enabled_check.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        act_layout.addWidget(self.enabled_check)

        hint = QLabel("Désactivez pour stopper toutes les notifications sans perdre la configuration.")
        hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        act_layout.addWidget(hint)

        activation_card.add_layout(act_layout)
        layout.addWidget(activation_card)

        # Credentials
        creds_card = Card("Identifiants du bot Telegram")
        creds_form = QFormLayout()

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ1234567890")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        creds_form.addRow("Token :", self.token_input)

        show_token_check = QCheckBox("Afficher le token")
        show_token_check.toggled.connect(
            lambda c: self.token_input.setEchoMode(
                QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password
            )
        )
        creds_form.addRow("", show_token_check)

        self.chat_id_input = QLineEdit()
        self.chat_id_input.setPlaceholderText("123456789")
        creds_form.addRow("Chat ID :", self.chat_id_input)

        creds_card.add_layout(creds_form)

        # Bouton test
        test_row = QHBoxLayout()
        self.test_btn = QPushButton("📤 Envoyer un message de test")
        self.test_btn.setMinimumHeight(38)
        self.test_btn.clicked.connect(self._test_send)
        self.test_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['primary']}; color: white;
                          font-weight: bold; border-radius: 4px; padding: 0 20px; }}
            QPushButton:hover {{ background-color: {COLORS['primary_hover']}; }}
        """)
        test_row.addWidget(self.test_btn)
        test_row.addStretch()
        creds_card.add_layout(test_row)
        layout.addWidget(creds_card)

        # Événements à notifier
        events_card = Card("Événements à notifier")
        events_layout = QVBoxLayout()

        self.alert_position_open = QCheckBox("Ouverture de position (notification silencieuse)")
        self.alert_position_close = QCheckBox("Clôture de position avec P&L")
        self.alert_drawdown = QCheckBox("Drawdown excessif")
        self.alert_consecutive = QCheckBox("Pertes consécutives approchant la limite")
        self.alert_circuit_breaker = QCheckBox("Activation du circuit breaker")
        self.alert_news = QCheckBox("News économiques à haut impact imminentes")
        self.alert_daily_report = QCheckBox("Rapport journalier")
        self.alert_connection = QCheckBox("Perte de connexion au broker")

        for check in [self.alert_position_open, self.alert_position_close,
                      self.alert_drawdown, self.alert_consecutive,
                      self.alert_circuit_breaker, self.alert_news,
                      self.alert_daily_report, self.alert_connection]:
            events_layout.addWidget(check)

        # Seuils
        thresholds_form = QFormLayout()
        thresholds_form.setContentsMargins(0, 12, 0, 0)

        self.drawdown_threshold = QSpinBox()
        self.drawdown_threshold.setRange(1, 50)
        self.drawdown_threshold.setSuffix(" %")
        thresholds_form.addRow("Seuil drawdown :", self.drawdown_threshold)

        self.daily_report_hour = QSpinBox()
        self.daily_report_hour.setRange(0, 23)
        self.daily_report_hour.setSuffix(" h")
        thresholds_form.addRow("Heure rapport journalier :", self.daily_report_hour)

        events_layout.addLayout(thresholds_form)
        events_card.add_layout(events_layout)
        layout.addWidget(events_card)

        # Bouton enregistrer
        save_row = QHBoxLayout()
        save_btn = QPushButton("💾 Enregistrer")
        save_btn.setMinimumHeight(38)
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['success']}; color: white;
                          font-weight: bold; border-radius: 4px; padding: 0 20px; }}
            QPushButton:hover {{ background-color: #059669; }}
        """)
        save_row.addWidget(save_btn)

        guide_btn = QPushButton("❓ Comment configurer ?")
        guide_btn.setMinimumHeight(38)
        guide_btn.clicked.connect(self._show_guide)
        save_row.addWidget(guide_btn)

        save_row.addStretch()
        layout.addLayout(save_row)
        layout.addStretch()

    def _load_config(self):
        cfg = config_manager.config.telegram
        self.enabled_check.setChecked(cfg.enabled)
        self.token_input.setText(cfg.token)
        self.chat_id_input.setText(cfg.chat_id)
        self.alert_position_open.setChecked(cfg.alert_position_open)
        self.alert_position_close.setChecked(cfg.alert_position_close)
        self.alert_drawdown.setChecked(cfg.alert_drawdown)
        self.alert_consecutive.setChecked(cfg.alert_consecutive_losses)
        self.alert_circuit_breaker.setChecked(True)  # Toujours actif par défaut
        self.alert_news.setChecked(cfg.alert_news)
        self.alert_daily_report.setChecked(cfg.alert_daily_report)
        self.alert_connection.setChecked(True)  # Toujours actif par défaut
        self.drawdown_threshold.setValue(int(cfg.alert_drawdown_threshold))
        self.daily_report_hour.setValue(cfg.daily_report_hour)

    def _save(self):
        cfg = config_manager.config.telegram
        cfg.enabled = self.enabled_check.isChecked()
        cfg.token = self.token_input.text().strip()
        cfg.chat_id = self.chat_id_input.text().strip()
        cfg.alert_position_open = self.alert_position_open.isChecked()
        cfg.alert_position_close = self.alert_position_close.isChecked()
        cfg.alert_drawdown = self.alert_drawdown.isChecked()
        cfg.alert_consecutive_losses = self.alert_consecutive.isChecked()
        cfg.alert_news = self.alert_news.isChecked()
        cfg.alert_daily_report = self.alert_daily_report.isChecked()
        cfg.alert_drawdown_threshold = float(self.drawdown_threshold.value())
        cfg.daily_report_hour = self.daily_report_hour.value()
        config_manager.save()

        # Rechargement dans le moteur s'il tourne
        if self.engine and hasattr(self.engine, 'reload_telegram'):
            self.engine.reload_telegram()

        QMessageBox.information(self, "Enregistré",
                                "Configuration Telegram sauvegardée.\n\n"
                                "Si le bot est actif, les nouveaux paramètres sont "
                                "appliqués immédiatement.")

    def _test_send(self):
        token = self.token_input.text().strip()
        chat_id = self.chat_id_input.text().strip()

        if not token or not chat_id:
            QMessageBox.warning(self, "Champs manquants",
                                "Renseignez le Token et le Chat ID avant de tester.")
            return

        try:
            from bot.telegram_alerts import AlertSystem
            alerts = AlertSystem(token=token, chat_id=chat_id)

            if alerts.test():
                QMessageBox.information(
                    self, "Test réussi ✅",
                    "Message envoyé avec succès !\n\n"
                    "Vérifiez votre Telegram, vous devriez avoir reçu une notification.\n\n"
                    "Si vous n'avez rien reçu :\n"
                    "• Avez-vous bien démarré une conversation avec votre bot ?\n"
                    "• Le Chat ID est-il correct ?"
                )
            else:
                QMessageBox.warning(
                    self, "Échec",
                    "Le message n'a pas pu être envoyé.\n\n"
                    "Causes possibles :\n"
                    "• Token incorrect\n"
                    "• Chat ID incorrect\n"
                    "• Pas de connexion internet\n"
                    "• Vous n'avez pas démarré de conversation avec votre bot"
                )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Exception : {e}")

    def _show_guide(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Guide de configuration Telegram")
        dialog.setTextFormat(Qt.TextFormat.RichText)
        dialog.setText(GUIDE_TEXT)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()
