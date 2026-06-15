"""
SafeTrendBot Builder GUI — Interface graphique améliorée
=======================================================
Interface moderne pour générer des builds protégés.
"""

import sys
import os
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# UI Framework
try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
        QTableWidget, QTableWidgetItem, QTabWidget, QComboBox, QSpinBox,
        QCheckBox, QRadioButton, QGroupBox, QMessageBox, QFileDialog,
        QProgressDialog, QStatusBar, QMenuBar, QMenu, QDialog, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
    from PyQt6.QtGui import QAction, QIcon, QPalette, QColor, QFont
    UI_FRAMEWORK = "PyQt6"
except ImportError:
    try:
        from PyQt5.QtWidgets import (
            QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
            QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
            QTableWidget, QTableWidgetItem, QTabWidget, QComboBox, QSpinBox,
            QCheckBox, QRadioButton, QGroupBox, QMessageBox, QFileDialog,
            QProgressDialog, QStatusBar, QMenuBar, QMenu, QDialog, QFrame
        )
        from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
        from PyQt5.QtGui import QAction, QIcon, QPalette, QColor, QFont
        UI_FRAMEWORK = "PyQt5"
    except ImportError:
        print("PyQt5/PyQt6 requis. Install: pip install PyQt6")
        sys.exit(1)

# Ajouter le parent au path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from builder.license_builder import (
    SafeTrendBotBuilder, BuildConfig, LicenseGenerator, LicenseDatabase, VERSION
)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════════════════════

DARK_STYLE = """
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #16213e;
}

QLabel {
    color: #e0e0e0;
}

QLabel#title {
    font-size: 24px;
    font-weight: bold;
    color: #00d9ff;
}

QLabel#subtitle {
    font-size: 14px;
    color: #888;
}

QPushButton {
    background-color: #0f3460;
    color: #fff;
    border: 1px solid #0f3460;
    border-radius: 5px;
    padding: 8px 16px;
    min-height: 30px;
}

QPushButton:hover {
    background-color: #165a8a;
}

QPushButton:pressed {
    background-color: #0a2540;
}

QPushButton#primary {
    background-color: #00d9ff;
    color: #000;
    font-weight: bold;
    border: none;
}

QPushButton#primary:hover {
    background-color: #33e5ff;
}

QPushButton#danger {
    background-color: #e74c3c;
    border: none;
}

QPushButton#danger:hover {
    background-color: #c0392b;
}

QPushButton#success {
    background-color: #27ae60;
    border: none;
}

QPushButton#success:hover {
    background-color: #2ecc71;
}

QLineEdit {
    background-color: #0d1117;
    color: #00d9ff;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border: 1px solid #00d9ff;
}

QTextEdit {
    background-color: #0d1117;
    color: #58a6ff;
    border: 1px solid #30363d;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
}

QTableWidget {
    background-color: #0d1117;
    alternate-background-color: #161b22;
    gridline-color: #30363d;
    border: 1px solid #30363d;
    border-radius: 4px;
}

QTableWidget::item {
    padding: 5px;
}

QTableWidget::item:selected {
    background-color: #1f6feb;
}

QHeaderView::section {
    background-color: #0d1117;
    color: #00d9ff;
    padding: 8px;
    border: none;
    font-weight: bold;
}

QTabWidget::pane {
    border: 1px solid #30363d;
    border-radius: 4px;
    background-color: #1a1a2e;
}

QTabBar::tab {
    background-color: #0d1117;
    color: #888;
    padding: 10px 20px;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #1a1a2e;
    color: #00d9ff;
    border-bottom: 2px solid #00d9ff;
}

QSpinBox, QComboBox {
    background-color: #0d1117;
    color: #00d9ff;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 5px;
}

QSpinBox:focus, QComboBox:focus {
    border: 1px solid #00d9ff;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #0d1117;
    color: #00d9ff;
    selection-background-color: #1f6feb;
}

QGroupBox {
    border: 1px solid #30363d;
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    color: #00d9ff;
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QProgressBar {
    border: 1px solid #30363d;
    border-radius: 4px;
    background-color: #0d1117;
    text-align: center;
    color: #00d9ff;
}

QProgressBar::chunk {
    background-color: #00d9ff;
    border-radius: 3px;
}

QStatusBar {
    background-color: #0d1117;
    color: #888;
}

QMenuBar {
    background-color: #0d1117;
    color: #e0e0e0;
}

QMenuBar::item:selected {
    background-color: #1f6feb;
}

QMenu {
    background-color: #0d1117;
    color: #e0e0e0;
    border: 1px solid #30363d;
}

QMenu::item:selected {
    background-color: #1f6feb;
}

QCheckBox {
    color: #e0e0e0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #30363d;
    border-radius: 3px;
    background-color: #0d1117;
}

QCheckBox::indicator:checked {
    background-color: #00d9ff;
    border-color: #00d9ff;
}

QRadioButton {
    color: #e0e0e0;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #30363d;
    border-radius: 8px;
    background-color: #0d1117;
}

QRadioButton::indicator:checked {
    border-color: #00d9ff;
    background-color: #00d9ff;
}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# THREAD WORKER
# ═══════════════════════════════════════════════════════════════════════════════

class BuildWorker(QThread):
    """Thread worker pour les builds en arrière-plan."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, builder, config):
        super().__init__()
        self.builder = builder
        self.config = config
    
    def run(self):
        try:
            self.progress.emit(f"🚀 Build: {self.config.output_name}")
            success, msg = self.builder.build(self.config)
            self.finished.emit(success, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class BatchWorker(QThread):
    """Thread worker pour les batch builds."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    
    def __init__(self, builder, count, email_prefix, expiry_days, platform):
        super().__init__()
        self.builder = builder
        self.count = count
        self.email_prefix = email_prefix
        self.expiry_days = expiry_days
        self.platform = platform
    
    def run(self):
        try:
            results = self.builder.build_batch(
                count=self.count,
                email_prefix=self.email_prefix,
                expiry_days=self.expiry_days,
                platform=self.platform
            )
            self.finished.emit(results)
        except Exception as e:
            self.finished.emit([])


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class BuilderWindow(QWidget):
    """Fenêtre principale du Builder."""
    
    def __init__(self):
        super().__init__()
        
        self.builder = SafeTrendBotBuilder()
        self.build_worker: Optional[BuildWorker] = None
        self.batch_worker: Optional[BatchWorker] = None
        
        self._setup_ui()
        self._refresh_licenses()
    
    def _setup_ui(self):
        """Configure l'interface."""
        self.setWindowTitle(f"SafeTrendBot Builder v{VERSION}")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(DARK_STYLE)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header
        header = QVBoxLayout()
        title = QLabel("🔐 SafeTrendBot License Builder")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        header.addWidget(title)
        
        subtitle = QLabel("Générez des builds protégés pour distribution")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        header.addWidget(subtitle)
        
        layout.addLayout(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tab(), "📦 Générer Build")
        self.tabs.addTab(self._batch_tab(), "📋 Batch (Multi)")
        self.tabs.addTab(self._licenses_tab(), "🔑 Licences")
        self.tabs.addTab(self._server_tab(), "🖥️ Serveur Activation")
        self.tabs.addTab(self._settings_tab(), "⚙️ Configuration")
        
        layout.addWidget(self.tabs)
        
        # Log
        log_label = QLabel("📝 Console:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setMinimumHeight(80)
        layout.addWidget(self.log_text)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Prêt")
        layout.addWidget(self.status_bar)
        
        self.setLayout(layout)
    
    def _build_tab(self) -> QWidget:
        """Onglet génération de build unique."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Clé de licence
        key_group = QGroupBox("🔑 Clé de Licence")
        key_layout = QHBoxLayout()
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("STB5-XXXX-XXXX-XXXX (laisser vide pour générer)")
        self.key_input.setMinimumWidth(300)
        key_layout.addWidget(self.key_input)
        
        gen_key_btn = QPushButton("🎲 Générer")
        gen_key_btn.clicked.connect(self._generate_key)
        key_layout.addWidget(gen_key_btn)
        
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        # Client info
        info_group = QGroupBox("👤 Information Client")
        info_layout = QFormLayout()
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("client@exemple.com")
        info_layout.addRow("Email:", self.email_input)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Expiration & Plateforme
        options_group = QGroupBox("⏰ Expiration & Plateforme")
        options_layout = QHBoxLayout()
        
        # Expiration
        exp_layout = QVBoxLayout()
        self.expiry_check = QCheckBox("Activer expiration")
        exp_layout.addWidget(self.expiry_check)
        
        expiry_row = QHBoxLayout()
        self.expiry_days = QSpinBox()
        self.expiry_days.setMinimum(1)
        self.expiry_days.setMaximum(365)
        self.expiry_days.setValue(30)
        self.expiry_days.setEnabled(False)
        self.expiry_check.toggled.connect(self.expiry_days.setEnabled)
        expiry_row.addWidget(QLabel("Jours:"))
        expiry_row.addWidget(self.expiry_days)
        exp_layout.addLayout(expiry_row)
        options_layout.addLayout(exp_layout)
        
        # Plateforme
        plat_layout = QVBoxLayout()
        plat_layout.addWidget(QLabel("Plateforme:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["windows", "linux", "macos"])
        plat_layout.addWidget(self.platform_combo)
        options_layout.addLayout(plat_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Options advanced
        opts_group = QGroupBox("🔒 Options de Protection")
        opts_layout = QHBoxLayout()
        
        self.obfuscate_check = QCheckBox("Obfuscation PyArmor")
        self.obfuscate_check.setChecked(True)
        opts_layout.addWidget(self.obfuscate_check)
        
        self.cython_check = QCheckBox("Compilation Cython")
        self.cython_check.setChecked(True)
        opts_layout.addWidget(self.cython_check)
        
        self.pyinstaller_check = QCheckBox("PyInstaller (exe)")
        self.pyinstaller_check.setChecked(True)
        opts_layout.addWidget(self.pyinstaller_check)
        
        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)
        
        # Bouton build
        self.build_btn = QPushButton("🚀 GÉNÉRER LE BUILD")
        self.build_btn.setObjectName("primary")
        self.build_btn.setMinimumHeight(50)
        self.build_btn.clicked.connect(self._start_build)
        layout.addWidget(self.build_btn)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _batch_tab(self) -> QWidget:
        """Onglet batch."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Nombre
        count_group = QGroupBox("📊 Configuration Batch")
        count_layout = QFormLayout()
        
        self.batch_count = QSpinBox()
        self.batch_count.setMinimum(1)
        self.batch_count.setMaximum(100)
        self.batch_count.setValue(10)
        count_layout.addRow("Nombre de builds:", self.batch_count)
        
        self.batch_email_prefix = QLineEdit()
        self.batch_email_prefix.setText("client")
        count_layout.addRow("Préfixe email:", self.batch_email_prefix)
        
        count_group.setLayout(count_layout)
        layout.addWidget(count_group)
        
        # Options batch
        opts_group = QGroupBox("Options")
        opts_layout = QHBoxLayout()
        
        # Expiration
        expiry_layout = QVBoxLayout()
        expiry_layout.addWidget(QLabel("Expiration (0 = illimité):"))
        self.batch_expiry = QSpinBox()
        self.batch_expiry.setMinimum(0)
        self.batch_expiry.setMaximum(365)
        self.batch_expiry.setValue(30)
        expiry_layout.addWidget(self.batch_expiry)
        opts_layout.addLayout(expiry_layout)
        
        # Plateforme
        plat_layout = QVBoxLayout()
        plat_layout.addWidget(QLabel("Plateforme:"))
        self.batch_platform = QComboBox()
        self.batch_platform.addItems(["windows", "linux", "macos"])
        plat_layout.addWidget(self.batch_platform)
        opts_layout.addLayout(plat_layout)
        
        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)
        
        # Bouton
        self.batch_btn = QPushButton("📦 GÉNÉRER BATCH")
        self.batch_btn.setObjectName("primary")
        self.batch_btn.setMinimumHeight(50)
        self.batch_btn.clicked.connect(self._start_batch)
        layout.addWidget(self.batch_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _licenses_tab(self) -> QWidget:
        """Onglet gestion des licences."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Stats
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("📊 0 licences | 0 actives | 0 révoquées")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Table
        self.licenses_table = QTableWidget()
        self.licenses_table.setColumnCount(6)
        self.licenses_table.setHorizontalHeaderLabels([
            "Clé", "Email", "Expires", "Status", "Machine", "Activations"
        ])
        self.licenses_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.licenses_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.licenses_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.licenses_table)
        
        # Boutons
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Rafraîchir")
        refresh_btn.clicked.connect(self._refresh_licenses)
        btn_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("💾 Exporter CSV")
        export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_btn)
        
        revoke_btn = QPushButton("❌ Révoquer")
        revoke_btn.setObjectName("danger")
        revoke_btn.clicked.connect(self._revoke_selected)
        btn_layout.addWidget(revoke_btn)
        
        copy_btn = QPushButton("📋 Copier Clé")
        copy_btn.clicked.connect(self._copy_key)
        btn_layout.addWidget(copy_btn)
        
        layout.addLayout(btn_layout)
        
        tab.setLayout(layout)
        return tab
    
    def _server_tab(self) -> QWidget:
        """Onglet serveur d'activation."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Info
        info = QLabel("""🖥️ Serveur d'Activation en Ligne
        
Ce serveur permet de:
• Gérer les licences à distance
• Révoquer des licences instantanément
• Tracker les activations
• Recevoir des heartbeats

Pour lancer le serveur:
    cd server
    pip install flask
    python activation_server.py

Le serveur écoute sur le port 5000 par défaut.""")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Actions
        actions_group = QGroupBox("Actions Rapides")
        actions_layout = QHBoxLayout()
        
        open_server_btn = QPushButton("📂 Ouvrir dossier server")
        open_server_btn.clicked.connect(self._open_server_folder)
        actions_layout.addWidget(open_server_btn)
        
        start_server_btn = QPushButton("🚀 Démarrer Serveur (local)")
        start_server_btn.setObjectName("success")
        start_server_btn.clicked.connect(self._start_server)
        actions_layout.addWidget(start_server_btn)
        
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def _settings_tab(self) -> QWidget:
        """Onglet paramètres."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Versions
        version_group = QGroupBox("Versions")
        version_layout = QFormLayout()
        version_layout.addRow("Version:", QLabel(VERSION))
        version_layout.addRow("Python:", QLabel(sys.version.split()[0]))
        version_group.setLayout(version_layout)
        layout.addWidget(version_group)
        
        # Paths
        paths_group = QGroupBox("Chemins")
        paths_layout = QFormLayout()
        paths_layout.addRow("Project:", QLabel(str(self.builder.project_root)))
        paths_layout.addRow("Builds:", QLabel(str(self.builder.project_root / "builds")))
        paths_layout.addRow("Releases:", QLabel(str(self.builder.project_root / "releases")))
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        # Master key (warning)
        key_group = QGroupBox("⚠️ Sécurité")
        key_layout = QVBoxLayout()
        key_warning = QLabel("""ATTENTION: La MASTER_KEY dans license_builder.py 
doit être changée en production!
        
Ne jamais distribuer cette clé.""")
        key_warning.setStyleSheet("color: #e74c3c;")
        key_layout.addWidget(key_warning)
        
        change_key_btn = QPushButton("🔑 Générer nouvelle Master Key")
        change_key_btn.clicked.connect(self._generate_master_key)
        key_layout.addWidget(change_key_btn)
        
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SLOTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _log(self, msg: str):
        """Ajoute au log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {msg}")
        self.status_bar.showMessage(msg)
    
    def _generate_key(self):
        """Génère une clé."""
        key = LicenseGenerator.generate_key()
        self.key_input.setText(key)
        self._log(f"✅ Clé générée: {key}")
    
    def _start_build(self):
        """Lance un build."""
        key = self.key_input.text().strip() or LicenseGenerator.generate_key()
        email = self.email_input.text().strip()
        expiry = self.expiry_days.value() if self.expiry_check.isChecked() else None
        
        config = BuildConfig(
            license_key=key,
            email=email,
            expiry_days=expiry,
            platform=self.platform_combo.currentText(),
            obfuscate=self.obfuscate_check.isChecked(),
            compile_cython=self.cython_check.isChecked(),
        )
        
        self.build_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        self._log(f"🚀 Démarrage build...")
        
        self.build_worker = BuildWorker(self.builder, config)
        self.build_worker.progress.connect(self._log)
        self.build_worker.finished.connect(self._build_finished)
        self.build_worker.start()
    
    def _build_finished(self, success: bool, msg: str):
        """Callback fin de build."""
        self.build_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if success:
            self._log(f"✅ BUILD RÉUSSI: {msg}")
            self._refresh_licenses()
        else:
            self._log(f"❌ ERREUR: {msg}")
            QMessageBox.critical(self, "Erreur Build", msg)
    
    def _start_batch(self):
        """Lance un batch."""
        count = self.batch_count.value()
        expiry = self.batch_expiry.value() or None
        
        self.batch_btn.setEnabled(False)
        self._log(f"🚀 Batch: {count} builds...")
        
        self.batch_worker = BatchWorker(
            self.builder,
            count,
            self.batch_email_prefix.text(),
            expiry,
            self.batch_platform.currentText()
        )
        self.batch_worker.progress.connect(self._log)
        self.batch_worker.finished.connect(self._batch_finished)
        self.batch_worker.start()
    
    def _batch_finished(self, results: list):
        self.batch_btn.setEnabled(True)
        success_count = sum(1 for r in results if r["success"])
        self._log(f"✅ Batch terminé: {success_count}/{len(results)} réussie(s)")
        self._refresh_licenses()
        
        if success_count < len(results):
            QMessageBox.warning(
                self, "Batch partiel",
                f"{success_count}/{len(results)} builds réussis.\n"
                "Vérifiez la console pour les erreurs."
            )
    
    def _refresh_licenses(self):
        """Rafraîchit la table des licences."""
        licenses = self.builder.license_db.list_all()
        
        self.licenses_table.setRowCount(len(licenses))
        
        active_count = 0
        revoked_count = 0
        
        for i, lic in enumerate(licenses):
            self.licenses_table.setItem(i, 0, QTableWidgetItem(lic["key"]))
            self.licenses_table.setItem(i, 1, QTableWidgetItem(lic.get("email", "")))
            self.licenses_table.setItem(i, 2, QTableWidgetItem(
                lic.get("expires", "Jamais") or "Jamais"
            ))
            
            revoked = lic.get("revoked", False)
            status_item = QTableWidgetItem("✅ Active" if not revoked else "❌ Révoquée")
            if revoked:
                revoked_count += 1
            else:
                active_count += 1
            self.licenses_table.setItem(i, 3, status_item)
            
            # Machine (première activation)
            activations = lic.get("activations", [])
            machine = activations[0]["machine"] if activations else "N/A"
            self.licenses_table.setItem(i, 4, QTableWidgetItem(machine[:30]))
            
            self.licenses_table.setItem(i, 5, QTableWidgetItem(str(len(activations))))
        
        self.licenses_table.resizeColumnsToContents()
        
        # Update stats
        self.stats_label.setText(
            f"📊 {len(licenses)} licences | {active_count} actives | {revoked_count} révoquées"
        )
    
    def _revoke_selected(self):
        """Révoque la licence sélectionnée."""
        row = self.licenses_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Sélection", "Sélectionnez une licence")
            return
        
        key_item = self.licenses_table.item(row, 0)
        if key_item:
            key = key_item.text()
            
            reply = QMessageBox.question(
                self, "Révoquer",
                f"Révoquer la licence {key}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.builder.license_db.revoke(key)
                LicenseGenerator.revoke_key(key)
                self._log(f"❌ Révoquée: {key}")
                self._refresh_licenses()
    
    def _copy_key(self):
        """Copie la clé sélectionnée."""
        row = self.licenses_table.currentRow()
        if row >= 0:
            key_item = self.licenses_table.item(row, 0)
            if key_item:
                clipboard = QApplication.clipboard()
                clipboard.setText(key_item.text())
                self._log(f"📋 Copié: {key_item.text()}")
    
    def _export_csv(self):
        """Exporte les licences en CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV",
            f"licenses_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV (*.csv)"
        )
        
        if path:
            licenses = self.builder.license_db.list_all()
            with open(path, "w", encoding="utf-8") as f:
                f.write("key,email,expires,revoked,activations\n")
                for lic in licenses:
                    f.write(f'{lic["key"]},{lic.get("email","")},'
                           f'{lic.get("expires","")},{lic.get("revoked",False)},'
                           f'{len(lic.get("activations",[]))}\n')
            self._log(f"💾 Exporté: {path}")
    
    def _open_server_folder(self):
        """Ouvre le dossier server."""
        import os
        server_path = self.builder.project_root / "server"
        os.startfile(server_path) if os.name == 'nt' else None
    
    def _start_server(self):
        """Démarre le serveur d'activation."""
        self._log("🚀 Lancement serveur...")
        
        import subprocess
        server_path = self.builder.project_root / "server" / "activation_server.py"
        
        if server_path.exists():
            threading.Thread(
                target=lambda: subprocess.Popen(
                    [sys.executable, str(server_path)],
                    cwd=str(server_path.parent)
                ),
                daemon=True
            ).start()
            self._log("✅ Serveur démarré sur http://localhost:5000")
        else:
            self._log("❌ Serveur non trouvé")
    
    def _generate_master_key(self):
        """Génère une nouvelle master key."""
        import secrets
        new_key = secrets.token_hex(32)
        
        builder_path = self.builder.project_root / "builder" / "license_builder.py"
        
        if builder_path.exists():
            content = builder_path.read_text()
            
            # Remplacer la master key
            content = content.replace(
                'MASTER_KEY = "SafeTrendBot_MasterKey_2024_ChangeMe!"',
                f'MASTER_KEY = "{new_key}"'
            )
            
            builder_path.write_text(content)
            self._log(f"🔑 Nouvelle Master Key générée!")
            self._log(f"   ATTENTION: {new_key}")
        else:
            self._log("❌ Fichier non trouvé")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    
    # Style
    app.setStyle('Fusion')
    
    # Palette sombre
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 26, 46))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.ColorRole.Base, QColor(13, 17, 23))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(22, 27, 34))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 217, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(31, 111, 235))
    app.setPalette(palette)
    
    window = BuilderWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()