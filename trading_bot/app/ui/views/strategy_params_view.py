"""
Vue des paramètres de stratégie ajustables sans code.
Sliders pour EMA, RSI, Bollinger, ATR, risque — avec aperçu en temps réel.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFormLayout, QDoubleSpinBox, QSpinBox,
    QSlider, QMessageBox, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.widgets import PageHeader, Card
from app.ui.theme import COLORS
from app.core.config_manager import config_manager


def c(k, d='#888'):
    return COLORS.get(k, d)


class SliderSpinRow(QWidget):
    """Ligne avec slider + spinbox synchronisés"""

    value_changed = pyqtSignal(float)

    def __init__(self, label: str, min_v: float, max_v: float,
                 step: float = 1.0, decimals: int = 0,
                 unit: str = "", tooltip: str = "", parent=None):
        super().__init__(parent)
        self._decimals = decimals
        self._step = step
        self._scale = 10 ** decimals

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFixedWidth(180)
        lbl.setFont(QFont("Segoe UI", 9))
        if tooltip:
            lbl.setToolTip(tooltip)
        layout.addWidget(lbl)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(int(min_v * self._scale), int(max_v * self._scale))
        self.slider.setSingleStep(int(step * self._scale))
        self.slider.setFixedWidth(220)
        layout.addWidget(self.slider)

        self.spin = QDoubleSpinBox() if decimals > 0 else QSpinBox()
        self.spin.setRange(min_v, max_v)
        if decimals > 0:
            self.spin.setDecimals(decimals)
            self.spin.setSingleStep(step)
        if unit:
            self.spin.setSuffix(f" {unit}")
        self.spin.setFixedWidth(90)
        layout.addWidget(self.spin)

        layout.addStretch()

        # Synchronisation
        self.slider.valueChanged.connect(self._slider_changed)
        if decimals > 0:
            self.spin.valueChanged.connect(self._spin_changed)
        else:
            self.spin.valueChanged.connect(self._spin_changed_int)

    def _slider_changed(self, v):
        real = v / self._scale
        self.spin.blockSignals(True)
        self.spin.setValue(real)
        self.spin.blockSignals(False)
        self.value_changed.emit(real)

    def _spin_changed(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(int(v * self._scale))
        self.slider.blockSignals(False)
        self.value_changed.emit(v)

    def _spin_changed_int(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(int(v))
        self.slider.blockSignals(False)
        self.value_changed.emit(float(v))

    def set_value(self, v: float):
        self.spin.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.setValue(v)
        self.slider.setValue(int(v * self._scale))
        self.spin.blockSignals(False)
        self.slider.blockSignals(False)

    def get_value(self) -> float:
        return float(self.spin.value())


class StrategyParamsView(QWidget):
    """Vue complète de réglage des paramètres de stratégie"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        self._load()

    def _build(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        main.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Paramètres de stratégie",
            "Ajustez les indicateurs techniques sans toucher au code"
        ))

        # Avertissement
        warn = QLabel(
            "⚠️ Chaque modification change le comportement des stratégies. "
            "Toujours relancer un backtest après modification. "
            "En cas de doute, utilisez 'Réinitialiser les valeurs par défaut'."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet(
            f"color: {c('warning')}; padding: 10px; "
            f"background: rgba(245,158,11,0.1); border-radius: 6px;"
        )
        layout.addWidget(warn)

        # ── RISQUE ─────────────────────────────────────────────────
        risk_card = Card("💰 Gestion du risque")

        self.risk_pct = SliderSpinRow(
            "Risque par trade", 0.1, 5.0, 0.1, 1, "%",
            "Pourcentage du capital risqué sur chaque position.\n"
            "Recommandé : 0.5-1.5%. Au-delà de 2% : risque élevé."
        )
        risk_card.add_widget(self.risk_pct)

        self.rr_ratio = SliderSpinRow(
            "Ratio Risk/Reward", 1.0, 5.0, 0.5, 1,
            tooltip="TP = SL × ce ratio. Ex: 2.0 = TP 2× plus loin que le SL."
        )
        risk_card.add_widget(self.rr_ratio)

        self.atr_mult = SliderSpinRow(
            "Multiplicateur ATR (SL)", 0.5, 4.0, 0.1, 1,
            tooltip="Stop Loss = ATR × ce multiplicateur.\n"
                    "Plus grand = SL plus large = moins de stop-outs mais plus de perte si déclenché."
        )
        risk_card.add_widget(self.atr_mult)

        self.max_positions = SliderSpinRow(
            "Positions max simultanées", 1, 10, 1, 0,
            tooltip="Nombre maximum de positions ouvertes en même temps."
        )
        risk_card.add_widget(self.max_positions)

        layout.addWidget(risk_card)

        # ── TREND FOLLOWING ────────────────────────────────────────
        trend_card = Card("📈 Trend Following — EMA")

        self.fast_ema = SliderSpinRow(
            "EMA rapide (période)", 5, 100, 1, 0,
            tooltip="EMA court terme. Plus petit = plus réactif mais plus de faux signaux."
        )
        trend_card.add_widget(self.fast_ema)

        self.slow_ema = SliderSpinRow(
            "EMA lente (période)", 50, 500, 5, 0,
            tooltip="EMA long terme. 200 est le standard. Réduire pour plus de signaux."
        )
        trend_card.add_widget(self.slow_ema)

        layout.addWidget(trend_card)

        # ── RSI ───────────────────────────────────────────────────
        rsi_card = Card("📊 RSI")

        self.rsi_period = SliderSpinRow(
            "Période RSI", 5, 30, 1, 0,
            tooltip="Période de calcul du RSI. 14 est le standard de Wilder."
        )
        rsi_card.add_widget(self.rsi_period)

        self.rsi_ob = SliderSpinRow(
            "Seuil surachat", 60, 90, 1, 0, "%",
            tooltip="RSI au-dessus = signal de vente pour Mean Reversion."
        )
        rsi_card.add_widget(self.rsi_ob)

        self.rsi_os = SliderSpinRow(
            "Seuil survente", 10, 40, 1, 0, "%",
            tooltip="RSI en-dessous = signal d'achat pour Mean Reversion."
        )
        rsi_card.add_widget(self.rsi_os)

        layout.addWidget(rsi_card)

        # ── SIGNAL ────────────────────────────────────────────────
        signal_card = Card("🎯 Filtres de signal")

        self.min_agreement = SliderSpinRow(
            "Stratégies requises", 1, 4, 1, 0,
            tooltip="Nombre minimum de stratégies qui doivent voter dans le même sens.\n"
                    "1 = beaucoup de trades. 4 = très peu de trades mais haute qualité."
        )
        signal_card.add_widget(self.min_agreement)

        self.min_confidence = SliderSpinRow(
            "Confiance minimum", 0.3, 0.9, 0.05, 2,
            tooltip="Confiance moyenne minimale requise (0 à 1).\n"
                    "0.40 = seuil bas, beaucoup de signaux.\n"
                    "0.70 = seuil élevé, signaux rares mais précis."
        )
        signal_card.add_widget(self.min_confidence)

        self.min_bars = SliderSpinRow(
            "Bougies min entre trades", 1, 50, 1, 0,
            tooltip="Empêche deux trades trop proches en temps.\n"
                    "Sur H1 : 5 = minimum 5 heures entre trades."
        )
        signal_card.add_widget(self.min_bars)

        layout.addWidget(signal_card)

        # ── HEURES ────────────────────────────────────────────────
        hours_card = Card("🕐 Heures de trading")

        self.start_hour = SliderSpinRow(
            "Heure de début", 0, 23, 1, 0, "h",
            tooltip="Le bot ne trade pas avant cette heure (heure locale)."
        )
        hours_card.add_widget(self.start_hour)

        self.end_hour = SliderSpinRow(
            "Heure de fin", 1, 24, 1, 0, "h",
            tooltip="Le bot ne trade pas après cette heure. 24 = toujours actif."
        )
        hours_card.add_widget(self.end_hour)

        layout.addWidget(hours_card)

        # ── BOUTONS ───────────────────────────────────────────────
        btn_row = QHBoxLayout()

        reset_btn = QPushButton("↺ Réinitialiser les valeurs par défaut")
        reset_btn.setMinimumHeight(36)
        reset_btn.clicked.connect(self._reset_defaults)
        reset_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; "
            f"color: {c('text_secondary')}; border: 1px solid {c('border')}; "
            f"border-radius: 6px; }}"
            f"QPushButton:hover {{ color: {c('text_primary')}; }}"
        )
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()

        save_btn = QPushButton("💾 Enregistrer les paramètres")
        save_btn.setMinimumHeight(36)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _load(self):
        s = config_manager.config.strategy
        self.risk_pct.set_value(s.risk_percent)
        self.rr_ratio.set_value(s.risk_reward_ratio)
        self.atr_mult.set_value(s.atr_multiplier_sl)
        self.max_positions.set_value(float(s.max_positions))
        self.fast_ema.set_value(float(s.fast_ema))
        self.slow_ema.set_value(float(s.slow_ema))
        self.rsi_period.set_value(float(s.rsi_period))
        self.rsi_ob.set_value(s.rsi_overbought)
        self.rsi_os.set_value(s.rsi_oversold)
        self.min_agreement.set_value(float(s.min_strategies_agreement))
        self.min_confidence.set_value(s.min_confidence)
        self.min_bars.set_value(float(s.min_bars_between_trades))
        self.start_hour.set_value(float(s.start_hour))
        self.end_hour.set_value(float(s.end_hour))

    def _save(self):
        s = config_manager.config.strategy
        s.risk_percent = self.risk_pct.get_value()
        s.risk_reward_ratio = self.rr_ratio.get_value()
        s.atr_multiplier_sl = self.atr_mult.get_value()
        s.max_positions = int(self.max_positions.get_value())
        s.fast_ema = int(self.fast_ema.get_value())
        s.slow_ema = int(self.slow_ema.get_value())
        s.rsi_period = int(self.rsi_period.get_value())
        s.rsi_overbought = self.rsi_ob.get_value()
        s.rsi_oversold = self.rsi_os.get_value()
        s.min_strategies_agreement = int(self.min_agreement.get_value())
        s.min_confidence = self.min_confidence.get_value()
        s.min_bars_between_trades = int(self.min_bars.get_value())
        s.start_hour = int(self.start_hour.get_value())
        s.end_hour = int(self.end_hour.get_value())

        config_manager.save()
        QMessageBox.information(
            self, "Enregistré",
            "Paramètres enregistrés.\n\n"
            "Redémarrez le bot pour que les changements prennent effet."
        )

    def _reset_defaults(self):
        reply = QMessageBox.question(
            self, "Réinitialiser",
            "Remettre tous les paramètres aux valeurs par défaut ?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.core.config_manager import StrategyParams
        defaults = StrategyParams()
        config_manager.config.strategy = defaults
        config_manager.save()
        self._load()
        QMessageBox.information(self, "Réinitialisé",
                                "Paramètres réinitialisés aux valeurs par défaut.")
