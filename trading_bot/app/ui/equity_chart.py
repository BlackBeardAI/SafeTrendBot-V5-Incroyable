"""
Widget graphique d'équité — courbe temps réel dessinée en PyQt6 natif.
Pas de dépendance matplotlib pour rester léger.
Affiche : courbe equity, drawdown, niveau de référence.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QLinearGradient, QPainterPath

from app.ui.theme import COLORS


def c(k, d='#888'):
    return COLORS.get(k, d)


class EquityChart(QWidget):
    """
    Graphique d'équité avec :
    - Courbe equity (verte si positive, rouge si négative)
    - Zone de drawdown remplie
    - Ligne de référence (capital initial)
    - Grille et labels d'axes
    - Tooltip au survol
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._equity_history: list[tuple] = []  # [(timestamp, value), ...]
        self._initial_capital = 10000.0
        self._hover_index = -1

        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    # ── API publique ──────────────────────────────────────────────────

    def set_data(self, equity_history: list, initial_capital: float = 10000.0):
        """Met à jour les données et redessine"""
        self._equity_history = equity_history or []
        self._initial_capital = initial_capital
        self.update()

    def append_point(self, timestamp, value: float):
        """Ajoute un point et redessine"""
        self._equity_history.append((timestamp, value))
        # Garder 500 points max pour la performance
        if len(self._equity_history) > 500:
            self._equity_history = self._equity_history[-500:]
        self.update()

    def clear(self):
        self._equity_history.clear()
        self.update()

    # ── Dessin ───────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        pad_l, pad_r, pad_t, pad_b = 72, 16, 16, 36

        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        # Fond
        bg = QColor(c('card_bg', '#1a2028'))
        painter.fillRect(0, 0, w, h, bg)

        if len(self._equity_history) < 2:
            self._draw_empty(painter, w, h)
            painter.end()
            return

        values = [v for _, v in self._equity_history]
        min_v = min(values)
        max_v = max(values)
        ref = self._initial_capital

        # Étendre l'axe Y pour inclure la référence
        min_v = min(min_v, ref) * 0.998
        max_v = max(max_v, ref) * 1.002
        v_range = max(max_v - min_v, 1.0)

        def px(i, val):
            x = pad_l + (i / (len(values) - 1)) * chart_w
            y = pad_t + chart_h - ((val - min_v) / v_range) * chart_h
            return x, y

        # Grille horizontale
        grid_pen = QPen(QColor(c('border', '#1e293b')))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        label_font = QFont("Segoe UI", 8)
        painter.setFont(label_font)

        for step in range(5):
            val = min_v + (v_range * step / 4)
            _, y = px(0, val)
            painter.drawLine(pad_l, int(y), pad_l + chart_w, int(y))
            text = f"{val:,.0f}"
            painter.drawText(2, int(y) + 4, pad_l - 6, 16,
                             Qt.AlignmentFlag.AlignRight, text)

        # Zone de drawdown (rouge translucide)
        dd_path = QPainterPath()
        peak = values[0]
        started = False
        for i, val in enumerate(values):
            if val > peak:
                peak = val
            if val < peak:
                x, y_val = px(i, val)
                _, y_peak = px(i, peak)
                if not started:
                    dd_path.moveTo(x, y_peak)
                    started = True
                dd_path.lineTo(x, y_val)
            else:
                if started:
                    x, _ = px(i, val)
                    dd_path.lineTo(x, _)
                    started = False
                    peak = val

        dd_color = QColor('#ef4444')
        dd_color.setAlpha(40)
        painter.fillPath(dd_path, dd_color)

        # Ligne de référence (capital initial)
        _, ref_y = px(0, ref)
        ref_pen = QPen(QColor(c('text_muted', '#64748b')))
        ref_pen.setStyle(Qt.PenStyle.DashLine)
        ref_pen.setWidth(1)
        painter.setPen(ref_pen)
        painter.drawLine(pad_l, int(ref_y), pad_l + chart_w, int(ref_y))
        painter.drawText(pad_l + 4, int(ref_y) - 3, f"Ref {ref:,.0f}")

        # Remplissage sous la courbe
        current_val = values[-1]
        fill_color = QColor('#10b981' if current_val >= ref else '#ef4444')
        fill_color.setAlpha(25)

        fill_path = QPainterPath()
        x0, y0 = px(0, values[0])
        fill_path.moveTo(x0, pad_t + chart_h)
        fill_path.lineTo(x0, y0)
        for i, val in enumerate(values[1:], 1):
            x, y = px(i, val)
            fill_path.lineTo(x, y)
        xn, _ = px(len(values) - 1, values[-1])
        fill_path.lineTo(xn, pad_t + chart_h)
        fill_path.closeSubpath()
        painter.fillPath(fill_path, fill_color)

        # Courbe principale
        is_positive = current_val >= ref
        line_color = QColor('#10b981' if is_positive else '#ef4444')
        line_pen = QPen(line_color)
        line_pen.setWidth(2)
        painter.setPen(line_pen)

        curve = QPainterPath()
        x0, y0 = px(0, values[0])
        curve.moveTo(x0, y0)
        for i, val in enumerate(values[1:], 1):
            x, y = px(i, val)
            curve.lineTo(x, y)
        painter.drawPath(curve)

        # Point final (rond)
        xn, yn = px(len(values) - 1, values[-1])
        painter.setBrush(line_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(int(xn), int(yn)), 5, 5)

        # Tooltip au survol
        if 0 <= self._hover_index < len(values):
            xh, yh = px(self._hover_index, values[self._hover_index])
            ts, val = self._equity_history[self._hover_index]
            ts_str = ts.strftime('%d/%m %H:%M') if hasattr(ts, 'strftime') else str(ts)
            diff = val - ref
            diff_pct = (diff / ref) * 100
            tooltip = f"{ts_str}\n{val:,.2f} ({diff_pct:+.1f}%)"

            # Ligne verticale
            vl_pen = QPen(QColor(c('text_muted')))
            vl_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(vl_pen)
            painter.drawLine(int(xh), pad_t, int(xh), pad_t + chart_h)

            # Bulle
            tip_rect = QRect(int(xh) + 8, int(yh) - 30, 160, 40)
            if tip_rect.right() > w - 8:
                tip_rect.moveLeft(int(xh) - 168)
            tip_bg = QColor(c('bg_secondary', '#161c24'))
            tip_bg.setAlpha(220)
            painter.fillRect(tip_rect, tip_bg)
            painter.setPen(QPen(line_color))
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(tip_rect.adjusted(6, 4, -4, -4), tooltip)

        painter.end()

    def _draw_empty(self, painter, w, h):
        painter.setPen(QPen(QColor(c('text_muted'))))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                         "Démarrez le bot pour voir la courbe d'équité")

    def mouseMoveEvent(self, event):
        if len(self._equity_history) < 2:
            return
        pad_l = 72
        chart_w = self.width() - pad_l - 16
        mx = event.position().x() - pad_l
        idx = int(mx / chart_w * (len(self._equity_history) - 1))
        self._hover_index = max(0, min(idx, len(self._equity_history) - 1))
        self.update()

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()


class EquityChartWidget(QWidget):
    """Widget complet avec en-tête et métriques"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # En-tête avec métriques clés
        header = QHBoxLayout()

        self._equity_label = QLabel("Équité : —")
        self._equity_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.addWidget(self._equity_label)

        header.addStretch()

        self._return_label = QLabel("Rendement : —")
        self._return_label.setFont(QFont("Segoe UI", 10))
        header.addWidget(self._return_label)

        self._dd_label = QLabel("Drawdown max : —")
        self._dd_label.setFont(QFont("Segoe UI", 10))
        header.addWidget(self._dd_label)

        layout.addLayout(header)

        # Graphique
        self.chart = EquityChart()
        layout.addWidget(self.chart)

    def update_data(self, equity_history: list, initial_capital: float = 10000.0):
        """Met à jour graphique + métriques"""
        self.chart.set_data(equity_history, initial_capital)

        if not equity_history:
            return

        values = [v for _, v in equity_history]
        current = values[-1]
        ref = initial_capital
        ret_pct = (current / ref - 1) * 100

        # Drawdown max
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (v / peak - 1) * 100
            if dd < max_dd:
                max_dd = dd

        col = c('success') if ret_pct >= 0 else c('error')
        self._equity_label.setText(f"Équité : {current:,.2f}")
        self._return_label.setText(f"Rendement : {ret_pct:+.2f}%")
        self._return_label.setStyleSheet(f"color: {col};")
        self._dd_label.setText(f"Drawdown max : {max_dd:.2f}%")
        self._dd_label.setStyleSheet(f"color: {c('error')};")
