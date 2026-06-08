"""
Vue d'analyse de tendance long terme (jusqu'à 5 ans).
Permet à l'utilisateur d'analyser un symbole avant de trader dessus.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QFrame, QScrollArea, QFormLayout, QSpinBox,
    QProgressBar, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS
from app.core.historical_data import (
    fetch_historical_yfinance, analyze_trend, TrendAnalysis,
)


class HistoricalFetchWorker(QThread):
    """Worker pour télécharger les données historiques sans bloquer l'UI"""

    finished_ok = pyqtSignal(object)
    finished_error = pyqtSignal(str)

    def __init__(self, symbol: str, years: int):
        super().__init__()
        self.symbol = symbol
        self.years = years

    def run(self):
        try:
            data = fetch_historical_yfinance(self.symbol, self.years)
            if data is None:
                self.finished_error.emit(
                    f"Impossible de récupérer les données pour '{self.symbol}'.\n\n"
                    f"Vérifiez :\n"
                    f"• Le symbole est-il correct ?\n"
                    f"• Êtes-vous connecté à Internet ?\n"
                    f"• yfinance est-il installé ? (pip install yfinance)"
                )
                return
            analysis = analyze_trend(data)
            if analysis is None:
                self.finished_error.emit("Erreur d'analyse des données")
                return
            self.finished_ok.emit(analysis)
        except Exception as e:
            self.finished_error.emit(str(e))


class TrendAnalysisView(QWidget):
    """Vue d'analyse de tendance"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
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
            "Analyse de tendance long terme",
            "Récupère et analyse jusqu'à 5 ans de données historiques pour un symbole"
        ))

        # Contrôles
        control_card = Card("Configuration")
        form = QFormLayout()

        # Symbole : combobox avec presets + saisie libre
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setMinimumHeight(32)
        self.symbol_combo.addItem("EURUSD - Euro / Dollar US", "EURUSD")
        self.symbol_combo.addItem("GBPUSD - Livre / Dollar US", "GBPUSD")
        self.symbol_combo.addItem("USDJPY - Dollar US / Yen", "USDJPY")
        self.symbol_combo.addItem("XAUUSD - Or", "XAUUSD")
        self.symbol_combo.addItem("BTC-USD - Bitcoin", "BTC-USD")
        self.symbol_combo.addItem("ETH-USD - Ethereum", "ETH-USD")
        self.symbol_combo.addItem("^GSPC - S&P 500", "^GSPC")
        self.symbol_combo.addItem("^IXIC - NASDAQ", "^IXIC")
        self.symbol_combo.addItem("^FCHI - CAC 40", "^FCHI")
        self.symbol_combo.addItem("^GDAXI - DAX", "^GDAXI")
        self.symbol_combo.addItem("AAPL - Apple", "AAPL")
        self.symbol_combo.addItem("MSFT - Microsoft", "MSFT")
        form.addRow("Symbole :", self.symbol_combo)

        # Période en années
        self.years_spin = QSpinBox()
        self.years_spin.setRange(1, 10)
        self.years_spin.setValue(5)
        self.years_spin.setSuffix(" années")
        form.addRow("Période :", self.years_spin)

        control_card.add_layout(form)

        # Bouton analyser
        self.analyze_btn = QPushButton("📊 Analyser les tendances")
        self.analyze_btn.setMinimumHeight(40)
        self.analyze_btn.clicked.connect(self._start_analysis)
        control_card.add_widget(self.analyze_btn)

        # Barre de progression
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indéterminée
        self.progress.setVisible(False)
        control_card.add_widget(self.progress)

        layout.addWidget(control_card)

        # Résultats
        self.results_card = Card("Résultats")
        self.results_card.setVisible(False)

        self.results_label = QLabel(
            "Cliquez sur 'Analyser' pour récupérer les données et analyser un symbole."
        )
        self.results_label.setWordWrap(True)
        self.results_card.add_widget(self.results_label)

        layout.addWidget(self.results_card)

        # Résumé initial
        info_card = Card("💡 À quoi ça sert")
        info_text = QLabel(
            "Cette analyse permet de comprendre la tendance long terme d'un symbole "
            "avant de le trader. Elle calcule :\n\n"
            "• <b>Tendance générale</b> : haussière, baissière ou latérale (basée sur "
            "les moyennes mobiles 50 et 200 jours)\n"
            "• <b>Position actuelle</b> : où se situe le prix par rapport à son range "
            "5 ans (près des plus hauts ? plus bas ?)\n"
            "• <b>Volatilité annualisée</b> : niveau de fluctuation typique\n"
            "• <b>Drawdown maximum</b> : la pire baisse historique sur la période\n"
            "• <b>Sharpe ratio</b> : rendement ajusté du risque (>1 = bon, >2 = excellent)\n\n"
            "<b>Source des données :</b> Yahoo Finance (gratuit, légal). "
            "Les données peuvent légèrement différer de votre broker à cause "
            "de la convention de pricing utilisée."
        )
        info_text.setWordWrap(True)
        info_text.setTextFormat(Qt.TextFormat.RichText)
        info_text.setFont(QFont("Segoe UI", 9))
        info_card.add_widget(info_text)
        layout.addWidget(info_card)

        layout.addStretch()

    def _start_analysis(self):
        symbol = self.symbol_combo.currentData() or self.symbol_combo.currentText().strip()
        if not symbol:
            return

        self.analyze_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.results_label.setText(f"Récupération des données pour {symbol}...")
        self.results_card.setVisible(True)

        self.worker = HistoricalFetchWorker(symbol, self.years_spin.value())
        self.worker.finished_ok.connect(self._on_analysis_done)
        self.worker.finished_error.connect(self._on_analysis_error)
        self.worker.start()

    def _on_analysis_done(self, analysis: TrendAnalysis):
        self.analyze_btn.setEnabled(True)
        self.progress.setVisible(False)

        # Format des résultats
        def color_pct(value):
            if value > 0:
                return f"<span style='color: #10b981;'>+{value:.2f}%</span>"
            elif value < 0:
                return f"<span style='color: #ef4444;'>{value:.2f}%</span>"
            return f"{value:.2f}%"

        # Évaluation Sharpe
        if analysis.sharpe_ratio > 2:
            sharpe_text = f"{analysis.sharpe_ratio:.2f} (excellent)"
            sharpe_color = "#10b981"
        elif analysis.sharpe_ratio > 1:
            sharpe_text = f"{analysis.sharpe_ratio:.2f} (bon)"
            sharpe_color = "#10b981"
        elif analysis.sharpe_ratio > 0:
            sharpe_text = f"{analysis.sharpe_ratio:.2f} (médiocre)"
            sharpe_color = "#f59e0b"
        else:
            sharpe_text = f"{analysis.sharpe_ratio:.2f} (négatif)"
            sharpe_color = "#ef4444"

        html = f"""
        <h3>{analysis.symbol} sur {analysis.period_years:.1f} ans</h3>
        <table cellpadding="6" style="font-size: 11pt;">
        <tr><td><b>Prix de départ :</b></td><td>{analysis.start_price:.4f}</td></tr>
        <tr><td><b>Prix actuel :</b></td><td>{analysis.end_price:.4f}</td></tr>
        <tr><td><b>Variation totale :</b></td><td>{color_pct(analysis.total_return_pct)}</td></tr>
        <tr><td><b>Rendement annualisé :</b></td><td>{color_pct(analysis.annualized_return_pct)}</td></tr>
        <tr><td><b>Drawdown maximum :</b></td><td>{color_pct(analysis.max_drawdown_pct)}</td></tr>
        <tr><td><b>Volatilité annualisée :</b></td><td>{analysis.volatility_pct:.2f}%</td></tr>
        <tr><td><b>Sharpe ratio :</b></td><td><span style='color: {sharpe_color};'>{sharpe_text}</span></td></tr>
        <tr><td><b>Tendance long terme :</b></td><td>{analysis.long_term_trend}</td></tr>
        <tr><td><b>Position actuelle :</b></td><td>{analysis.current_position}</td></tr>
        <tr><td><b>Bougies analysées :</b></td><td>{analysis.candles_count}</td></tr>
        </table>

        <h4>📌 Interprétation</h4>
        <p>{self._interpret(analysis)}</p>
        """

        self.results_label.setText(html)
        self.results_label.setTextFormat(Qt.TextFormat.RichText)

    def _interpret(self, a: TrendAnalysis) -> str:
        """Interprétation simple des données"""
        comments = []

        if "Haussière" in a.long_term_trend:
            comments.append(
                "Le symbole est en tendance <b>haussière long terme</b>. "
                "Les stratégies de suivi de tendance sont favorisées."
            )
        elif "Baissière" in a.long_term_trend:
            comments.append(
                "Le symbole est en tendance <b>baissière long terme</b>. "
                "Privilégier les positions short ou éviter ce symbole."
            )
        else:
            comments.append(
                "Le symbole est en tendance <b>latérale/indécise</b>. "
                "Les stratégies de retour à la moyenne peuvent être adaptées, "
                "mais le suivi de tendance sera moins efficace."
            )

        if a.volatility_pct > 30:
            comments.append(
                "Volatilité <b>élevée</b> - prévoir des stop loss larges et "
                "réduire la taille des positions."
            )
        elif a.volatility_pct < 10:
            comments.append(
                "Volatilité <b>faible</b> - les mouvements seront lents, "
                "patience requise."
            )

        if a.max_drawdown_pct < -50:
            comments.append(
                f"⚠️ Drawdown historique très important ({a.max_drawdown_pct:.0f}%). "
                "Soyez conscient du potentiel de perte."
            )

        return "<br>".join(f"• {c}" for c in comments)

    def _on_analysis_error(self, error_msg: str):
        self.analyze_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.results_label.setText(
            f"<span style='color: {COLORS.get('error', '#ef4444')};'>"
            f"❌ Erreur</span><br><br>{error_msg}"
        )
        self.results_label.setTextFormat(Qt.TextFormat.RichText)
