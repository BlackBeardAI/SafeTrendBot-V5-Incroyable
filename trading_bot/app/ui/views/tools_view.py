"""
Vue Outils : utilitaires pratiques.
- Calculator de taille de position
- Export CSV des trades
- Watchlist (symboles à surveiller)
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
    QFormLayout, QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QFrame, QScrollArea, QGroupBox, QFileDialog, QTextBrowser,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS
from app.core.position_calculator import (
    calculate_position_size, PositionCalculation,
)
from app.core.csv_export import export_trades_to_csv


class ToolsView(QWidget):
    """Vue Outils utilitaires"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine = engine
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
            "Outils",
            "Calculator de position, export de données, et utilitaires"
        ))

        # Section : Calculator de position
        layout.addWidget(self._build_calculator_card())

        # Section : Export CSV
        layout.addWidget(self._build_export_card())

        # Section : Mode lecture seule
        layout.addWidget(self._build_readonly_card())

        layout.addStretch()

    def _build_calculator_card(self) -> Card:
        card = Card("📐 Calculator de taille de position")

        info = QLabel(
            "Calcule combien de lots trader pour un risque donné. "
            "Indispensable pour respecter votre money management."
        )
        info.setWordWrap(True)
        card.add_widget(info)

        form = QFormLayout()

        self.calc_capital = QDoubleSpinBox()
        self.calc_capital.setRange(0, 10_000_000)
        self.calc_capital.setValue(10000)
        self.calc_capital.setSuffix(" EUR")
        self.calc_capital.setDecimals(2)
        form.addRow("Capital du compte :", self.calc_capital)

        self.calc_risk = QDoubleSpinBox()
        self.calc_risk.setRange(0.01, 10.0)
        self.calc_risk.setValue(1.0)
        self.calc_risk.setSuffix(" %")
        self.calc_risk.setSingleStep(0.1)
        form.addRow("Risque par trade :", self.calc_risk)

        self.calc_sl_pips = QDoubleSpinBox()
        self.calc_sl_pips.setRange(1, 1000)
        self.calc_sl_pips.setValue(20)
        self.calc_sl_pips.setSuffix(" pips")
        form.addRow("Stop loss :", self.calc_sl_pips)

        self.calc_symbol = QComboBox()
        self.calc_symbol.setEditable(True)
        self.calc_symbol.addItems([
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD",
            "USDCHF", "USDCAD", "EURJPY", "GBPJPY", "XAUUSD",
            "BTCUSD", "ETHUSD",
        ])
        form.addRow("Symbole :", self.calc_symbol)

        card.add_layout(form)

        calc_btn = QPushButton("Calculer la taille de position")
        calc_btn.setMinimumHeight(36)
        calc_btn.clicked.connect(self._do_calculate)
        card.add_widget(calc_btn)

        self.calc_result = QTextBrowser()
        self.calc_result.setMaximumHeight(200)
        self.calc_result.setPlaceholderText("Le résultat s'affichera ici...")
        card.add_widget(self.calc_result)

        return card

    def _do_calculate(self):
        result = calculate_position_size(
            capital=self.calc_capital.value(),
            risk_percent=self.calc_risk.value(),
            stop_loss_pips=self.calc_sl_pips.value(),
            symbol=self.calc_symbol.currentText().strip().upper(),
        )

        warnings_html = ""
        if result.warnings:
            warnings_html = "<br><br>" + "<br>".join(
                f"⚠️ {w}" for w in result.warnings
            )

        html = f"""
        <h3>Résultat</h3>
        <table cellpadding="6" style="font-size: 11pt;">
        <tr><td><b>Capital :</b></td><td>{result.capital:.2f} EUR</td></tr>
        <tr><td><b>Risque max accepté :</b></td><td>{result.risk_amount:.2f} EUR ({result.risk_percent}%)</td></tr>
        <tr><td><b>Stop loss :</b></td><td>{result.stop_loss_pips} pips</td></tr>
        <tr><td><b>Valeur d'un pip :</b></td><td>{result.pip_value:.2f} EUR/lot</td></tr>
        <tr style="font-size: 14pt;"><td><b>📌 Taille de position :</b></td>
            <td><b style="color: #10b981;">{result.lot_size} lot ({result.units:,} unités)</b></td></tr>
        <tr><td><b>Risque réel après arrondi :</b></td><td>{result.actual_risk:.2f} EUR</td></tr>
        </table>{warnings_html}
        """
        self.calc_result.setHtml(html)

    def _build_export_card(self) -> Card:
        card = Card("📤 Export CSV des trades")

        info = QLabel(
            "Exporte l'historique de vos trades au format CSV pour analyse "
            "dans Excel, Google Sheets, ou pour vos déclarations fiscales."
        )
        info.setWordWrap(True)
        card.add_widget(info)

        export_btn = QPushButton("📥 Exporter l'historique des trades")
        export_btn.setMinimumHeight(36)
        export_btn.clicked.connect(self._do_export)
        card.add_widget(export_btn)

        return card

    def _do_export(self):
        try:
            # Récupérer les trades depuis le journal
            trades = []
            if self.engine and hasattr(self.engine, 'journal'):
                journal = self.engine.journal
                if hasattr(journal, 'get_all_trades'):
                    trades_objs = journal.get_all_trades()
                    # Convertir les objets en dict
                    for t in trades_objs:
                        if hasattr(t, '__dict__'):
                            trades.append(t.__dict__)
                        elif isinstance(t, dict):
                            trades.append(t)

            if not trades:
                QMessageBox.information(
                    self, "Aucun trade",
                    "Aucun trade dans le journal pour le moment.\n"
                    "Démarrez le bot et laissez-le trader, "
                    "ou lancez un backtest pour générer des données."
                )
                return

            # Demander où sauvegarder
            from datetime import datetime
            default_name = f"trades_safetrendbot_{datetime.now().strftime('%Y-%m-%d')}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Exporter les trades",
                default_name,
                "Fichiers CSV (*.csv)",
            )
            if not file_path:
                return

            output = export_trades_to_csv(trades, Path(file_path))
            QMessageBox.information(
                self, "Export réussi",
                f"✓ {len(trades)} trade(s) exporté(s) vers :\n{output}\n\n"
                "Vous pouvez ouvrir ce fichier dans Excel."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur",
                f"Erreur lors de l'export :\n{e}"
            )

    def _build_readonly_card(self) -> Card:
        from app.core.config_manager import config_manager

        card = Card("👁️ Mode lecture seule")
        info = QLabel(
            "En mode lecture seule, le bot peut analyser les marchés et générer "
            "des signaux, mais NE PEUT PAS ouvrir de positions. "
            "Utile pour observer le comportement du bot sans risque réel."
        )
        info.setWordWrap(True)
        card.add_widget(info)

        from PyQt6.QtWidgets import QCheckBox
        self.readonly_check = QCheckBox(
            "Activer le mode lecture seule (bloque toute prise de position)"
        )
        # État actuel
        cfg = config_manager.config
        readonly = getattr(cfg.strategy, 'read_only_mode', False)
        self.readonly_check.setChecked(readonly)
        self.readonly_check.toggled.connect(self._toggle_readonly)
        card.add_widget(self.readonly_check)

        return card

    def _toggle_readonly(self, checked: bool):
        from app.core.config_manager import config_manager
        cfg = config_manager.config
        cfg.strategy.read_only_mode = checked
        config_manager.save()

        if checked:
            QMessageBox.information(
                self, "Mode lecture seule",
                "✓ Mode lecture seule ACTIVÉ.\n\n"
                "Le bot continuera d'analyser et de logger ses signaux, "
                "mais n'ouvrira AUCUNE position tant que ce mode est actif."
            )
