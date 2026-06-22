#!/usr/bin/env python3
"""
SafeTrendBot V5 — Lanceur Windows (.pyw)
=========================================
Ce fichier est lance par pythonw.exe (pas de console noire).
Il redirige vers main.py avec gestion d'erreurs complete.
Si une erreur se produit, une boite de dialogue s'affiche.
"""

import sys
import os
import traceback
from pathlib import Path

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))


def show_error(title, message):
    """Affiche une erreur dans une boite de dialogue."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(f"SafeTrendBot V5 — {title}")
        msg.setText(message)
        msg.exec()
    except Exception:
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(f"SafeTrendBot V5 — {title}", message)
            root.destroy()
        except Exception:
            pass  # On ne peut rien faire de plus


def main():
    try:
        # Lancer le vrai main.py
        import main as _main
        _main.main()
    except SystemExit:
        pass
    except Exception as e:
        tb = traceback.format_exc()
        show_error(
            "Erreur au demarrage",
            f"SafeTrendBot n'a pas pu demarrer.\n\n"
            f"Erreur: {e}\n\n"
            f"Détails:\n{tb[:800]}\n\n"
            f"Contactez @BlackBeardAI sur Telegram"
        )


if __name__ == "__main__":
    main()