"""
SafeTrendBot Builder — Exécute le builder avec interface graphique.
Usage: python run_builder.py
"""
import sys
from pathlib import Path

if __name__ == "__main__":
    # Vérifier les dépendances
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("❌ PyQt6 manquant — pip install PyQt6")
        sys.exit(1)

    try:
        import qrcode
    except ImportError:
        print("❌ qrcode manquant — pip install qrcode[pil]")
        sys.exit(1)

    from builder_gui import main
    main()
