"""
Vue Broker - Support de 8 plateformes de trading.
MT5 mis en avant, autres brokers accessibles via un sélecteur.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QFormLayout, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QFrame, QScrollArea, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.ui.widgets import PageHeader, Card
from app.core.config_manager import config_manager
from app.brokers import BrokerType
from app.brokers.factory import list_available_brokers
import logging

logger = logging.getLogger("broker_view")


class BrokerView(QWidget):
    broker_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._load_config()

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
            "Broker",
            "Choisissez votre plateforme et configurez la connexion"
        ))

        # Sélecteur de broker
        selector_card = Card("Plateforme de trading")
        form = QFormLayout()

        self.broker_combo = QComboBox()
        self.broker_combo.setMinimumHeight(32)
        self.broker_combo.addItem("MetaTrader 5  🟢 Forex/CFD/Actions (recommandé)", "mt5")
        self.broker_combo.addItem("XTB xStation  🟡 Forex/CFD (expérimental)", "xtb")
        self.broker_combo.addItem("Interactive Brokers  🟡 Multi-marchés (expérimental)", "ib")
        self.broker_combo.addItem("cTrader  🟡 Forex/CFD (expérimental)", "ctrader")
        self.broker_combo.addItem("Binance  🟡 Crypto (expérimental)", "binance")
        self.broker_combo.addItem("Bybit  🟡 Crypto (expérimental)", "bybit")
        self.broker_combo.addItem("Kraken  🟡 Crypto (expérimental)", "kraken")
        self.broker_combo.addItem("Coinbase Advanced  🟡 Crypto (expérimental)", "coinbase")
        self.broker_combo.currentIndexChanged.connect(self._on_broker_changed)
        form.addRow("Broker actif :", self.broker_combo)

        selector_card.add_layout(form)

        self.install_status = QLabel()
        self.install_status.setWordWrap(True)
        selector_card.add_widget(self.install_status)

        layout.addWidget(selector_card)

        # Stack des panneaux de config
        self.config_stack = QStackedWidget()
        self.config_stack.addWidget(self._build_mt5_panel())    # 0
        self.config_stack.addWidget(self._build_xtb_panel())    # 1
        self.config_stack.addWidget(self._build_ib_panel())     # 2
        self.config_stack.addWidget(self._build_ctrader_panel())# 3
        self.config_stack.addWidget(self._build_crypto_panel('binance', 'Binance'))   # 4
        self.config_stack.addWidget(self._build_crypto_panel('bybit', 'Bybit'))       # 5
        self.config_stack.addWidget(self._build_crypto_panel('kraken', 'Kraken'))     # 6
        self.config_stack.addWidget(self._build_crypto_panel('coinbase', 'Coinbase')) # 7
        layout.addWidget(self.config_stack)

        # Boutons
        buttons = QHBoxLayout()
        test_btn = QPushButton("🔌 Tester la connexion")
        test_btn.setMinimumHeight(40)
        test_btn.clicked.connect(self._test_connection)
        buttons.addWidget(test_btn)

        save_btn = QPushButton("💾 Enregistrer")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(lambda: self._save(show_message=True))
        buttons.addWidget(save_btn)

        buttons.addStretch()
        layout.addLayout(buttons)

        layout.addStretch()

    # ------------------------------------------------------------------------
    # PANNEAUX
    # ------------------------------------------------------------------------

    def _build_mt5_panel(self):
        card = Card("Configuration MetaTrader 5")
        form = QFormLayout()

        self.mt5_auto_detect = QCheckBox(
            "Détection automatique (utilise le MT5 déjà ouvert)"
        )
        self.mt5_auto_detect.setChecked(True)
        self.mt5_auto_detect.toggled.connect(self._on_mt5_auto)
        form.addRow(self.mt5_auto_detect)

        self.mt5_terminal_path = QLineEdit()
        self.mt5_terminal_path.setPlaceholderText(
            "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
        )
        form.addRow("Chemin terminal :", self.mt5_terminal_path)

        self.mt5_login = QSpinBox()
        self.mt5_login.setRange(0, 999999999)
        self.mt5_login.setSpecialValueText("(auto)")
        form.addRow("Numéro de compte :", self.mt5_login)

        self.mt5_password = QLineEdit()
        self.mt5_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mot de passe :", self.mt5_password)

        self.mt5_server = QLineEdit()
        self.mt5_server.setPlaceholderText("Ex: ICMarkets-Demo")
        form.addRow("Serveur :", self.mt5_server)

        card.add_layout(form)
        card.add_widget(self._info_label(
            "Ouvrez MT5 sur votre PC avant de tester. "
            "Dans MT5 : Outils > Options > Expert Advisors > cocher "
            "'Autoriser le trading automatique'."
        ))
        return card

    def _build_xtb_panel(self):
        card = Card("Configuration XTB xStation")
        form = QFormLayout()

        self.xtb_user_id = QLineEdit()
        self.xtb_user_id.setPlaceholderText("Numéro de compte XTB")
        form.addRow("User ID :", self.xtb_user_id)

        self.xtb_password = QLineEdit()
        self.xtb_password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mot de passe :", self.xtb_password)

        self.xtb_demo = QCheckBox("Compte démo (recommandé)")
        self.xtb_demo.setChecked(True)
        form.addRow(self.xtb_demo)

        card.add_layout(form)
        card.add_widget(self._warning_label(
            "XTB peut bloquer les comptes utilisant du trading automatisé. "
            "Contactez leur support pour autoriser l'API sur votre compte avant usage."
        ))
        return card

    def _build_ib_panel(self):
        card = Card("Configuration Interactive Brokers")
        form = QFormLayout()

        self.ib_host = QLineEdit()
        self.ib_host.setText("127.0.0.1")
        form.addRow("Host :", self.ib_host)

        self.ib_port = QSpinBox()
        self.ib_port.setRange(1000, 65535)
        self.ib_port.setValue(7497)
        form.addRow("Port :", self.ib_port)

        port_info = QLabel(
            "7497 = TWS démo · 7496 = TWS live · 4002 = Gateway démo · 4001 = Gateway live"
        )
        port_info.setStyleSheet("font-size: 10px;")
        form.addRow("", port_info)

        self.ib_client_id = QSpinBox()
        self.ib_client_id.setRange(0, 999)
        self.ib_client_id.setValue(1)
        form.addRow("Client ID :", self.ib_client_id)

        card.add_layout(form)
        card.add_widget(self._warning_label(
            "Lancez TWS ou IB Gateway. "
            "Dans TWS : Configure > API > cocher 'Enable ActiveX and Socket Clients' "
            "et DÉCOCHER 'Read-Only API'."
        ))
        return card

    def _build_ctrader_panel(self):
        card = Card("Configuration cTrader")
        form = QFormLayout()

        self.ctrader_client_id = QLineEdit()
        form.addRow("Client ID :", self.ctrader_client_id)

        self.ctrader_client_secret = QLineEdit()
        self.ctrader_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Client Secret :", self.ctrader_client_secret)

        self.ctrader_access_token = QLineEdit()
        self.ctrader_access_token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Access Token :", self.ctrader_access_token)

        self.ctrader_account_id = QSpinBox()
        self.ctrader_account_id.setRange(0, 999999999)
        form.addRow("Account ID :", self.ctrader_account_id)

        self.ctrader_demo = QCheckBox("Compte démo")
        self.ctrader_demo.setChecked(True)
        form.addRow(self.ctrader_demo)

        card.add_layout(form)
        card.add_widget(self._warning_label(
            "cTrader nécessite de créer une application sur "
            "https://openapi.ctrader.com puis d'obtenir un access token via OAuth2. "
            "Cette implémentation est un squelette - le flow complet est à finaliser."
        ))
        return card

    def _build_crypto_panel(self, broker_id: str, broker_name: str):
        card = Card(f"Configuration {broker_name}")
        form = QFormLayout()

        api_key = QLineEdit()
        api_key.setPlaceholderText(f"Clé API {broker_name}")
        form.addRow("API Key :", api_key)
        setattr(self, f"{broker_id}_api_key", api_key)

        api_secret = QLineEdit()
        api_secret.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("API Secret :", api_secret)
        setattr(self, f"{broker_id}_api_secret", api_secret)

        if broker_id == "coinbase":
            passphrase = QLineEdit()
            passphrase.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow("Passphrase :", passphrase)
            setattr(self, f"{broker_id}_passphrase", passphrase)

        sandbox = QCheckBox("Mode testnet/sandbox (si supporté)")
        form.addRow(sandbox)
        setattr(self, f"{broker_id}_sandbox", sandbox)

        card.add_layout(form)

        card.add_widget(self._warning_label(
            f"IMPORTANT pour {broker_name} : créez votre API key avec les permissions "
            f"MINIMALES nécessaires :\n"
            f"• Lecture du compte : OUI\n"
            f"• Trading spot : OUI\n"
            f"• Retraits / Withdrawals : NON (jamais !)\n"
            f"• Si possible, restreignez par adresse IP."
        ))
        return card

    def _info_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("padding: 10px; background: rgba(37, 99, 235, 0.08); border-radius: 4px;")
        return label

    def _warning_label(self, text: str) -> QLabel:
        label = QLabel(f"⚠️ {text}")
        label.setWordWrap(True)
        label.setStyleSheet("padding: 10px; background: rgba(245, 158, 11, 0.1); border-radius: 4px;")
        return label

    # ------------------------------------------------------------------------
    # LOGIQUE
    # ------------------------------------------------------------------------

    def _on_broker_changed(self):
        self.config_stack.setCurrentIndex(self.broker_combo.currentIndex())
        self._update_install_status()

    def _on_mt5_auto(self, checked):
        self.mt5_terminal_path.setEnabled(not checked)
        self.mt5_login.setEnabled(not checked)
        self.mt5_password.setEnabled(not checked)
        self.mt5_server.setEnabled(not checked)

    def _update_install_status(self):
        available = {b: True for b in list_available_brokers()}
        type_map = {
            "mt5": BrokerType.MT5,
            "xtb": BrokerType.XTB,
            "ib": BrokerType.INTERACTIVE_BROKERS,
            "ctrader": BrokerType.CTRADER,
            "binance": BrokerType.BINANCE,
            "bybit": BrokerType.BYBIT,
            "kraken": BrokerType.KRAKEN,
            "coinbase": BrokerType.COINBASE,
        }
        broker_name = self.broker_combo.currentData()
        broker_type = type_map.get(broker_name)

        if available.get(broker_type, False):
            self.install_status.setText("✓ Bibliothèque installée")
            self.install_status.setStyleSheet("color: #10b981;")
        else:
            pkg_map = {
                BrokerType.MT5: "pip install MetaTrader5",
                BrokerType.XTB: "(inclus)",
                BrokerType.INTERACTIVE_BROKERS: "pip install ib_insync",
                BrokerType.CTRADER: "pip install ctrader-open-api",
                BrokerType.BINANCE: "pip install ccxt",
                BrokerType.BYBIT: "pip install ccxt",
                BrokerType.KRAKEN: "pip install ccxt",
                BrokerType.COINBASE: "pip install ccxt",
            }
            pkg = pkg_map.get(broker_type, "")
            self.install_status.setText(f"✗ Installation requise : {pkg}")
            self.install_status.setStyleSheet("color: #ef4444;")

    def _load_config(self):
        try:
            cfg = config_manager.config.broker

            idx = self.broker_combo.findData(cfg.selected or "mt5")
            if idx >= 0:
                self.broker_combo.setCurrentIndex(idx)

            # MT5
            self.mt5_auto_detect.setChecked(cfg.mt5.auto_detect)
            self.mt5_terminal_path.setText(cfg.mt5.terminal_path or "")
            self.mt5_login.setValue(cfg.mt5.login or 0)
            self.mt5_password.setText(cfg.mt5.password or "")
            self.mt5_server.setText(cfg.mt5.server or "")
            self._on_mt5_auto(cfg.mt5.auto_detect)

            # XTB
            self.xtb_user_id.setText(cfg.xtb.user_id or "")
            self.xtb_password.setText(cfg.xtb.password or "")
            self.xtb_demo.setChecked(cfg.xtb.demo)

            # IB
            self.ib_host.setText(cfg.ib.host or "127.0.0.1")
            self.ib_port.setValue(cfg.ib.port or 7497)
            self.ib_client_id.setValue(cfg.ib.client_id or 1)

            # cTrader
            self.ctrader_client_id.setText(cfg.ctrader.client_id or "")
            self.ctrader_client_secret.setText(cfg.ctrader.client_secret or "")
            self.ctrader_access_token.setText(cfg.ctrader.access_token or "")
            self.ctrader_account_id.setValue(cfg.ctrader.account_id or 0)
            self.ctrader_demo.setChecked(cfg.ctrader.demo)

            # Crypto
            for b in ('binance', 'bybit', 'kraken', 'coinbase'):
                c = getattr(cfg, b)
                getattr(self, f"{b}_api_key").setText(c.api_key or "")
                getattr(self, f"{b}_api_secret").setText(c.api_secret or "")
                getattr(self, f"{b}_sandbox").setChecked(c.sandbox)
                if b == "coinbase":
                    self.coinbase_passphrase.setText(c.passphrase or "")

            self._update_install_status()
        except Exception as e:
            logger.warning(f"Erreur chargement config broker : {e}")

    def _save(self, show_message=False):
        try:
            cfg = config_manager.config.broker
            cfg.selected = self.broker_combo.currentData() or "mt5"

            cfg.mt5.auto_detect = self.mt5_auto_detect.isChecked()
            cfg.mt5.terminal_path = self.mt5_terminal_path.text().strip()
            cfg.mt5.login = self.mt5_login.value()
            cfg.mt5.password = self.mt5_password.text()
            cfg.mt5.server = self.mt5_server.text().strip()

            cfg.xtb.user_id = self.xtb_user_id.text().strip()
            cfg.xtb.password = self.xtb_password.text()
            cfg.xtb.demo = self.xtb_demo.isChecked()

            cfg.ib.host = self.ib_host.text().strip() or "127.0.0.1"
            cfg.ib.port = self.ib_port.value()
            cfg.ib.client_id = self.ib_client_id.value()

            cfg.ctrader.client_id = self.ctrader_client_id.text().strip()
            cfg.ctrader.client_secret = self.ctrader_client_secret.text()
            cfg.ctrader.access_token = self.ctrader_access_token.text()
            cfg.ctrader.account_id = self.ctrader_account_id.value()
            cfg.ctrader.demo = self.ctrader_demo.isChecked()

            for b in ('binance', 'bybit', 'kraken', 'coinbase'):
                c = getattr(cfg, b)
                c.api_key = getattr(self, f"{b}_api_key").text().strip()
                c.api_secret = getattr(self, f"{b}_api_secret").text()
                c.sandbox = getattr(self, f"{b}_sandbox").isChecked()
                if b == "coinbase":
                    c.passphrase = self.coinbase_passphrase.text()

            config_manager.save()
            self.broker_changed.emit(cfg.selected)

            if show_message:
                QMessageBox.information(
                    self, "Sauvegardé",
                    f"Broker configuré : {cfg.selected.upper()}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur sauvegarde : {e}")

    def _test_connection(self):
        self._save(show_message=False)

        from app.brokers.factory import create_broker_adapter
        type_map = {
            "mt5": BrokerType.MT5, "xtb": BrokerType.XTB,
            "ib": BrokerType.INTERACTIVE_BROKERS, "ctrader": BrokerType.CTRADER,
            "binance": BrokerType.BINANCE, "bybit": BrokerType.BYBIT,
            "kraken": BrokerType.KRAKEN, "coinbase": BrokerType.COINBASE,
        }
        broker_name = self.broker_combo.currentData()
        broker_type = type_map.get(broker_name)
        if broker_type is None:
            return

        try:
            adapter = create_broker_adapter(broker_type)
            if adapter is None:
                QMessageBox.warning(self, "Erreur",
                                    "Impossible de créer l'adapter broker.")
                return

            cfg = config_manager.config.broker
            ok = False

            if broker_name == "mt5":
                ok = adapter.connect(
                    auto_detect=cfg.mt5.auto_detect,
                    terminal_path=cfg.mt5.terminal_path,
                    login=cfg.mt5.login, password=cfg.mt5.password,
                    server=cfg.mt5.server,
                )
            elif broker_name == "xtb":
                ok = adapter.connect(
                    user_id=cfg.xtb.user_id, password=cfg.xtb.password,
                    demo=cfg.xtb.demo,
                )
            elif broker_name == "ib":
                ok = adapter.connect(
                    host=cfg.ib.host, port=cfg.ib.port,
                    client_id=cfg.ib.client_id,
                )
            elif broker_name == "ctrader":
                ok = adapter.connect(
                    client_id=cfg.ctrader.client_id,
                    client_secret=cfg.ctrader.client_secret,
                    access_token=cfg.ctrader.access_token,
                    account_id=cfg.ctrader.account_id,
                    demo=cfg.ctrader.demo,
                )
            elif broker_name in ('binance', 'bybit', 'kraken', 'coinbase'):
                c = getattr(cfg, broker_name)
                ok = adapter.connect(
                    api_key=c.api_key, api_secret=c.api_secret,
                    passphrase=c.passphrase if broker_name == 'coinbase' else '',
                    sandbox=c.sandbox,
                )

            if ok:
                info = adapter.get_account_info()
                if info:
                    QMessageBox.information(
                        self, "Connexion réussie",
                        f"✓ Connecté avec succès !\n\n"
                        f"Compte : {info.name}\n"
                        f"Serveur : {info.server}\n"
                        f"Balance : {info.balance:.4f} {info.currency}\n"
                        f"Équité : {info.equity:.4f} {info.currency}"
                    )
                else:
                    QMessageBox.warning(
                        self, "Connexion partielle",
                        "Connecté mais impossible de lire le compte."
                    )
                # ⚠️ NE PAS déconnecter MT5 — mt5.shutdown() est global
                if broker_name != "mt5":
                    adapter.disconnect()
            else:
                err = adapter.get_last_error() or "Raison inconnue"
                QMessageBox.warning(
                    self, "Échec de connexion",
                    f"Impossible de se connecter.\n\nErreur : {err}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Exception : {e}")
