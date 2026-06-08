"""
Génère les PDFs commerciaux à partir des guides markdown.
Usage: python generate_pdfs.py
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re


def markdown_to_pdf(input_md: Path, output_pdf: Path, title: str):
    """Convertit un fichier markdown en PDF"""
    
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#cba6f7'),
        spaceAfter=12,
        spaceBefore=20,
    )
    
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#89b4fa'),
        spaceAfter=10,
        spaceBefore=15,
    )
    
    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#cdd6f4'),
        spaceAfter=8,
        spaceBefore=10,
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
    )
    
    code_style = ParagraphStyle(
        'CustomCode',
        parent=styles['Code'],
        fontSize=9,
        fontName='Courier',
        textColor=colors.HexColor('#a6e3a1'),
        backColor=colors.HexColor('#1e1e2e'),
        leftIndent=10,
        spaceAfter=6,
    )
    
    warning_style = ParagraphStyle(
        'Warning',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#f38ba8'),
        backColor=colors.HexColor('#1e1e2e'),
        borderColor=colors.HexColor('#f38ba8'),
        borderWidth=1,
        borderPadding=8,
        spaceAfter=12,
    )
    
    # Lire le markdown
    content = input_md.read_text(encoding='utf-8')
    
    story = []
    
    # Page de titre
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("SafeTrendBot V5 — Ultra Edition", h2_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Document confidentiel — Usage interne", body_style))
    story.append(PageBreak())
    
    # Parsing simple du markdown
    lines = content.split('\n')
    in_code = False
    code_buffer = []
    in_table = False
    table_data = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip les lignes vides hors code
        if not stripped and not in_code:
            continue
        
        # Détection code block
        if stripped.startswith('```'):
            if in_code:
                # Fin du bloc
                if code_buffer:
                    code_text = '<br/>'.join(code_buffer)
                    story.append(Paragraph(code_text, code_style))
                    code_buffer = []
                in_code = False
            else:
                in_code = True
            continue
        
        if in_code:
            # Échapper les caractères spéciaux
            escaped = stripped.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            code_buffer.append(escaped)
            continue
        
        # Titres
        if stripped.startswith('# ') and not stripped.startswith('## '):
            text = stripped[2:]
            story.append(Paragraph(text, h1_style))
            continue
        elif stripped.startswith('## '):
            text = stripped[3:]
            story.append(Paragraph(text, h2_style))
            continue
        elif stripped.startswith('### '):
            text = stripped[4:]
            story.append(Paragraph(text, h3_style))
            continue
        elif stripped.startswith('#### '):
            text = stripped[5:]
            story.append(Paragraph(text, h3_style))
            continue
        
        # Tables (détection simple)
        if '|' in stripped and not stripped.startswith('```'):
            cells = [c.strip() for c in stripped.split('|') if c.strip()]
            if cells and not all(c.replace('-', '').replace(':', '') == '' for c in cells):
                table_data.append(cells)
            continue
        else:
            if table_data:
                # Rendre la table
                if len(table_data) >= 2:
                    col_count = max(len(row) for row in table_data)
                    # Normaliser les lignes
                    for row in table_data:
                        while len(row) < col_count:
                            row.append('')
                    
                    table = Table(table_data, repeatRows=1)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e1e2e')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#cba6f7')),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#313244')),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#cdd6f4')),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#45475a')),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.5*cm))
                table_data = []
        
        # Blockquote / warning
        if stripped.startswith('>'):
            text = stripped[1:].strip()
            text = text.replace('**', '').replace('*', '')
            story.append(Paragraph(text, warning_style))
            continue
        
        # Listes
        if stripped.startswith('- ') or stripped.startswith('* '):
            text = stripped[2:]
            text = re.sub(r'\*\*(.*?)\*\*', r'&lt;b&gt;\1&lt;/b&gt;', text)
            text = re.sub(r'`(.*?)`', r'&lt;code&gt;\1&lt;/code&gt;', text)
            story.append(Paragraph(f"• {text}", body_style))
            continue
        
        # Texte normal
        if stripped:
            # Markdown bold/italic/code
            text = stripped
            text = re.sub(r'\*\*(.*?)\*\*', r'&lt;b&gt;\1&lt;/b&gt;', text)
            text = re.sub(r'\*(.*?)\*', r'&lt;i&gt;\1&lt;/i&gt;', text)
            text = re.sub(r'`(.*?)`', r'&lt;code&gt;\1&lt;/code&gt;', text)
            story.append(Paragraph(text, body_style))
    
    # Dernière table si existante
    if table_data:
        if len(table_data) >= 2:
            col_count = max(len(row) for row in table_data)
            for row in table_data:
                while len(row) < col_count:
                    row.append('')
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e1e2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#cba6f7')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#45475a')),
            ]))
            story.append(table)
    
    # Footer sur chaque page
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6c7086'))
        canvas.drawString(2*cm, 1*cm, "SafeTrendBot V5 Ultra — Document confidentiel")
        canvas.drawRightString(A4[0]-2*cm, 1*cm, f"Page {doc.page}")
        canvas.restoreState()
    
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    print(f"✅ PDF généré : {output_pdf}")


def main():
    docs_dir = Path(__file__).parent / "docs"
    output_dir = Path(__file__).parent / "docs" / "pdf"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = [
        ("USER_GUIDE.md", "SafeTrendBot_V5_User_Guide.pdf", "Guide Utilisateur Complet"),
        ("TUNNEL_VENTE.md", "SafeTrendBot_V5_Tunnel_Vente.pdf", "Tunnel de Vente"),
    ]
    
    for md_name, pdf_name, title in files:
        md_path = docs_dir / md_name
        pdf_path = output_dir / pdf_name
        if md_path.exists():
            markdown_to_pdf(md_path, pdf_path, title)
        else:
            print(f"❌ {md_path} introuvable")
    
    print(f"\n📁 PDFs disponibles dans : {output_dir}")


if __name__ == "__main__":
    main()
