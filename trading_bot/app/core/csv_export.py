"""
Export CSV de l'historique des trades.
Permet d'exporter le journal vers un fichier .csv pour analyse externe (Excel)
ou pour des besoins fiscaux.
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import List, Optional


def export_trades_to_csv(
    trades: List[dict],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Exporte une liste de trades au format CSV.

    Args:
        trades: liste de dicts avec les champs trade
        output_path: chemin de sortie (défaut: trades_export_YYYY-MM-DD.csv)

    Returns:
        Path du fichier créé
    """
    if output_path is None:
        date_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = Path(f"trades_export_{date_str}.csv")

    if not trades:
        # Créer un fichier vide avec en-têtes
        trades = []

    # Colonnes standardisées
    fieldnames = [
        'date_open', 'date_close', 'symbol', 'direction',
        'entry_price', 'exit_price', 'volume',
        'stop_loss', 'take_profit',
        'profit', 'profit_pips', 'commission', 'swap',
        'duration_minutes', 'strategy', 'confidence',
        'comment', 'magic',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        # utf-8-sig pour bonne ouverture dans Excel français
        writer = csv.DictWriter(
            f, fieldnames=fieldnames,
            delimiter=';',  # Séparateur ; pour Excel français
            extrasaction='ignore',
        )
        writer.writeheader()
        for trade in trades:
            # Normaliser les dates en string
            normalized = {}
            for k in fieldnames:
                v = trade.get(k, '')
                if isinstance(v, datetime):
                    v = v.strftime('%Y-%m-%d %H:%M:%S')
                normalized[k] = v
            writer.writerow(normalized)

    return output_path


def export_summary_to_csv(
    summary: dict,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Exporte un résumé agrégé (par stratégie, par symbole, etc.)

    Args:
        summary: dict avec différentes sections
            ex: {'by_symbol': {...}, 'by_strategy': {...}}
    """
    if output_path is None:
        date_str = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = Path(f"summary_export_{date_str}.csv")

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')

        for section_name, section_data in summary.items():
            writer.writerow([f"=== {section_name.upper()} ==="])
            if isinstance(section_data, dict):
                # Récupérer toutes les clés
                if section_data:
                    first_value = next(iter(section_data.values()))
                    if isinstance(first_value, dict):
                        # Format par clé
                        keys = list(first_value.keys())
                        writer.writerow(['Item'] + keys)
                        for key, vals in section_data.items():
                            writer.writerow([key] + [vals.get(k, '') for k in keys])
                    else:
                        # Format simple clé/valeur
                        for k, v in section_data.items():
                            writer.writerow([k, v])
            writer.writerow([])  # ligne vide

    return output_path
