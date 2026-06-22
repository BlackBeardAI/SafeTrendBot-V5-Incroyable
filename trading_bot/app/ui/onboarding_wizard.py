"""
Onboarding Wizard — SafeTrendBot V5
====================================
Wizard PyQt6 qui s'ouvre au premier lancement (détecté via
`config.onboarding_completed == False`).

3 étapes :
  1. Bienvenue + choix du broker (MT5 / cTrader / Paper)
  2. Configuration du risque (risk %, max positions, symboles)
  3. Confirmation + "Démarrer"

À la fin, sauvegarde la config et marque onboarding_completed=True.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QDoubleSpinBox, QSpinBox, QLineEdit, QTextEdit,
    QPushButton, QCheckBox, QMessageBox, QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.core.config_manager import config_manager, AppConfig, SymbolConfig


class WelcomePage(QWizardPage):
    """Étape 1 : Bienvenue + choix du broker."""

    BROKERS = [
        ("mt5", "MetaTrader 5 (MT5)", "Broker Forex/CFD le plus répandu."),
        ("ctrader", "cTrader", "Broker ECN populaire."),
        ("paper", "Paper Trading (simulé)", "Mode démo — aucun argent réel. Recommandé pour débuter."),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Bienvenue dans SafeTrendBot V5 👋")
        self.setSubTitle(
            "Ce wizard va vous guider pour configurer le bot en quelques secondes.\n"
            "Vous pourrez tout modifier plus tard dans les Paramètres."
        )

        layout = QVBoxLayout(self)

        intro = QLabel(
            "SafeTrendBot V5 est une plateforme de trading automatisé intelligent.\n\n"
            "⚠️  Par sécurité, le bot démarre en mode **Paper Trading** (simulation).\n"
            "Vous pourrez passer en mode **Live** plus tard une fois configuré."
        )
        intro.setWordWrap(True)
        intro.setFont(QFont("Segoe UI", 10))
        layout.addWidget(intro)

        # Choix du broker
        broker_box = QGroupBox("Choisissez votre broker")
        broker_layout = QVBoxLayout(broker_box)

        self.broker_group = QButtonGroup(self)
        self.broker_group.setExclusive(True)
        for idx, (key, label, desc) in enumerate(self.BROKERS):
            radio = QRadioButton(f"{label}  —  {desc}")
            radio.setProperty("broker_key", key)
            self.broker_group.addButton(radio, idx)
            broker_layout.addWidget(radio)
            # Paper sélectionné par défaut
            if key == "paper":
                radio.setChecked(True)

        layout.addWidget(broker_box)
        layout.addStretch()

        # Champ obligatoire : un broker doit être sélectionné.
        # registerField utilise l'attribut _broker_key ; la lecture publique
        # se fait via la property broker_selected.
        self._broker_key = "paper"
        self.registerField("broker_selected*", self, "_broker_key")

        # Synchroniser l'attribut quand la sélection change
        self.broker_group.buttonToggled.connect(self._on_broker_changed)

    def _on_broker_changed(self, button: QRadioButton, checked: bool):
        if checked:
            self._broker_key = button.property("broker_key")

    @property
    def broker_selected(self) -> str:
        """Broker sélectionné (clé: mt5 / ctrader / paper)."""
        btn = self.broker_group.checkedButton()
        return btn.property("broker_key") if btn else self._broker_key


class RiskPage(QWizardPage):
    """Étape 2 : Configuration du risque."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Configuration du risque 🛡️")
        self.setSubTitle(
            "Définissez vos paramètres de gestion du risque.\n"
            "Ces valeurs protègent votre capital."
        )

        layout = QFormLayout(self)

        # Risk %
        self.risk_spin = QDoubleSpinBox()
        self.risk_spin.setRange(0.1, 10.0)
        self.risk_spin.setSingleStep(0.1)
        self.risk_spin.setSuffix(" %")
        self.risk_spin.setValue(1.0)
        self.risk_spin.setToolTip("Risque maximum par trade en % du capital.")
        layout.addRow("Risque par trade :", self.risk_spin)

        # Max positions
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 20)
        self.max_positions_spin.setValue(3)
        self.max_positions_spin.setToolTip("Nombre maximum de positions simultanées.")
        layout.addRow("Positions maximum :", self.max_positions_spin)

        # Max daily loss
        self.daily_loss_spin = QDoubleSpinBox()
        self.daily_loss_spin.setRange(0.5, 20.0)
        self.daily_loss_spin.setSingleStep(0.5)
        self.daily_loss_spin.setSuffix(" %")
        self.daily_loss_spin.setValue(3.0)
        self.daily_loss_spin.setToolTip("Perte journalière maximum avant arrêt automatique.")
        layout.addRow("Perte journalière max :", self.daily_loss_spin)

        # Symboles
        symbols_box = QGroupBox("Symboles à surveiller")
        symbols_layout = QVBoxLayout(symbols_box)

        hint = QLabel("Entrez les symboles séparés par des virgules (ex: EURUSD, GBPUSD, XAUUSD):")
        hint.setFont(QFont("Segoe UI", 9))
        symbols_layout.addWidget(hint)

        self.symbols_edit = QTextEdit()
        self.symbols_edit.setPlainText("EURUSD, GBPUSD, USDJPY, XAUUSD, AUDUSD")
        self.symbols_edit.setMaximumHeight(80)
        symbols_layout.addWidget(self.symbols_edit)

        layout.addRow(symbols_box)

        # Capital initial
        self.capital_spin = QDoubleSpinBox()
        self.capital_spin.setRange(100.0, 10_000_000.0)
        self.capital_spin.setSingleStep(100.0)
        self.capital_spin.setPrefix("$ ")
        self.capital_spin.setValue(10000.0)
        layout.addRow("Capital initial :", self.capital_spin)

    def get_symbols(self) -> list:
        """Retourne la liste des symboles saisie."""
        text = self.symbols_edit.toPlainText().strip()
        if not text:
            return ["EURUSD"]
        return [s.strip().upper() for s in text.split(",") if s.strip()]


class ConfirmationPage(QWizardPage):
    """Étape 3 : Confirmation + Démarrer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Confirmation ✅")
        self.setSubTitle("Vérifiez vos paramètres puis cliquez sur Terminer.")

        layout = QVBoxLayout(self)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setFont(QFont("Segoe UI", 10))
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.summary_label)

        layout.addStretch()

        # Case à cocher confirmation
        self.confirm_check = QCheckBox(
            "Je confirme avoir lu et compris les paramètres ci-dessus."
        )
        layout.addWidget(self.confirm_check)

        # Rendre la checkbox obligatoire pour valider
        self.registerField("confirm*", self.confirm_check)

    def initializePage(self):
        """Appelé automatiquement quand la page s'affiche."""
        wizard = self.wizard()
        # Récupérer les pages typées
        welcome = wizard.page(0) if wizard else None
        risk_page = wizard.page(1) if wizard else None
        broker = getattr(welcome, "broker_selected", "paper") if welcome else "paper"

        risk_spin = getattr(risk_page, "risk_spin", None)
        max_pos_spin = getattr(risk_page, "max_positions_spin", None)
        daily_loss_spin = getattr(risk_page, "daily_loss_spin", None)
        capital_spin = getattr(risk_page, "capital_spin", None)

        risk = risk_spin.value() if risk_spin else 1.0
        max_pos = max_pos_spin.value() if max_pos_spin else 3
        daily_loss = daily_loss_spin.value() if daily_loss_spin else 3.0
        capital = capital_spin.value() if capital_spin else 10000.0
        symbols = risk_page.get_symbols() if hasattr(risk_page, "get_symbols") else ["EURUSD"]  # type: ignore[union-attr]

        broker_label = {
            "mt5": "MetaTrader 5",
            "ctrader": "cTrader",
            "paper": "Paper Trading (simulé)",
        }.get(broker, broker)

        self.summary_label.setText(
            f"<b>Broker :</b> {broker_label}<br><br>"
            f"<b>Mode par défaut :</b> Paper Trading (sécurité)<br><br>"
            f"<b>Risque par trade :</b> {risk:.1f} %<br>"
            f"<b>Positions maximum :</b> {max_pos}<br>"
            f"<b>Perte journalière max :</b> {daily_loss:.1f} %<br><br>"
            f"<b>Capital initial :</b> $ {capital:,.2f}<br><br>"
            f"<b>Symboles surveillés ({len(symbols)}) :</b> {', '.join(symbols)}<br><br>"
            f"<i>Vous pourrez modifier tous ces paramètres ultérieurement.</i>"
        )


class OnboardingWizard(QWizard):
    """Wizard d'onboarding complet (3 étapes)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SafeTrendBot V5 — Configuration initiale")
        self.setMinimumSize(640, 520)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.IndependentPages, False)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)

        # Style moderne
        self.setStyleSheet("""
            QWizard {
                background: #1e1e2e;
            }
            QWizardPage {
                background: #1e1e2e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QGroupBox {
                color: #b0b0b0;
                border: 1px solid #3a3a4a;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background: #2d4a8a;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #3a5fa8;
            }
            QPushButton:disabled {
                background: #3a3a4a;
                color: #777;
            }
            QRadioButton, QCheckBox {
                color: #e0e0e0;
                spacing: 8px;
            }
            QDoubleSpinBox, QSpinBox, QTextEdit {
                background: #2a2a3a;
                color: #e0e0e0;
                border: 1px solid #3a3a4a;
                border-radius: 4px;
                padding: 4px;
            }
        """)

        self.welcome_page = WelcomePage(self)
        self.risk_page = RiskPage(self)
        self.confirm_page = ConfirmationPage(self)

        self.addPage(self.welcome_page)
        self.addPage(self.risk_page)
        self.addPage(self.confirm_page)

        # Boutons personnalisés
        self.setButtonText(QWizard.WizardButton.NextButton, "Suivant →")
        self.setButtonText(QWizard.WizardButton.BackButton, "← Retour")
        self.setButtonText(QWizard.WizardButton.FinishButton, "✓ Terminer")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Annuler")

    def apply_config(self) -> bool:
        """Applique les choix du wizard à la config et sauvegarde.

        Returns:
            True si la config a été sauvegardée avec succès.
        """
        try:
            config: AppConfig = config_manager.config

            # Broker
            broker_key = self.welcome_page.broker_selected
            config.broker.selected = broker_key
            if broker_key == "paper":
                config.default_mode = "paper"
            else:
                # Même si broker réel sélectionné, on reste en paper par sécurité.
                # L'utilisateur passera en live manuellement après connexion.
                config.default_mode = "paper"

            # Risque
            config.strategy.risk_percent = self.risk_page.risk_spin.value()
            config.strategy.risk_per_trade = self.risk_page.risk_spin.value()
            config.strategy.max_positions = self.risk_page.max_positions_spin.value()
            config.strategy.daily_loss_limit_pct = self.risk_page.daily_loss_spin.value()
            config.strategy.max_daily_loss_percent = self.risk_page.daily_loss_spin.value()
            config.initial_capital = self.risk_page.capital_spin.value()

            # Symboles
            symbols = self.risk_page.get_symbols()
            config.symbols = [SymbolConfig(symbol=s, timeframe="H1", enabled=True) for s in symbols]

            # Marquer onboarding complété
            config.onboarding_completed = True

            # Sauvegarder + backup automatique
            config_manager.save(backup=True)

            return True
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur",
                f"Impossible de sauvegarder la configuration :\n{e}"
            )
            return False

    def accept(self):
        """Appelé quand l'utilisateur clique sur Terminer."""
        if self.apply_config():
            super().accept()
        # Sinon, on reste sur place (l'erreur a déjà été affichée)


def run_onboarding_if_needed(parent=None) -> bool:
    """Lance le wizard d'onboarding si nécessaire.

    Args:
        parent: widget parent (optionnel).

    Returns:
        True si l'onboarding est complété (ou l'était déjà),
        False si l'utilisateur a annulé.
    """
    config = config_manager.config
    if getattr(config, "onboarding_completed", False):
        return True

    wizard = OnboardingWizard(parent)
    result = wizard.exec()
    if result == QWizard.DialogCode.Accepted:
        return True
    return False