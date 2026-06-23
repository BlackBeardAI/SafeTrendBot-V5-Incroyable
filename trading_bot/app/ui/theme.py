"""
Thème et styles de l'application.
Gère proprement le basculement dark/light sans perdre les couleurs.
"""

from PyQt6.QtGui import QPalette, QColor


# ============================================================================
# PALETTES
# ============================================================================

COLORS_DARK = {
    'bg_primary': '#0f1419',
    'bg_secondary': '#161c24',
    'sidebar_bg': '#0a0e13',
    'accent': '#2563eb',
    'accent_hover': '#1d4ed8',
    'primary': '#2563eb',
    'primary_hover': '#1d4ed8',
    'success': '#10b981',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'text_primary': '#f1f5f9',
    'text_secondary': '#94a3b8',
    'text_muted': '#64748b',
    'border': '#1e293b',
    'hover': '#1e293b',
    'card_bg': '#1a2028',
    'surface_variant': '#1a2028',
}

COLORS_LIGHT = {
    'bg_primary': '#ffffff',        # Fond principal blanc pur
    'bg_secondary': '#f8fafc',      # Fond légèrement gris
    'sidebar_bg': '#f1f5f9',        # Sidebar gris clair
    'accent': '#2563eb',            # Bleu vif
    'accent_hover': '#1d4ed8',
    'primary': '#2563eb',
    'primary_hover': '#1d4ed8',
    'success': '#059669',           # Vert foncé (contraste)
    'warning': '#d97706',           # Orange foncé
    'error': '#dc2626',             # Rouge foncé
    'text_primary': '#0f172a',      # Quasi-noir (très lisible)
    'text_secondary': '#334155',    # Gris foncé (plus lisible qu'avant)
    'text_muted': '#64748b',        # Gris moyen
    'border': '#cbd5e1',            # Bordure plus marquée
    'hover': '#e2e8f0',             # Hover léger
    'card_bg': '#ffffff',           # Cartes blanches
    'surface_variant': '#f1f5f9',
}

# Palette active (commence en dark)
COLORS = dict(COLORS_DARK)


def _build_stylesheet(palette: dict) -> str:
    return f"""
        QMainWindow, QDialog {{
            background-color: {palette['bg_primary']};
            color: {palette['text_primary']};
        }}
        QWidget {{
            background-color: transparent;
            color: {palette['text_primary']};
            font-family: "Segoe UI", sans-serif;
        }}

        /* ==== WIDGETS REUTILISABLES (selecteurs forts) ==== */
        QFrame#Card, QFrame#KPICard {{
            background-color: {palette['card_bg']};
            border: 1px solid {palette['border']};
            border-radius: 8px;
        }}
        QFrame#Card > QLabel#CardTitle,
        QLabel#CardTitle {{
            color: {palette['text_secondary']};
            background: transparent;
        }}
        QFrame#KPICard > QLabel#KPITitle,
        QLabel#KPITitle {{
            color: {palette['text_secondary']};
            background: transparent;
        }}
        QFrame#KPICard > QLabel#KPIValue,
        QLabel#KPIValue {{
            color: {palette['text_primary']};
            background: transparent;
        }}
        QFrame#KPICard > QLabel#KPISubtitle,
        QLabel#KPISubtitle {{
            color: {palette['text_muted']};
            background: transparent;
        }}
        QWidget QLabel#PageTitle,
        QLabel#PageTitle {{
            color: {palette['text_primary']};
            background: transparent;
        }}
        QWidget QLabel#PageDescription,
        QLabel#PageDescription {{
            color: {palette['text_secondary']};
            background: transparent;
        }}
        /* Sidebar : fond et boutons */
        QWidget#Sidebar {{
            background-color: {palette['sidebar_bg']};
        }}
        QLabel#SidebarTitle {{
            color: {palette['text_primary']};
            background: transparent;
            padding: 4px 12px 0 12px;
        }}
        QLabel#SidebarSubtitle {{
            color: {palette['text_secondary']};
            background: transparent;
            padding: 0 12px 16px 12px;
        }}
        QLabel#SidebarSection {{
            color: {palette['text_muted']};
            background: transparent;
            padding: 0 12px;
        }}
        QPushButton#SidebarButton {{
            background: transparent;
            border: none;
            text-align: left;
            color: {palette['text_secondary']};
            border-radius: 6px;
            padding: 0 16px;
        }}
        QPushButton#SidebarButton:hover {{
            background: {palette['hover']};
            color: {palette['text_primary']};
        }}
        QPushButton#SidebarButton:checked {{
            background: {palette['accent']};
            color: white;
        }}
        QPushButton#ThemeButton {{
            background-color: transparent;
            color: {palette['text_primary']};
            border: 1px solid {palette['border']};
            border-radius: 16px;
            font-size: 14px;
        }}
        QPushButton#ThemeButton:hover {{
            background-color: {palette['hover']};
        }}
        QPushButton#StartButton {{
            background-color: {palette['accent']};
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            padding: 8px;
        }}
        QPushButton#StartButton:hover {{
            background-color: {palette['accent_hover']};
        }}
        QPushButton#StartButton:disabled {{
            background-color: {palette['hover']};
            color: {palette['text_muted']};
        }}
        QPushButton#StopButton {{
            background-color: transparent;
            color: {palette['text_primary']};
            border: 1px solid {palette['border']};
            border-radius: 6px;
            padding: 8px;
        }}
        QPushButton#StopButton:hover {{
            background-color: {palette['hover']};
        }}
        QPushButton#StopButton:disabled {{
            color: {palette['text_muted']};
        }}

        QScrollBar:vertical {{
            background: {palette['bg_secondary']};
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {palette['border']};
            border-radius: 5px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {palette['text_muted']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QTableWidget {{
            background-color: {palette['card_bg']};
            alternate-background-color: {palette['bg_secondary']};
            gridline-color: {palette['border']};
            border: 1px solid {palette['border']};
            border-radius: 6px;
            color: {palette['text_primary']};
        }}
        QTableWidget::item {{
            padding: 8px;
            color: {palette['text_primary']};
        }}
        QTableWidget::item:selected {{
            background-color: {palette['accent']};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {palette['bg_secondary']};
            color: {palette['text_secondary']};
            padding: 8px;
            border: none;
            border-bottom: 1px solid {palette['border']};
            font-weight: bold;
        }}
        QPushButton {{
            background-color: {palette['accent']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {palette['accent_hover']};
        }}
        QPushButton:disabled {{
            background-color: {palette['hover']};
            color: {palette['text_muted']};
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QDateEdit {{
            background-color: {palette['bg_secondary']};
            color: {palette['text_primary']};
            border: 1px solid {palette['border']};
            border-radius: 6px;
            padding: 6px 10px;
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
        QComboBox:focus, QTextEdit:focus {{
            border: 1px solid {palette['accent']};
        }}
        QLineEdit:disabled, QSpinBox:disabled {{
            background-color: {palette['hover']};
            color: {palette['text_muted']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QGroupBox {{
            border: 1px solid {palette['border']};
            border-radius: 6px;
            margin-top: 16px;
            padding-top: 12px;
            font-weight: bold;
            color: {palette['text_secondary']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            color: {palette['text_primary']};
        }}
        QTabWidget::pane {{
            border: 1px solid {palette['border']};
            border-radius: 6px;
            background-color: {palette['bg_secondary']};
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {palette['text_secondary']};
            padding: 10px 20px;
            border: none;
        }}
        QTabBar::tab:selected {{
            color: {palette['text_primary']};
            border-bottom: 2px solid {palette['accent']};
        }}
        QTabBar::tab:hover {{
            color: {palette['text_primary']};
        }}
        QCheckBox {{
            color: {palette['text_primary']};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid {palette['border']};
            border-radius: 4px;
            background: {palette['bg_secondary']};
        }}
        QCheckBox::indicator:checked {{
            background: {palette['accent']};
            border-color: {palette['accent']};
        }}
        QStatusBar {{
            background-color: {palette['sidebar_bg']};
            color: {palette['text_secondary']};
            border-top: 1px solid {palette['border']};
        }}
        QMenu {{
            background-color: {palette['card_bg']};
            color: {palette['text_primary']};
            border: 1px solid {palette['border']};
            border-radius: 6px;
        }}
        QMenu::item {{
            padding: 8px 24px;
        }}
        QMenu::item:selected {{
            background-color: {palette['accent']};
            color: white;
        }}
        QLabel {{
            background-color: transparent;
            color: {palette['text_primary']};
        }}
    """


def _apply_palette(app, palette: dict):
    qp = QPalette()
    qp.setColor(QPalette.ColorRole.Window, QColor(palette['bg_primary']))
    qp.setColor(QPalette.ColorRole.WindowText, QColor(palette['text_primary']))
    qp.setColor(QPalette.ColorRole.Base, QColor(palette['bg_secondary']))
    qp.setColor(QPalette.ColorRole.AlternateBase, QColor(palette['card_bg']))
    qp.setColor(QPalette.ColorRole.Text, QColor(palette['text_primary']))
    qp.setColor(QPalette.ColorRole.Button, QColor(palette['bg_secondary']))
    qp.setColor(QPalette.ColorRole.ButtonText, QColor(palette['text_primary']))
    qp.setColor(QPalette.ColorRole.Highlight, QColor(palette['accent']))
    qp.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
    qp.setColor(QPalette.ColorRole.ToolTipBase, QColor(palette['card_bg']))
    qp.setColor(QPalette.ColorRole.ToolTipText, QColor(palette['text_primary']))
    qp.setColor(QPalette.ColorRole.PlaceholderText, QColor(palette['text_muted']))
    app.setPalette(qp)


def apply_dark_theme(app):
    """Applique le thème sombre"""
    COLORS.clear()
    COLORS.update(COLORS_DARK)
    _apply_palette(app, COLORS)
    app.setStyleSheet(_build_stylesheet(COLORS))


def apply_light_theme(app):
    """Applique le thème clair"""
    COLORS.clear()
    COLORS.update(COLORS_LIGHT)
    _apply_palette(app, COLORS)
    app.setStyleSheet(_build_stylesheet(COLORS))
