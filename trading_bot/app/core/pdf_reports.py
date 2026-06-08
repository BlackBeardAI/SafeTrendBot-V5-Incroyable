"""
Générateur de rapports PDF hebdomadaires.
Utilise reportlab (pure Python, multi-plateforme).
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image as RLImage
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactif
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class PDFReportGenerator:
    """Génère des rapports PDF de performance de trading"""

    # Palette de couleurs
    BRAND_BLUE = colors.HexColor('#2563eb')
    BRAND_GREEN = colors.HexColor('#10b981')
    BRAND_RED = colors.HexColor('#ef4444')
    LIGHT_GRAY = colors.HexColor('#f1f5f9')
    DARK_GRAY = colors.HexColor('#475569')

    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab requis : pip install reportlab")

    def generate_weekly_report(self, journal, account_info: dict,
                               output_path: Path, week_end: Optional[datetime] = None) -> Path:
        """
        Génère un rapport hebdomadaire.

        Args:
            journal: TradeJournal instance
            account_info: Infos du compte (balance, currency, etc.)
            output_path: Où écrire le PDF
            week_end: Date de fin de semaine (default: maintenant)
        """
        if week_end is None:
            week_end = datetime.now()
        week_start = week_end - timedelta(days=7)

        # Filtrer les trades de la semaine
        all_trades = journal.get_all(only_closed=True)
        week_trades = [
            t for t in all_trades
            if t.exit_time and week_start <= t.exit_time <= week_end
        ]

        doc = SimpleDocTemplate(
            str(output_path), pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )

        story = []
        styles = self._get_styles()

        # Page 1 : Sommaire
        story.extend(self._cover_page(styles, week_start, week_end, week_trades, account_info))
        story.append(PageBreak())

        # Page 2 : Statistiques
        story.extend(self._statistics_page(styles, week_trades, account_info))
        story.append(PageBreak())

        # Page 3 : Courbe d'équité
        if MATPLOTLIB_AVAILABLE and week_trades:
            equity_img = self._create_equity_curve(week_trades, account_info)
            if equity_img:
                story.append(Paragraph("Courbe d'équité hebdomadaire", styles['Heading1']))
                story.append(Spacer(1, 10 * mm))
                story.append(equity_img)
                story.append(PageBreak())

        # Page 4 : Analyse par stratégie
        story.extend(self._strategy_analysis_page(styles, journal, week_trades))
        story.append(PageBreak())

        # Page 5 : Liste des trades
        story.extend(self._trades_list_page(styles, week_trades))

        doc.build(story)
        return output_path

    # ========================================================================
    # PAGES DU RAPPORT
    # ========================================================================

    def _cover_page(self, styles, week_start, week_end, trades, account_info):
        elements = []

        # Titre
        elements.append(Paragraph("RAPPORT HEBDOMADAIRE", styles['Title']))
        elements.append(Paragraph("SafeTrendBot Trading", styles['Subtitle']))
        elements.append(Spacer(1, 5 * mm))

        period = f"{week_start.strftime('%d %B %Y')} → {week_end.strftime('%d %B %Y')}"
        elements.append(Paragraph(period, styles['Centered']))
        elements.append(Spacer(1, 15 * mm))

        # Résumé en grande cartes
        total_profit = sum(t.profit for t in trades)
        win_rate = (sum(1 for t in trades if t.profit > 0) / len(trades) * 100) if trades else 0

        profit_color = self.BRAND_GREEN if total_profit >= 0 else self.BRAND_RED

        summary_data = [
            ["Performance de la semaine"],
            [f"{total_profit:+,.2f} {account_info.get('currency', 'EUR')}"],
            [f"{len(trades)} trades · {win_rate:.1f}% de réussite"],
        ]
        summary_table = Table(summary_data, colWidths=[15 * cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), self.LIGHT_GRAY),
            ('BACKGROUND', (0, 1), (0, 1), profit_color),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
            ('TEXTCOLOR', (0, 0), (0, 0), self.DARK_GRAY),
            ('FONTSIZE', (0, 0), (0, 0), 11),
            ('FONTSIZE', (0, 1), (0, 1), 28),
            ('FONTSIZE', (0, 2), (0, 2), 11),
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, self.DARK_GRAY),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15 * mm))

        # Infos compte
        account_data = [
            ["Compte", account_info.get('name', 'N/A')],
            ["Broker / Serveur", account_info.get('server', 'N/A')],
            ["Balance actuelle", f"{account_info.get('balance', 0):,.2f} {account_info.get('currency', '')}"],
            ["Équité actuelle", f"{account_info.get('equity', 0):,.2f} {account_info.get('currency', '')}"],
            ["Date de génération", datetime.now().strftime('%d/%m/%Y %H:%M')],
        ]
        account_table = Table(account_data, colWidths=[6 * cm, 9 * cm])
        account_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.LIGHT_GRAY),
            ('TEXTCOLOR', (0, 0), (0, -1), self.DARK_GRAY),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, self.DARK_GRAY),
        ]))
        elements.append(account_table)

        return elements

    def _statistics_page(self, styles, trades, account_info):
        elements = []
        elements.append(Paragraph("Statistiques détaillées", styles['Heading1']))
        elements.append(Spacer(1, 8 * mm))

        if not trades:
            elements.append(Paragraph("Aucun trade cette semaine.", styles['Body']))
            return elements

        # Calculs
        wins = [t for t in trades if t.profit > 0]
        losses = [t for t in trades if t.profit < 0]
        total_wins = sum(t.profit for t in wins)
        total_losses = abs(sum(t.profit for t in losses))

        stats = [
            ["Métrique", "Valeur"],
            ["Nombre total de trades", str(len(trades))],
            ["Trades gagnants", f"{len(wins)} ({len(wins)/len(trades)*100:.1f}%)"],
            ["Trades perdants", f"{len(losses)} ({len(losses)/len(trades)*100:.1f}%)"],
            ["Gain total", f"{total_wins:+,.2f}"],
            ["Perte totale", f"{-total_losses:,.2f}"],
            ["Profit net", f"{sum(t.profit for t in trades):+,.2f}"],
            ["Gain moyen", f"{(total_wins/len(wins) if wins else 0):+,.2f}"],
            ["Perte moyenne", f"{(-total_losses/len(losses) if losses else 0):,.2f}"],
            ["Profit factor", f"{total_wins/total_losses:.2f}" if total_losses > 0 else "∞"],
            ["Meilleur trade", f"{max((t.profit for t in trades), default=0):+,.2f}"],
            ["Pire trade", f"{min((t.profit for t in trades), default=0):+,.2f}"],
            ["Durée moyenne", f"{sum(t.duration_minutes for t in trades)/len(trades):.0f} min"],
        ]

        stats_table = Table(stats, colWidths=[8 * cm, 7 * cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, self.DARK_GRAY),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(stats_table)

        return elements

    def _strategy_analysis_page(self, styles, journal, week_trades):
        elements = []
        elements.append(Paragraph("Analyse par stratégie", styles['Heading1']))
        elements.append(Spacer(1, 8 * mm))

        # Ne prendre que les trades de la semaine
        strategy_stats = {}
        for entry in week_trades:
            for strat in entry.strategies_agreed:
                if strat not in strategy_stats:
                    strategy_stats[strat] = {'count': 0, 'wins': 0, 'profit': 0.0}
                strategy_stats[strat]['count'] += 1
                strategy_stats[strat]['profit'] += entry.profit
                if entry.profit > 0:
                    strategy_stats[strat]['wins'] += 1

        if not strategy_stats:
            elements.append(Paragraph("Pas de données de stratégie pour cette semaine.",
                                      styles['Body']))
            return elements

        data = [["Stratégie", "Trades", "Win rate", "Profit total"]]
        for name, stats in sorted(strategy_stats.items(),
                                  key=lambda x: x[1]['profit'], reverse=True):
            win_rate = stats['wins'] / stats['count'] * 100 if stats['count'] else 0
            data.append([
                name,
                str(stats['count']),
                f"{win_rate:.1f}%",
                f"{stats['profit']:+,.2f}",
            ])

        table = Table(data, colWidths=[7 * cm, 2.5 * cm, 2.5 * cm, 3 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, self.DARK_GRAY),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10 * mm))

        # Note explicative
        elements.append(Paragraph(
            "<i>Note : une stratégie apparaît dans la colonne 'Trades' si elle a voté "
            "en faveur du trade, même si d'autres stratégies ont aussi voté.</i>",
            styles['SmallItalic']
        ))

        return elements

    def _trades_list_page(self, styles, trades):
        elements = []
        elements.append(Paragraph("Liste des trades de la semaine", styles['Heading1']))
        elements.append(Spacer(1, 8 * mm))

        if not trades:
            elements.append(Paragraph("Aucun trade.", styles['Body']))
            return elements

        data = [["Date", "Symbole", "Dir.", "Vol.", "Entrée", "Sortie", "Raison", "P&L"]]
        for t in sorted(trades, key=lambda x: x.entry_time):
            profit_str = f"{t.profit:+,.2f}"
            data.append([
                t.entry_time.strftime('%d/%m %H:%M'),
                t.symbol,
                t.direction,
                f"{t.volume:.2f}",
                f"{t.entry_price:.5f}",
                f"{t.exit_price:.5f}" if t.exit_price else "—",
                t.exit_reason[:8],
                profit_str,
            ])

        table = Table(data, colWidths=[2.3 * cm, 1.8 * cm, 1 * cm, 1 * cm,
                                        2 * cm, 2 * cm, 1.8 * cm, 2 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.BRAND_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.3, self.DARK_GRAY),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        # Colorer la colonne P&L
        for i, t in enumerate(sorted(trades, key=lambda x: x.entry_time), start=1):
            color = self.BRAND_GREEN if t.profit >= 0 else self.BRAND_RED
            table.setStyle(TableStyle([
                ('TEXTCOLOR', (7, i), (7, i), color),
                ('FONTNAME', (7, i), (7, i), 'Helvetica-Bold'),
            ]))

        elements.append(table)
        return elements

    # ========================================================================
    # GRAPHIQUES
    # ========================================================================

    def _create_equity_curve(self, trades, account_info) -> Optional[RLImage]:
        """Crée la courbe d'équité en image"""
        if not MATPLOTLIB_AVAILABLE or not trades:
            return None

        sorted_trades = sorted(trades, key=lambda t: t.exit_time or t.entry_time)
        dates = [t.exit_time or t.entry_time for t in sorted_trades]
        cumulative = []
        running = 0
        for t in sorted_trades:
            running += t.profit
            cumulative.append(running)

        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(dates, cumulative, color='#2563eb', linewidth=2)
        ax.fill_between(dates, cumulative, 0,
                        where=[c >= 0 for c in cumulative],
                        color='#10b981', alpha=0.2)
        ax.fill_between(dates, cumulative, 0,
                        where=[c < 0 for c in cumulative],
                        color='#ef4444', alpha=0.2)
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
        ax.set_xlabel('Date')
        ax.set_ylabel(f'P&L cumulé ({account_info.get("currency", "")})')
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        plt.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)

        img = RLImage(buf, width=16 * cm, height=8 * cm)
        return img

    # ========================================================================
    # STYLES
    # ========================================================================

    def _get_styles(self):
        base = getSampleStyleSheet()
        styles = {
            'Title': ParagraphStyle(
                'CustomTitle', parent=base['Title'],
                fontSize=24, textColor=self.BRAND_BLUE,
                alignment=TA_CENTER, spaceAfter=6,
                fontName='Helvetica-Bold',
            ),
            'Subtitle': ParagraphStyle(
                'CustomSubtitle', parent=base['Normal'],
                fontSize=14, textColor=self.DARK_GRAY,
                alignment=TA_CENTER, spaceAfter=20,
            ),
            'Heading1': ParagraphStyle(
                'CustomH1', parent=base['Heading1'],
                fontSize=16, textColor=self.BRAND_BLUE,
                spaceAfter=8, fontName='Helvetica-Bold',
            ),
            'Body': ParagraphStyle(
                'CustomBody', parent=base['Normal'],
                fontSize=10, textColor=self.DARK_GRAY, leading=14,
            ),
            'Centered': ParagraphStyle(
                'Centered', parent=base['Normal'],
                fontSize=11, alignment=TA_CENTER,
                textColor=self.DARK_GRAY,
            ),
            'SmallItalic': ParagraphStyle(
                'SmallItalic', parent=base['Normal'],
                fontSize=9, textColor=self.DARK_GRAY,
                fontName='Helvetica-Oblique',
            ),
        }
        return styles


# ============================================================================
# PLANIFICATEUR DE RAPPORTS
# ============================================================================

import threading
from datetime import datetime, timedelta


class ReportScheduler:
    """Planifie l'envoi automatique des rapports hebdomadaires"""

    def __init__(self, journal, config_manager, output_dir: Path,
                 telegram_alerts=None):
        self.journal = journal
        self.config_manager = config_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.telegram_alerts = telegram_alerts
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ReportScheduler")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        # Générer un rapport chaque dimanche à 20h
        while not self._stop_event.is_set():
            now = datetime.now()
            if now.weekday() == 6 and now.hour == 20 and now.minute < 5:
                try:
                    self.generate_now()
                except Exception as e:
                    print(f"Erreur génération rapport : {e}")
                self._stop_event.wait(300)  # 5 minutes pour éviter double gen
            else:
                self._stop_event.wait(60)

    def generate_now(self, account_info: Optional[dict] = None) -> Path:
        """Génère un rapport maintenant"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab non installé")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output = self.output_dir / f'rapport_hebdo_{timestamp}.pdf'

        if account_info is None:
            account_info = {'currency': 'EUR', 'balance': 0, 'equity': 0}

        generator = PDFReportGenerator()
        generator.generate_weekly_report(self.journal, account_info, output)
        return output
