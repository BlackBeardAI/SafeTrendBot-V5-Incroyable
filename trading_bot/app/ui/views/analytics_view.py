"""
Vue Analytics - Analyses détaillées du journal de trading
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QTabWidget, QPushButton, QLabel, QHeaderView, QFileDialog, QMessageBox,
    QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from pathlib import Path
from datetime import datetime

from app.ui.widgets import PageHeader, Card, KPICard
from app.ui.theme import COLORS
from app.core.config_manager import config_manager


class AnalyticsView(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(PageHeader(
            "Analyses",
            "Analyses détaillées du journal de trading pour identifier ce qui fonctionne"
        ))

        # Actions
        actions = QHBoxLayout()
        refresh_btn = QPushButton("↻ Actualiser")
        refresh_btn.clicked.connect(self.refresh)
        actions.addWidget(refresh_btn)

        export_csv_btn = QPushButton("📥 Exporter CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        actions.addWidget(export_csv_btn)

        report_btn = QPushButton("📄 Générer rapport PDF")
        report_btn.clicked.connect(self._generate_pdf)
        actions.addWidget(report_btn)

        actions.addStretch()
        layout.addLayout(actions)

        # KPI globaux
        kpi_row = QHBoxLayout()
        self.total_trades_kpi = KPICard("Trades totaux", "—")
        self.win_rate_kpi = KPICard("Win rate global", "—")
        self.profit_factor_kpi = KPICard("Profit factor", "—")
        self.total_pnl_kpi = KPICard("P&L total", "—")
        kpi_row.addWidget(self.total_trades_kpi)
        kpi_row.addWidget(self.win_rate_kpi)
        kpi_row.addWidget(self.profit_factor_kpi)
        kpi_row.addWidget(self.total_pnl_kpi)
        layout.addLayout(kpi_row)

        # Tabs pour les différentes analyses
        tabs = QTabWidget()

        # Tab 1 : Par stratégie
        self.strategy_table = self._create_analysis_table(
            ["Stratégie", "Trades", "Gagnants", "Win rate", "Profit total", "Profit moyen"]
        )
        tabs.addTab(self._wrap_table(self.strategy_table), "Par stratégie")

        # Tab 2 : Par symbole
        self.symbol_table = self._create_analysis_table(
            ["Symbole", "Trades", "Gagnants", "Win rate", "Profit total", "Profit moyen"]
        )
        tabs.addTab(self._wrap_table(self.symbol_table), "Par symbole")

        # Tab 3 : Par heure
        self.hour_table = self._create_analysis_table(
            ["Heure", "Trades", "Gagnants", "Win rate", "Profit total"]
        )
        tabs.addTab(self._wrap_table(self.hour_table), "Par heure")

        # Tab 4 : Par volatilité
        self.volatility_table = self._create_analysis_table(
            ["Régime", "Trades", "Gagnants", "Win rate", "Profit total", "Profit moyen"]
        )
        tabs.addTab(self._wrap_table(self.volatility_table), "Par volatilité")

        # Tab 5 : Par confiance
        self.confidence_table = self._create_analysis_table(
            ["Niveau de confiance", "Trades", "Gagnants", "Win rate", "Profit total", "Profit moyen"]
        )
        tabs.addTab(self._wrap_table(self.confidence_table), "Par confiance")

        layout.addWidget(tabs)

    def _create_analysis_table(self, headers):
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        return table

    def _wrap_table(self, table):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 12, 0, 0)
        l.addWidget(table)
        return w

    def refresh(self):
        try:
            journal = self.engine.journal
            closed = journal.get_all(only_closed=True)

            # KPI globaux
            self.total_trades_kpi.set_value(str(len(closed)))
            if closed:
                wins = [t for t in closed if t.profit > 0]
                losses = [t for t in closed if t.profit < 0]
                win_rate = len(wins) / len(closed) * 100
                total_wins = sum(t.profit for t in wins)
                total_losses = abs(sum(t.profit for t in losses))
                pf = total_wins / total_losses if total_losses > 0 else float('inf')
                total_pnl = sum(t.profit for t in closed)

                self.win_rate_kpi.set_value(f"{win_rate:.1f}%")
                self.profit_factor_kpi.set_value(f"{pf:.2f}" if pf != float('inf') else "∞")
                color = COLORS['success'] if total_pnl >= 0 else COLORS['error']
                self.total_pnl_kpi.set_value(f"{total_pnl:+,.2f}", color)
            else:
                self.win_rate_kpi.set_value("—")
                self.profit_factor_kpi.set_value("—")
                self.total_pnl_kpi.set_value("—")

            # Tables d'analyse
            self._fill_strategy_analysis(journal)
            self._fill_symbol_analysis(journal)
            self._fill_hour_analysis(journal)
            self._fill_volatility_analysis(journal)
            self._fill_confidence_analysis(journal)
        except Exception as e:
            print(f"Erreur refresh analytics : {e}")

    def _fill_strategy_analysis(self, journal):
        stats = journal.analyze_by_strategy()
        self._fill_table(self.strategy_table, [
            [name, s['count'], s['wins'], f"{s['win_rate']:.1f}%",
             s['profit'], s['avg_profit']]
            for name, s in sorted(stats.items(), key=lambda x: x[1]['profit'], reverse=True)
        ])

    def _fill_symbol_analysis(self, journal):
        stats = journal.analyze_by_symbol()
        self._fill_table(self.symbol_table, [
            [sym, s['count'], s['wins'], f"{s['win_rate']:.1f}%",
             s['profit'], s['avg_profit']]
            for sym, s in sorted(stats.items(), key=lambda x: x[1]['profit'], reverse=True)
        ])

    def _fill_hour_analysis(self, journal):
        stats = journal.analyze_by_hour()
        self._fill_table(self.hour_table, [
            [f"{h:02d}:00", s['count'], s['wins'], f"{s['win_rate']:.1f}%", s['profit']]
            for h, s in sorted(stats.items()) if s['count'] > 0
        ])

    def _fill_volatility_analysis(self, journal):
        stats = journal.analyze_by_volatility()
        self._fill_table(self.volatility_table, [
            [regime, s['count'], s['wins'], f"{s['win_rate']:.1f}%",
             s['profit'], s['avg_profit']]
            for regime, s in sorted(stats.items(), key=lambda x: x[1]['profit'], reverse=True)
        ])

    def _fill_confidence_analysis(self, journal):
        stats = journal.analyze_by_confidence()
        self._fill_table(self.confidence_table, [
            [bucket, s['count'], s.get('wins', 0), f"{s['win_rate']:.1f}%",
             s['profit'], s.get('avg_profit', 0)]
            for bucket, s in stats.items()
        ])

    def _fill_table(self, table, rows):
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                # Formatage des nombres
                if isinstance(val, float):
                    if abs(val) < 0.01:
                        text = "0.00"
                    else:
                        text = f"{val:+,.2f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                # Coloration du profit (dernière colonne ou avant-dernière)
                if j == len(row) - 1 or j == len(row) - 2:
                    if isinstance(val, (int, float)) and val != 0:
                        color = QColor(COLORS['success']) if val > 0 else QColor(COLORS['error'])
                        item.setForeground(color)
                        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                table.setItem(i, j, item)

    def _export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exporter le journal",
            f"journal_trading_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV (*.csv)"
        )
        if filename:
            try:
                self.engine.journal.export_csv(Path(filename))
                QMessageBox.information(self, "Export", f"Journal exporté :\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Erreur", str(e))

    def _generate_pdf(self):
        try:
            from app.core.pdf_reports import PDFReportGenerator, REPORTLAB_AVAILABLE
            if not REPORTLAB_AVAILABLE:
                QMessageBox.warning(self, "reportlab requis",
                                   "Installez reportlab avec : pip install reportlab")
                return

            filename, _ = QFileDialog.getSaveFileName(
                self, "Sauvegarder le rapport PDF",
                f"rapport_trading_{datetime.now().strftime('%Y%m%d')}.pdf",
                "PDF (*.pdf)"
            )
            if not filename:
                return

            # Collecter les infos du compte
            account_info = {'currency': 'EUR', 'balance': 0, 'equity': 0}
            # (simplification - dans une vraie version, on lirait depuis le moteur)

            generator = PDFReportGenerator()
            generator.generate_weekly_report(
                self.engine.journal, account_info, Path(filename)
            )
            QMessageBox.information(self, "Rapport généré",
                                   f"Rapport sauvegardé :\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))
