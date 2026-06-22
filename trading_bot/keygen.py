#!/usr/bin/env python3
"""
SafeTrendBot V5 — Générateur de Clés de Licence
=================================================
Application standalone pour générer des clés de licence.

Usage:
    python keygen.py                  # Interface graphique
    python keygen.py --cli             # Mode console (génère 1 clé)
    python keygen.py --cli --count 5   # Génère 5 clés

Pour créer un .exe standalone:
    pyinstaller --onefile --noconsole --name "SafeTrendBot-KeyGen" keygen.py
"""

import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime

# Ajouter le path pour imports
sys.path.insert(0, str(Path(__file__).parent))


def generate_key():
    """Génère une clé de licence valide."""
    from app.core.simple_license import generate_key as _gen
    return _gen()


def validate_key(key):
    """Valide une clé de licence."""
    from app.core.simple_license import SimpleLicense
    lic = SimpleLicense(key)
    return lic.validate()


def save_keys(keys, filepath):
    """Sauvegarde les clés dans un fichier."""
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == '.json':
        data = []
        for key in keys:
            data.append({
                'key': key,
                'generated_at': datetime.now().isoformat(),
                'status': 'unused',
            })
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    elif ext == '.csv':
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['key', 'generated_at', 'status'])
            for key in keys:
                writer.writerow([key, datetime.now().isoformat(), 'unused'])
    else:
        # .txt ou autre
        with open(path, 'w', encoding='utf-8') as f:
            for key in keys:
                f.write(f"{key}\n")

    return path


def run_cli(count=1):
    """Mode console — génère et affiche des clés."""
    print("\n" + "=" * 50)
    print("  SafeTrendBot V5 — Générateur de Clés")
    print("=" * 50)
    print()

    keys = []
    for i in range(count):
        key = generate_key()
        valid = validate_key(key)
        keys.append(key)
        status = "✅ Valide" if valid else "❌ Invalide"
        print(f"  {i+1}. {key}  ({status})")

    print()

    # Proposer de sauvegarder
    if count > 0:
        save_path = Path(__file__).parent / "generated_keys.txt"
        save_keys(keys, save_path)
        print(f"  📁 Clés sauvegardées dans: {save_path}")

    return keys


def run_gui():
    """Interface graphique pour générer des clés."""
    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QLabel, QTextEdit, QSpinBox, QFileDialog,
            QMessageBox, QGroupBox, QLineEdit, QFrame
        )
        from PyQt6.QtGui import QFont, QColor, QClipboard
        from PyQt6.QtCore import Qt
    except ImportError:
        print("[ERREUR] PyQt6 non installé")
        print("Installez avec: pip install PyQt6")
        print("Ou utilisez le mode console: python keygen.py --cli")
        return 1

    class KeyGenWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("SafeTrendBot V5 — Générateur de Clés")
            self.setMinimumSize(600, 500)
            self.resize(650, 550)
            self.setStyleSheet("""
                QMainWindow { background: #0d1117; }
                QLabel { color: #c9d1d9; }
                QGroupBox {
                    color: #00d9ff;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 16px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px;
                    padding: 0 6px;
                }
                QPushButton {
                    background: #238636;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover { background: #2ea043; }
                QPushButton:pressed { background: #1a7f37; }
                QPushButton:disabled { background: #21262d; color: #6e7681; }
                QPushButton#secondary {
                    background: #21262d;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                }
                QPushButton#secondary:hover { background: #30363d; }
                QTextEdit {
                    background: #161b22;
                    color: #00d9ff;
                    border: 1px solid #30363d;
                    border-radius: 6px;
                    font-family: Consolas, monospace;
                    font-size: 14px;
                    padding: 8px;
                }
                QSpinBox {
                    background: #161b22;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 4px;
                    padding: 5px;
                    font-size: 13px;
                }
                QLineEdit {
                    background: #161b22;
                    color: #c9d1d9;
                    border: 1px solid #30363d;
                    border-radius: 4px;
                    padding: 5px;
                    font-family: Consolas, monospace;
                }
            """)

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)

            # Titre
            title = QLabel("🏴‍☠️ SafeTrendBot V5 — Générateur de Clés")
            title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            title.setStyleSheet("color: #00d9ff;")
            layout.addWidget(title)

            subtitle = QLabel("Génère des clés de licence au format STB5-XXXX-XXXX-XXXX")
            subtitle.setStyleSheet("color: #8b949e; font-size: 12px;")
            layout.addWidget(subtitle)

            # Groupe: Génération
            gen_group = QGroupBox("Génération")
            gen_layout = QHBoxLayout(gen_group)

            gen_layout.addWidget(QLabel("Nombre de clés:"))
            self.count_spin = QSpinBox()
            self.count_spin.setMinimum(1)
            self.count_spin.setMaximum(100)
            self.count_spin.setValue(1)
            gen_layout.addWidget(self.count_spin)

            gen_btn = QPushButton("⚡ Générer")
            gen_btn.clicked.connect(self.generate)
            gen_layout.addWidget(gen_btn)
            gen_layout.addStretch()

            layout.addWidget(gen_group)

            # Zone de résultats
            self.result_text = QTextEdit()
            self.result_text.setReadOnly(True)
            self.result_text.setPlaceholderText("Les clés générées apparaîtront ici...")
            layout.addWidget(self.result_text)

            # Groupe: Actions
            actions_group = QGroupBox("Actions")
            actions_layout = QHBoxLayout(actions_group)

            copy_btn = QPushButton("📋 Copier tout")
            copy_btn.setObjectName("secondary")
            copy_btn.clicked.connect(self.copy_all)
            actions_layout.addWidget(copy_btn)

            save_btn = QPushButton("💾 Sauvegarder (.txt)")
            save_btn.setObjectName("secondary")
            save_btn.clicked.connect(lambda: self.save_keys('txt'))
            actions_layout.addWidget(save_btn)

            save_csv_btn = QPushButton("📊 Sauvegarder (.csv)")
            save_csv_btn.setObjectName("secondary")
            save_csv_btn.clicked.connect(lambda: self.save_keys('csv'))
            actions_layout.addWidget(save_csv_btn)

            save_json_btn = QPushButton("🗂️ Sauvegarder (.json)")
            save_json_btn.setObjectName("secondary")
            save_json_btn.clicked.connect(lambda: self.save_keys('json'))
            actions_layout.addWidget(save_json_btn)

            layout.addWidget(actions_group)

            # Groupe: Validation
            val_group = QGroupBox("Valider une clé")
            val_layout = QHBoxLayout(val_group)

            val_layout.addWidget(QLabel("Clé:"))
            self.validate_input = QLineEdit()
            self.validate_input.setPlaceholderText("STB5-XXXX-XXXX-XXXX")
            val_layout.addWidget(self.validate_input)

            val_btn = QPushButton("✓ Valider")
            val_btn.setObjectName("secondary")
            val_btn.clicked.connect(self.validate_single)
            val_layout.addWidget(val_btn)

            layout.addWidget(val_group)

            self.keys = []

        def generate(self):
            count = self.count_spin.value()
            self.keys = []
            self.result_text.clear()

            text = f"╔════════════════════════════════════════╗\n"
            text += f"║  {count} clé(s) générée(s) — {datetime.now().strftime('%Y-%m-%d %H:%M')}║\n"
            text += f"╚════════════════════════════════════════╝\n\n"

            for i in range(count):
                try:
                    key = generate_key()
                    valid = validate_key(key)
                    self.keys.append(key)
                    icon = "✅" if valid else "❌"
                    text += f"  {i+1:3d}. {key}  {icon}\n"
                except Exception as e:
                    text += f"  {i+1:3d}. ERREUR: {e}\n"

            text += f"\n  Total: {len(self.keys)} clé(s)"

            self.result_text.setPlainText(text)

        def copy_all(self):
            if not self.keys:
                QMessageBox.information(self, "Info", "Aucune clé à copier. Génère d'abord des clés.")
                return
            text = "\n".join(self.keys)
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copié", f"{len(self.keys)} clé(s) copiée(s) dans le presse-papier.")

        def save_keys(self, fmt):
            if not self.keys:
                QMessageBox.information(self, "Info", "Aucune clé à sauvegarder. Génère d'abord des clés.")
                return

            ext = {'txt': '.txt', 'csv': '.csv', 'json': '.json'}[fmt]
            default_name = f"keys_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

            filepath, _ = QFileDialog.getSaveFileName(
                self, "Sauvegarder les clés", default_name,
                f"Fichier {fmt.upper()} (*{ext});;Tous les fichiers (*)"
            )

            if filepath:
                try:
                    save_keys(self.keys, filepath)
                    QMessageBox.information(self, "Sauvegardé", f"Clés sauvegardées dans:\n{filepath}")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Impossible de sauvegarder:\n{e}")

        def validate_single(self):
            key = self.validate_input.text().strip().upper()
            if not key:
                QMessageBox.warning(self, "Attention", "Entre une clé à valider.")
                return

            valid = validate_key(key)
            if valid:
                QMessageBox.information(self, "Valide", f"✅ Clé valide!\n\n{key}")
            else:
                QMessageBox.warning(self, "Invalide", f"❌ Clé invalide!\n\n{key}\n\nFormat attendu: STB5-XXXX-XXXX-XXXX")

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("SafeTrendBot KeyGen")
    window = KeyGenWindow()
    window.show()
    return app.exec()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SafeTrendBot V5 — Générateur de clés de licence")
    parser.add_argument("--cli", action="store_true", help="Mode console (pas de GUI)")
    parser.add_argument("--count", type=int, default=1, help="Nombre de clés à générer (mode CLI)")
    args = parser.parse_args()

    if args.cli:
        run_cli(args.count)
    else:
        sys.exit(run_gui())


if __name__ == "__main__":
    main()