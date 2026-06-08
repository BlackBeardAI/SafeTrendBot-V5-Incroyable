"""
Widget moniteur de signaux temps réel.
Affiche pour chaque symbole configuré :
  - Le signal actuel (BUY / SELL / NEUTRE) par stratégie
  - Le résultat du vote consolidé
  - Pourquoi le bot trade ou pas
Rafraîchissement toutes les 30 secondes.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.theme import COLORS


def c(k, d='#888'):
    return COLORS.get(k, d)


# ─────────────────────────────────────────────────────────────
# Worker (tourne en arrière-plan pour ne pas geler l'UI)
# ─────────────────────────────────────────────────────────────

class SignalWorker(QThread):
    """Récupère les données MT5 et calcule les signaux hors UI."""

    result = pyqtSignal(str, object)   # (symbol, VoteResult|None)
    error  = pyqtSignal(str, str)      # (symbol, message)

    def __init__(self, symbol: str, engine=None):
        super().__init__()
        self.symbol = symbol
        self.engine = engine

    def run(self):
        try:
            from app.core.strategies import (
                MarketData, StrategyVoter, SignalDirection,
            )
            from app.core.config_manager import config_manager

            cfg = config_manager.config
            tf  = cfg.strategy.timeframe or "H1"
            min_agree = cfg.strategy.min_strategies_agreement
            min_conf  = cfg.strategy.min_confidence

            # Récupérer les bougies
            closes, highs, lows, vols = [], [], [], []

            if (self.engine and hasattr(self.engine, 'broker')
                    and self.engine.broker
                    and self.engine.broker.is_connected()):
                candles = self.engine.broker.get_candles(self.symbol, tf, 250)
                if candles:
                    for c in candles:
                        closes.append(c.close)
                        highs.append(c.high)
                        lows.append(c.low)
                        vols.append(c.volume)
            else:
                # Fallback : yfinance si pas de broker connecté
                try:
                    import yfinance as yf
                    from app.core.historical_data import _to_yfinance_symbol
                    sym = _to_yfinance_symbol(self.symbol)
                    df = yf.Ticker(sym).history(period="60d", interval="1h")
                    if not df.empty:
                        closes = df['Close'].tolist()
                        highs  = df['High'].tolist()
                        lows   = df['Low'].tolist()
                        vols   = [int(v) for v in df['Volume'].tolist()]
                except Exception:
                    self.error.emit(self.symbol, "Broker non connecté (MT5 requis)")
                    return

            if len(closes) < 30:
                self.error.emit(self.symbol, "Pas assez de données")
                return

            data   = MarketData(closes, highs, lows, vols, self.symbol, tf)
            voter  = StrategyVoter()
            result = voter.vote(data, min_agree, min_conf)
            self.result.emit(self.symbol, result)

        except Exception as e:
            self.error.emit(self.symbol, str(e))


# ─────────────────────────────────────────────────────────────
# Carte par symbole
# ─────────────────────────────────────────────────────────────

class SymbolSignalCard(QFrame):
    """Carte signal pour un symbole."""

    def __init__(self, symbol: str, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.setObjectName("Card")
        self.setMinimumWidth(200)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Symbole + indicateur
        header = QHBoxLayout()
        self.sym_label = QLabel(self.symbol)
        self.sym_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.addWidget(self.sym_label)
        header.addStretch()
        self.dot = QLabel("●")
        self.dot.setFont(QFont("Segoe UI", 16))
        header.addWidget(self.dot)
        layout.addLayout(header)

        # Vote global
        self.vote_label = QLabel("En attente…")
        self.vote_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(self.vote_label)

        # Détail par stratégie
        self.detail_grid = QGridLayout()
        self.detail_grid.setSpacing(2)
        self.strategy_labels = {}
        strategies = ["TrendFollowing", "MeanReversion", "Breakout", "MACD"]
        for i, name in enumerate(strategies):
            n = QLabel(f"{name}:")
            n.setFont(QFont("Segoe UI", 8))
            n.setStyleSheet(f"color: {c('text_secondary')};")
            v = QLabel("—")
            v.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            self.detail_grid.addWidget(n, i, 0)
            self.detail_grid.addWidget(v, i, 1)
            self.strategy_labels[name] = v
        layout.addLayout(self.detail_grid)

        # Raison
        self.reason_label = QLabel("")
        self.reason_label.setFont(QFont("Segoe UI", 8))
        self.reason_label.setWordWrap(True)
        self.reason_label.setStyleSheet(f"color: {c('text_muted')};")
        layout.addWidget(self.reason_label)

    def set_loading(self):
        self.dot.setStyleSheet(f"color: {c('text_muted')};")
        self.vote_label.setText("Analyse…")
        self.vote_label.setStyleSheet(f"color: {c('text_muted')};")

    def set_error(self, msg: str):
        self.dot.setStyleSheet(f"color: {c('error', '#ef4444')};")
        self.vote_label.setText("Erreur")
        self.vote_label.setStyleSheet(f"color: {c('error', '#ef4444')};")
        self.reason_label.setText(msg[:80])

    def set_result(self, vote):
        from app.core.strategies import SignalDirection

        d = vote.direction
        conf_pct = int(vote.confidence * 100)

        if d == SignalDirection.BUY:
            color = c('success', '#10b981')
            text  = f"🟢 ACHETER ({conf_pct}%)"
        elif d == SignalDirection.SELL:
            color = c('error', '#ef4444')
            text  = f"🔴 VENDRE ({conf_pct}%)"
        else:
            color = c('text_muted', '#64748b')
            text  = "⚪ NEUTRE"

        self.dot.setStyleSheet(f"color: {color};")
        self.vote_label.setText(text)
        self.vote_label.setStyleSheet(f"color: {color};")

        # Détail par stratégie
        for sig in vote.signals:
            lbl = self.strategy_labels.get(sig.strategy_name)
            if lbl is None:
                continue
            if sig.direction == SignalDirection.BUY:
                lbl.setText(f"🟢 {int(sig.confidence*100)}%")
                lbl.setStyleSheet(f"color: {c('success', '#10b981')};")
            elif sig.direction == SignalDirection.SELL:
                lbl.setText(f"🔴 {int(sig.confidence*100)}%")
                lbl.setStyleSheet(f"color: {c('error', '#ef4444')};")
            else:
                lbl.setText("⚪ —")
                lbl.setStyleSheet(f"color: {c('text_muted')};")

        # Raisons
        if vote.reasons:
            self.reason_label.setText(" | ".join(vote.reasons[:2]))
        else:
            votes_txt = f"Buy:{vote.votes_buy} Sell:{vote.votes_sell} Neutre:{vote.votes_none}"
            self.reason_label.setText(votes_txt)


# ─────────────────────────────────────────────────────────────
# Widget principal
# ─────────────────────────────────────────────────────────────

class SignalMonitorWidget(QWidget):
    """
    Panneau affichant les signaux en temps réel pour
    tous les symboles configurés.
    """

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self.engine  = engine
        self.cards   = {}
        self.workers = []
        self._build()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(30_000)          # toutes les 30 s
        QTimer.singleShot(1000, self.refresh)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Titre + bouton refresh
        header = QHBoxLayout()
        title = QLabel("📡 Signaux en temps réel")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()

        self.last_update = QLabel("—")
        self.last_update.setStyleSheet(f"color: {c('text_muted')};")
        self.last_update.setFont(QFont("Segoe UI", 8))
        header.addWidget(self.last_update)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("Rafraîchir maintenant")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            f"QPushButton:hover {{ background: {c('hover')}; border-radius: 14px; }}"
        )
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Grille de cartes
        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        layout.addLayout(self.grid)

        self._rebuild_cards()

    def _rebuild_cards(self):
        # Vider la grille
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()

        from app.core.config_manager import config_manager
        symbols = [s.symbol for s in config_manager.config.symbols if s.enabled]

        if not symbols:
            placeholder = QLabel("Aucun symbole configuré.\nAllez dans Paramètres → Symboles.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(placeholder, 0, 0)
            return

        for i, sym in enumerate(symbols):
            card = SymbolSignalCard(sym)
            row, col = divmod(i, 3)
            self.grid.addWidget(card, row, col)
            self.cards[sym] = card

    def refresh(self):
        from datetime import datetime
        self.last_update.setText(f"Mis à jour : {datetime.now().strftime('%H:%M:%S')}")

        # Arrêter les workers précédents
        for w in self.workers:
            if w.isRunning():
                w.terminate()
        self.workers.clear()

        # Reconstruire si les symboles ont changé
        from app.core.config_manager import config_manager
        current = {s.symbol for s in config_manager.config.symbols if s.enabled}
        if current != set(self.cards.keys()):
            self._rebuild_cards()

        # Lancer un worker par symbole
        for sym, card in self.cards.items():
            card.set_loading()
            worker = SignalWorker(sym, self.engine)
            worker.result.connect(self._on_result)
            worker.error.connect(self._on_error)
            self.workers.append(worker)
            worker.start()

    def _on_result(self, symbol: str, vote):
        if symbol in self.cards:
            self.cards[symbol].set_result(vote)

    def _on_error(self, symbol: str, msg: str):
        if symbol in self.cards:
            self.cards[symbol].set_error(msg)
