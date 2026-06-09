"""
SafeTrendBot Builder GUI — Interface graphique du générateur
=============================================================

Usage:
    python builder_gui.py

Interface simple avec:
- Sélection du tier (Basic / Pro / EXTREME)
- Email du client
- Bouton "Générer le build"
- Barre de progression
- Log en temps réel
- Historique des builds générés
- QR code de paiement crypto (optionnel)

Pas besoin de ligne de commande.
"""

import sys
import os
import json
import subprocess
import threading
import qrcode
from pathlib import Path
from datetime import datetime
from io import BytesIO
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit, QProgressBar,
    QFrame, QScrollArea, QFileDialog, QMessageBox, QGroupBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent
BUILD_HISTORY_FILE = ROOT / "build_history.json"
TIER_CONFIG = {
    "basic": {"label": "Basic", "price": 99, "color": "#3b82f6"},
    "pro": {"label": "Pro", "price": 199, "color": "#f59e0b"},
    "extreme": {"label": "EXTREME", "price": 349, "color": "#ef4444"},
}


# ─────────────────────────────────────────────────────────────────────────────
# WORKER THREAD
# ─────────────────────────────────────────────────────────────────────────────

class BuilderWorker(QThread):
    """Thread séparé pour le build (ne bloque pas l'UI)."""

    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, dict)

    def __init__(self, tier: str, email: str, output: str):
        super().__init__()
        self.tier = tier
        self.email = email
        self.output = output

    def run(self):
        try:
            self.log.emit("🚀 Démarrage du build...")
            self.progress.emit(10)

            # Import builder en tant que module
            sys.path.insert(0, str(ROOT))
            from builder import build_single

            self.log.emit("   Génération de la licence...")
            self.progress.emit(25)

            self.log.emit("   Préparation du source...")
            self.progress.emit(40)

            self.log.emit("   Chiffrement des ressources...")
            self.progress.emit(55)

            self.log.emit("   Obfuscation du code...")
            self.progress.emit(70)

            self.log.emit("   Compilation PyInstaller...")
            self.progress.emit(85)

            result = build_single(self.tier, self.email, self.output)

            self.progress.emit(100)
            self.finished.emit(result.get("success", False), result)

        except Exception as e:
            self.log.emit(f"❌ ERREUR: {e}")
            self.finished.emit(False, {})


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class BuilderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SafeTrendBot Builder V5")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(self._get_stylesheet())
        self.build_history = self._load_history()
        self._build_ui()

    def _get_stylesheet(self):
        return """
        QMainWindow { background: #0f172a; }
        QWidget { color: #f8fafc; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
        QLabel { color: #94a3b8; }
        QGroupBox { border: 1px solid #1e293b; border-radius: 12px; padding: 16px; margin-top: 8px; }
        QGroupBox::title { color: #f8fafc; font-weight: 600; padding: 0 8px; }
        QPushButton {
            background: #3b82f6; color: white; border: none; border-radius: 8px;
            padding: 12px 24px; font-weight: 600; font-size: 14px;
        }
        QPushButton:hover { background: #2563eb; }
        QPushButton:disabled { background: #334155; color: #64748b; }
        QPushButton.success { background: #10b981; }
        QPushButton.danger { background: #ef4444; }
        QComboBox, QLineEdit {
            background: #1e293b; border: 1px solid #334155; border-radius: 8px;
            padding: 10px 14px; color: #f8fafc;
        }
        QComboBox::drop-down { border: none; }
        QTextEdit {
            background: #1e293b; border: 1px solid #334155; border-radius: 8px;
            padding: 12px; color: #94a3b8;
        }
        QProgressBar {
            background: #1e293b; border-radius: 6px; height: 8px;
            text-align: center;
        }
        QProgressBar::chunk {
            background: #3b82f6; border-radius: 6px;
        }
        QTableWidget {
            background: #1e293b; border: 1px solid #334155; border-radius: 8px;
            gridline-color: #334155;
        }
        QTableWidget::item { padding: 8px; }
        QHeaderView::section {
            background: #0f172a; color: #94a3b8; padding: 8px; border: none;
            font-weight: 600; font-size: 12px; text-transform: uppercase;
        }
        """

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # ─── LEFT PANEL: Build Form ───
        left = QVBoxLayout()
        left.setSpacing(16)

        # Header
        header = QLabel("🤖 SafeTrendBot Builder")
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.setStyleSheet("color: #f8fafc;")
        left.addWidget(header)

        subtitle = QLabel("Génère des builds uniques prêts à vendre")
        subtitle.setStyleSheet("color: #64748b; margin-bottom: 8px;")
        left.addWidget(subtitle)

        # Tier Selection
        tier_group = QGroupBox("🏷️ Sélection du Tier")
        tier_layout = QVBoxLayout(tier_group)

        self.tier_combo = QComboBox()
        for key, info in TIER_CONFIG.items():
            self.tier_combo.addItem(f"{info['label']} — ${info['price']}", key)
        self.tier_combo.currentIndexChanged.connect(self._on_tier_changed)
        tier_layout.addWidget(self.tier_combo)

        self.tier_desc = QLabel("Bot Basic — 3 positions max, 1% risque/trade")
        self.tier_desc.setWordWrap(True)
        self.tier_desc.setStyleSheet("color: #64748b; font-size: 12px;")
        tier_layout.addWidget(self.tier_desc)

        left.addWidget(tier_group)

        # Client Info
        client_group = QGroupBox("📧 Informations Client")
        client_layout = QVBoxLayout(client_group)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("client@example.com (optionnel)")
        client_layout.addWidget(QLabel("Email:"))
        client_layout.addWidget(self.email_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du client (optionnel)")
        client_layout.addWidget(QLabel("Nom:"))
        client_layout.addWidget(self.name_input)

        left.addWidget(client_group)

        # Options
        opts_group = QGroupBox("⚙️ Options")
        opts_layout = QVBoxLayout(opts_group)

        self.chk_encrypt = QPushButton("🔒 Chiffrement AES-256: ACTIVÉ")
        self.chk_encrypt.setEnabled(False)
        self.chk_encrypt.setStyleSheet("background: #10b981;")
        opts_layout.addWidget(self.chk_encrypt)

        self.chk_obfuscate = QPushButton("🛡️ Obfuscation Cython: ACTIVÉ")
        self.chk_obfuscate.setEnabled(False)
        self.chk_obfuscate.setStyleSheet("background: #10b981;")
        opts_layout.addWidget(self.chk_obfuscate)

        self.chk_hw_lock = QPushButton("🔐 Hardware Lock: ACTIVÉ")
        self.chk_hw_lock.setEnabled(False)
        self.chk_hw_lock.setStyleSheet("background: #10b981;")
        opts_layout.addWidget(self.chk_hw_lock)

        left.addWidget(opts_group)

        # Build Button
        self.build_btn = QPushButton("🚀 GÉNÉRER LE BUILD")
        self.build_btn.setMinimumHeight(50)
        self.build_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.build_btn.clicked.connect(self._start_build)
        left.addWidget(self.build_btn)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        left.addWidget(self.progress)

        # Log
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        self.log_output.setPlaceholderText("Log du build...")
        left.addWidget(QLabel("📋 Log:"))
        left.addWidget(self.log_output)

        layout.addLayout(left, 1)

        # ─── RIGHT PANEL: History + QR ───
        right = QVBoxLayout()
        right.setSpacing(16)

        # QR Code Section
        qr_group = QGroupBox("💰 Paiement Crypto")
        qr_layout = QVBoxLayout(qr_group)

        self.qr_label = QLabel("Sélectionnez un tier pour générer le QR")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumHeight(200)
        self.qr_label.setStyleSheet("background: #1e293b; border-radius: 12px;")
        qr_layout.addWidget(self.qr_label)

        self.qr_addr = QLabel("Adresse: (sélectionnez un tier)")
        self.qr_addr.setWordWrap(True)
        self.qr_addr.setStyleSheet("color: #64748b; font-size: 11px;")
        qr_layout.addWidget(self.qr_addr)

        self.qr_copy_btn = QPushButton("📋 Copier l'adresse")
        self.qr_copy_btn.clicked.connect(self._copy_address)
        self.qr_copy_btn.setEnabled(False)
        qr_layout.addWidget(self.qr_copy_btn)

        right.addWidget(qr_group)

        # Build History
        hist_group = QGroupBox("📦 Historique des Builds")
        hist_layout = QVBoxLayout(hist_group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Date", "Tier", "Licence", "Client", "Fichier"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._populate_history()
        hist_layout.addWidget(self.history_table)

        right.addWidget(hist_group)

        # Quick Actions
        actions_group = QGroupBox("⚡ Actions Rapides")
        actions_layout = QVBoxLayout(actions_group)

        btn_open_builds = QPushButton("📁 Ouvrir le dossier builds")
        btn_open_builds.clicked.connect(self._open_builds_dir)
        actions_layout.addWidget(btn_open_builds)

        btn_clean = QPushButton("🗑️ Nettoyer les anciens builds")
        btn_clean.setStyleSheet("background: #ef4444;")
        btn_clean.clicked.connect(self._clean_builds)
        actions_layout.addWidget(btn_clean)

        right.addWidget(actions_group)
        right.addStretch()

        layout.addLayout(right, 1)

    # ─── Logic ───

    def _on_tier_changed(self):
        tier = self.tier_combo.currentData()
        info = TIER_CONFIG.get(tier, {})
        desc = {
            "basic": "Bot Basic — 3 positions max, 1% risque/trade, Safe + Normal modes",
            "pro": "Bot Pro — 5 positions max, 2% risque/trade, tous les modes",
            "extreme": "🔥🔥 Bot EXTREME — 8 positions, 5% risque, SL ultra-serré, max rendement",
        }
        self.tier_desc.setText(desc.get(tier, ""))
        self.tier_desc.setStyleSheet(f"color: {info.get('color', '#64748b')}; font-size: 12px;")

        # Generate QR
        self._generate_qr(tier)

    def _generate_qr(self, tier: str):
        """Génère un QR code avec une adresse de paiement."""
        # Fake address for demo — en production, utilise ta vraie adresse
        fake_addresses = {
            "basic": "TXY8x9K2mP3Q4rT5vW6zB7nJ8mK9pL0qR",
            "pro": "TXY8x9K2mP3Q4rT5vW6zB7nJ8mK9pL0qR",
            "extreme": "TXY8x9K2mP3Q4rT5vW6zB7nJ8mK9pL0qR",
        }
        addr = fake_addresses.get(tier, "")
        price = TIER_CONFIG.get(tier, {}).get("price", 0)

        # Create QR
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(f"tron:{addr}?amount={price}")
        qr.make(fit=True)

        img = qr.make_image(fill_color="white", back_color="#1e293b")
        buffer = BytesIO()
        img.save(buffer, "PNG")

        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        self.qr_label.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio))

        self.qr_addr.setText(f"Adresse USDT (TRC20):\n{addr}\n\nMontant: ${price}")
        self.qr_copy_btn.setEnabled(True)
        self._current_address = addr

    def _copy_address(self):
        if hasattr(self, '_current_address'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self._current_address)
            QMessageBox.information(self, "Copié", "Adresse copiée dans le presse-papiers!")

    def _start_build(self):
        tier = self.tier_combo.currentData()
        email = self.email_input.text().strip()
        output = f"SafeTrendBot_{tier}"

        self.build_btn.setEnabled(False)
        self.build_btn.setText("⏳ BUILD EN COURS...")
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log_output.clear()

        self.worker = BuilderWorker(tier, email, output)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self._append_log)
        self.worker.finished.connect(self._build_finished)
        self.worker.start()

    def _append_log(self, text: str):
        self.log_output.append(text)
        # Auto-scroll
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _build_finished(self, success: bool, result: dict):
        self.build_btn.setEnabled(True)
        self.build_btn.setText("🚀 GÉNÉRER LE BUILD")
        self.progress.setVisible(False)

        if success:
            # Add to history
            entry = {
                "date": datetime.now().isoformat(),
                "tier": result.get("tier", "?"),
                "license": result.get("license", "?"),
                "email": result.get("email", ""),
                "zip": result.get("zip", ""),
            }
            self.build_history.append(entry)
            self._save_history()
            self._populate_history()

            # Show success dialog
            zip_path = result.get("zip", "")
            license_key = result.get("license", "")
            reply = QMessageBox.question(
                self, "✅ Build Terminé",
                f"Build généré avec succès!\n\n"
                f"Licence: {license_key}\n"
                f"Fichier: {zip_path}\n\n"
                f"Ouvrir le dossier builds?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._open_builds_dir()
        else:
            QMessageBox.critical(self, "❌ Échec", "Le build a échoué. Consultez le log.")

    def _load_history(self) -> list:
        if BUILD_HISTORY_FILE.exists():
            return json.loads(BUILD_HISTORY_FILE.read_text(encoding="utf-8"))
        return []

    def _save_history(self):
        BUILD_HISTORY_FILE.write_text(json.dumps(self.build_history, indent=2), encoding="utf-8")

    def _populate_history(self):
        self.history_table.setRowCount(len(self.build_history))
        for i, entry in enumerate(reversed(self.build_history)):
            self.history_table.setItem(i, 0, QTableWidgetItem(entry.get("date", "")[:16]))
            self.history_table.setItem(i, 1, QTableWidgetItem(entry.get("tier", "").upper()))
            self.history_table.setItem(i, 2, QTableWidgetItem(entry.get("license", "")[:20] + "..."))
            self.history_table.setItem(i, 3, QTableWidgetItem(entry.get("email", "")[:20]))
            self.history_table.setItem(i, 4, QTableWidgetItem(Path(entry.get("zip", "")).name[:30]))

    def _open_builds_dir(self):
        builds_dir = ROOT / "builds"
        builds_dir.mkdir(exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(builds_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(builds_dir)])
        else:
            subprocess.run(["xdg-open", str(builds_dir)])

    def _clean_builds(self):
        reply = QMessageBox.warning(
            self, "Confirmer",
            "Supprimer tous les anciens builds?\nCette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            builds_dir = ROOT / "builds"
            if builds_dir.exists():
                shutil.rmtree(builds_dir)
                builds_dir.mkdir()
            self.build_history.clear()
            self._save_history()
            self._populate_history()
            QMessageBox.information(self, "Terminé", "Builds nettoyés.")


def main():
    app = QApplication(sys.argv)
    window = BuilderWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
