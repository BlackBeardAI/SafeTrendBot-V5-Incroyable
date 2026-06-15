"""
SafeTrendBot Builder GUI — Interface graphique de génération de builds
======================================================================
Permet de générer facilement des versions protégées du bot.
"""

import sys
import os
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# UI Framework — essayer PyQt5 puis tkinter
try:
    import PyQt6.QtWidgets as QtWidgets
    import PyQt6.QtCore as QtCore
    import PyQt6.QtGui as QtGui
    UI_FRAMEWORK = "PyQt6"
except ImportError:
    try:
        import PyQt5.QtWidgets as QtWidgets
        import PyQt5.QtCore as QtCore
        import PyQt5.QtGui as QtGui
        UI_FRAMEWORK = "PyQt5"
    except ImportError:
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
        UI_FRAMEWORK = "tkinter"

# Ajouter le parent au path pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from builder.license_builder import (
    SafeTrendBotBuilder, BuildConfig, LicenseGenerator, LicenseDatabase, VERSION
)


# ═══════════════════════════════════════════════════════════════════════════════
# PyQt6/PyQt5 GUI
# ═══════════════════════════════════════════════════════════════════════════════

class BuilderGUI:
    """Interface graphique principale du Builder."""
    
    def __init__(self):
        self.builder = SafeTrendBotBuilder()
        self.build_thread: Optional[threading.Thread] = None
        self._setup_ui()
    
    def _setup_ui(self):
        self.window = QtWidgets.QWidget()
        self.window.setWindowTitle(f"SafeTrendBot Builder v{VERSION}")
        self.window.setMinimumSize(700, 600)
        
        # Layout principal
        layout = QtWidgets.QVBoxLayout()
        
        # Header
        header = QtWidgets.QLabel(f"<h1>🔐 SafeTrendBot License Builder</h1>")
        header.setStyleSheet("padding: 10px; background: #1a1a2e; color: white; border-radius: 5px;")
        layout.addWidget(header)
        
        # Tab widget
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._build_tab(), "📦 Générer Build")
        tabs.addTab(self._batch_tab(), "📋 Batch")
        tabs.addTab(self._licenses_tab(), "🔑 Licences")
        tabs.addTab(self._settings_tab(), "⚙️ Settings")
        
        layout.addWidget(tabs)
        
        # Log output
        log_label = QtWidgets.QLabel("📝 Log:")
        layout.addWidget(log_label)
        
        self.log_output = QtWidgets.QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("font-family: monospace; background: #0d1117; color: #58a6ff;")
        layout.addWidget(self.log_output)
        
        self.window.setLayout(layout)
        self.window.show()
    
    def _build_tab(self) -> QtWidgets.QWidget:
        """Onglet génération de build unique."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout()
        
        # Clé de licence
        self.key_input = QtWidgets.QLineEdit()
        self.key_input.setPlaceholderText("STB5-XXXX-XXXX-XXXX (laisser vide pour générer)")
        self.gen_key_btn = QtWidgets.QPushButton("🎲 Générer")
        self.gen_key_btn.clicked.connect(self._generate_key)
        
        key_layout = QtWidgets.QHBoxLayout()
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.gen_key_btn)
        layout.addRow("Licence:", key_layout)
        
        # Email
        self.email_input = QtWidgets.QLineEdit()
        self.email_input.setPlaceholderText("client@exemple.com")
        layout.addRow("Email:", self.email_input)
        
        # Expiration
        self.expiry_check = QtWidgets.QCheckBox("Définir expiration")
        self.expiry_days = QtWidgets.QSpinBox()
        self.expiry_days.setMinimum(1)
        self.expiry_days.setMaximum(365)
        self.expiry_days.setValue(30)
        self.expiry_days.setEnabled(False)
        
        self.expiry_check.toggled.connect(lambda checked: self.expiry_days.setEnabled(checked))
        
        expiry_layout = QtWidgets.QHBoxLayout()
        expiry_layout.addWidget(self.expiry_check)
        expiry_layout.addWidget(self.expiry_days)
        expiry_layout.addWidget(QtWidgets.QLabel("jours"))
        layout.addRow("Expiration:", expiry_layout)
        
        # Plateforme
        self.platform_combo = QtWidgets.QComboBox()
        self.platform_combo.addItems(["windows", "linux", "macos"])
        layout.addRow("Plateforme:", self.platform_combo)
        
        # Options
        self.obfuscate_check = QtWidgets.QCheckBox("Obfuscation (PyArmor)")
        self.obfuscate_check.setChecked(True)
        self.cython_check = QtWidgets.QCheckBox("Compilation Cython")
        self.cython_check.setChecked(True)
        
        opts_layout = QtWidgets.QHBoxLayout()
        opts_layout.addWidget(self.obfuscate_check)
        opts_layout.addWidget(self.cython_check)
        layout.addRow("Options:", opts_layout)
        
        # Bouton build
        self.build_btn = QtWidgets.QPushButton("🚀 GÉNÉRER LE BUILD")
        self.build_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                padding: 12px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #2ea043; }
            QPushButton:disabled { background: #484f58; }
        """)
        self.build_btn.clicked.connect(self._start_build)
        layout.addRow("", self.build_btn)
        
        # Progress
        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        layout.addRow("", self.progress)
        
        tab.setLayout(layout)
        return tab
    
    def _batch_tab(self) -> QtWidgets.QWidget:
        """Onglet génération batch."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout()
        
        # Nombre
        self.batch_count = QtWidgets.QSpinBox()
        self.batch_count.setMinimum(1)
        self.batch_count.setMaximum(100)
        self.batch_count.setValue(10)
        layout.addRow("Nombre de builds:", self.batch_count)
        
        # Email prefix
        self.batch_email_prefix = QtWidgets.QLineEdit()
        self.batch_email_prefix.setText("client")
        layout.addRow("Préfixe email:", self.batch_email_prefix)
        
        # Expiration
        self.batch_expiry = QtWidgets.QSpinBox()
        self.batch_expiry.setMinimum(0)
        self.batch_expiry.setMaximum(365)
        self.batch_expiry.setValue(30)
        expiry_hint = QtWidgets.QLabel("0 = sans expiration")
        expiry_hint.setStyleSheet("color: gray;")
        expiry_row = QtWidgets.QHBoxLayout()
        expiry_row.addWidget(self.batch_expiry)
        expiry_row.addWidget(expiry_hint)
        layout.addRow("Jours expiration:", expiry_row)
        
        # Plateforme
        self.batch_platform = QtWidgets.QComboBox()
        self.batch_platform.addItems(["windows", "linux", "macos"])
        layout.addRow("Plateforme:", self.batch_platform)
        
        # Bouton
        self.batch_btn = QtWidgets.QPushButton("📦 GÉNÉRER BATCH")
        self.batch_btn.setStyleSheet("""
            QPushButton {
                background: #1f6feb;
                color: white;
                padding: 12px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #388bfd; }
        """)
        self.batch_btn.clicked.connect(self._start_batch)
        layout.addRow("", self.batch_btn)
        
        tab.setLayout(layout)
        return tab
    
    def _licenses_tab(self) -> QtWidgets.QWidget:
        """Onglet gestion des licences."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        # Table
        self.licenses_table = QtWidgets.QTableWidget()
        self.licenses_table.setColumnCount(5)
        self.licenses_table.setHorizontalHeaderLabels(["Clé", "Email", "Expires", "Revoked", "Activations"])
        self.licenses_table.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.licenses_table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        layout.addWidget(self.licenses_table)
        
        # Boutons
        btn_layout = QtWidgets.QHBoxLayout()
        
        refresh_btn = QtWidgets.QPushButton("🔄 Rafraîchir")
        refresh_btn.clicked.connect(self._refresh_licenses)
        btn_layout.addWidget(refresh_btn)
        
        revoke_btn = QtWidgets.QPushButton("❌ Révoquer")
        revoke_btn.clicked.connect(self._revoke_selected)
        btn_layout.addWidget(revoke_btn)
        
        export_btn = QtWidgets.QPushButton("💾 Exporter CSV")
        export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
        
        tab.setLayout(layout)
        self._refresh_licenses()
        return tab
    
    def _settings_tab(self) -> QtWidgets.QWidget:
        """Onglet paramètres."""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout()
        
        # Version
        layout.addRow("Version:", QtWidgets.QLabel(VERSION))
        
        # Path
        self.path_input = QtWidgets.QLineEdit()
        self.path_input.setText(str(self.builder.project_root))
        layout.addRow("Project path:", self.path_input)
        
        # Output
        self.output_input = QtWidgets.QLineEdit()
        self.output_input.setText(str(self.builder.project_root / "builds"))
        layout.addRow("Builds output:", self.output_input)
        
        tab.setLayout(layout)
        return tab
    
    def _log(self, msg: str):
        """Ajoute au log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {msg}")
    
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
        self.progress.setRange(0, 0)  # Indeterminate
        
        def run():
            self._log(f"🚀 Démarrage build: {config.output_name}")
            success, msg = self.builder.build(config)
            
            QtCore.QMetaObject.invokeMethod(QtWidgets.QApplication.instance(), 
                lambda: self._build_finished(success, msg))
        
        self.build_thread = threading.Thread(target=run)
        self.build_thread.start()
    
    def _build_finished(self, success: bool, msg: str):
        """Callback fin de build."""
        self.build_btn.setEnabled(True)
        self.progress.setVisible(False)
        
        if success:
            self._log(f"✅ BUILD RÉUSSI: {msg}")
        else:
            self._log(f"❌ ERREUR: {msg}")
    
    def _start_batch(self):
        """Lance un batch."""
        count = self.batch_count.value()
        expiry = self.batch_expiry.value() or None
        
        self.batch_btn.setEnabled(False)
        
        def run():
            results = self.builder.build_batch(
                count=count,
                email_prefix=self.batch_email_prefix.text(),
                expiry_days=expiry,
                platform=self.batch_platform.currentText(),
            )
            
            QtCore.QMetaObject.invokeMethod(QtWidgets.QApplication.instance(),
                lambda: self._batch_finished(results))
        
        self.build_thread = threading.Thread(target=run)
        self.build_thread.start()
    
    def _batch_finished(self, results: list):
        self.batch_btn.setEnabled(True)
        success_count = sum(1 for r in results if r["success"])
        self._log(f"✅ Batch terminé: {success_count}/{len(results)} réussie(s)")
        self._refresh_licenses()
    
    def _refresh_licenses(self):
        """Rafraîchit la table des licences."""
        licenses = self.builder.license_db.list_all()
        self.licenses_table.setRowCount(len(licenses))
        
        for i, lic in enumerate(licenses):
            self.licenses_table.setItem(i, 0, QtWidgets.QTableWidgetItem(lic["key"]))
            self.licenses_table.setItem(i, 1, QtWidgets.QTableWidgetItem(lic.get("email", "")))
            self.licenses_table.setItem(i, 2, QtWidgets.QTableWidgetItem(lic.get("expires", "Jamais")))
            self.licenses_table.setItem(i, 3, QtWidgets.QTableWidgetItem("✅" if not lic.get("revoked") else "❌"))
            self.licenses_table.setItem(i, 4, QtWidgets.QTableWidgetItem(str(len(lic.get("activations", [])))))
        
        self.licenses_table.resizeColumnsToContents()
    
    def _revoke_selected(self):
        """Révoque la licence sélectionnée."""
        row = self.licenses_table.currentRow()
        if row >= 0:
            key = self.licenses_table.item(row, 0).text()
            self.builder.license_db.revoke(key)
            LicenseGenerator.revoke_key(key)
            self._log(f"❌ Révoquée: {key}")
            self._refresh_licenses()
    
    def _export_csv(self):
        """Exporte les licences en CSV."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.window, "Exporter CSV",
            f"licenses_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV (*.csv)"
        )
        if path:
            licenses = self.builder.license_db.list_all()
            with open(path, "w") as f:
                f.write("key,email,expires,revoked,activations\n")
                for lic in licenses:
                    f.write(f'{lic["key"]},{lic.get("email","")},{lic.get("expires","")},{lic.get("revoked",False)},{len(lic.get("activations",[]))}\n')
            self._log(f"💾 Exporté: {path}")
    
    def run(self):
        """Lance l'application."""
        self._log(f"🔐 SafeTrendBot Builder v{VERSION} initialisé")
        return self.window


# ═══════════════════════════════════════════════════════════════════════════════
# tkinter fallback
# ═══════════════════════════════════════════════════════════════════════════════

class BuilderGUI_tk:
    """Version tkinter (fallback si PyQt pas disponible)."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"SafeTrendBot Builder v{VERSION}")
        self.root.geometry("600x500")
        self.builder = SafeTrendBotBuilder()
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Notebook (tabs)
        nb = ttk.Notebook(self.root)
        nb.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab Build
        build_frame = ttk.Frame(nb)
        nb.add(build_frame, text="📦 Générer Build")
        self._setup_build_tab(build_frame)
        
        # Tab Licences
        lic_frame = ttk.Frame(nb)
        nb.add(lic_frame, text="🔑 Licences")
        self._setup_licenses_tab(lic_frame)
        
        # Log
        ttk.Label(self.root, text="Log:").pack(anchor='w', padx=10)
        self.log_text = tk.Text(self.root, height=8, bg='black', fg='green')
        self.log_text.pack(fill='x', padx=10, pady=5)
    
    def _setup_build_tab(self, parent):
        ttk.Label(parent, text="Clé de licence:").pack(anchor='w', padx=10, pady=5)
        
        key_frame = ttk.Frame(parent)
        key_frame.pack(fill='x', padx=10)
        
        self.key_entry = ttk.Entry(key_frame, width=40)
        self.key_entry.pack(side='left')
        
        ttk.Button(key_frame, text="🎲 Générer", 
                   command=self._generate_key).pack(side='left', padx=5)
        
        ttk.Label(parent, text="Email:").pack(anchor='w', padx=10, pady=5)
        self.email_entry = ttk.Entry(parent, width=40)
        self.email_entry.pack(fill='x', padx=10)
        
        # Platform
        ttk.Label(parent, text="Plateforme:").pack(anchor='w', padx=10, pady=5)
        self.platform_var = tk.StringVar(value="windows")
        ttk.Radiobutton(parent, text="Windows", variable=self.platform_var, 
                       value="windows").pack(anchor='w', padx=30)
        ttk.Radiobutton(parent, text="Linux", variable=self.platform_var,
                       value="linux").pack(anchor='w', padx=30)
        
        # Build button
        self.build_btn = ttk.Button(parent, text="🚀 GÉNÉRER LE BUILD",
                                    command=self._start_build)
        self.build_btn.pack(pady=20)
    
    def _setup_licenses_tab(self, parent):
        self.licenses_listbox = tk.Listbox(parent, width=60)
        self.licenses_listbox.pack(fill='both', expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack()
        
        ttk.Button(btn_frame, text="🔄 Rafraîchir",
                   command=self._refresh_licenses).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="❌ Révoquer",
                   command=self._revoke_selected).pack(side='left', padx=5)
    
    def _log(self, msg: str):
        self.log_text.insert('end', f"[{datetime.now():%H:%M:%S}] {msg}\n")
        self.log_text.see('end')
    
    def _generate_key(self):
        key = LicenseGenerator.generate_key()
        self.key_entry.delete(0, 'end')
        self.key_entry.insert(0, key)
        self._log(f"✅ Clé générée: {key}")
    
    def _start_build(self):
        key = self.key_entry.get().strip() or LicenseGenerator.generate_key()
        email = self.email_entry.get().strip()
        
        config = BuildConfig(
            license_key=key,
            email=email,
            platform=self.platform_var.get(),
        )
        
        self.build_btn.config(state='disabled')
        self._log(f"🚀 Build: {config.output_name}")
        
        def run():
            success, msg = self.builder.build(config)
            self.root.after(0, lambda: self._build_finished(success, msg))
        
        threading.Thread(target=run).start()
    
    def _build_finished(self, success, msg):
        self.build_btn.config(state='normal')
        if success:
            self._log(f"✅ {msg}")
        else:
            self._log(f"❌ {msg}")
    
    def _refresh_licenses(self):
        self.licenses_listbox.delete(0, 'end')
        for lic in self.builder.license_db.list_all():
            status = "✅" if not lic.get("revoked") else "❌"
            self.licenses_listbox.insert('end', 
                f"{status} {lic['key']} | {lic.get('email', '')}")
    
    def _revoke_selected(self):
        selection = self.licenses_listbox.curselection()
        if selection:
            item = self.licenses_listbox.get(selection[0])
            key = item.split()[1]
            self.builder.license_db.revoke(key)
            self._log(f"❌ Révoquée: {key}")
            self._refresh_licenses()
    
    def run(self):
        self._log(f"🔐 SafeTrendBot Builder v{VERSION}")
        self._refresh_licenses()
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if UI_FRAMEWORK in ("PyQt6", "PyQt5"):
        app = QtWidgets.QApplication(sys.argv)
        
        # Style
        app.setStyle('Fusion')
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(30, 30, 30))
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white)
        app.setPalette(palette)
        
        gui = BuilderGUI()
        gui.run()
        sys.exit(app.exec())
    else:
        gui = BuilderGUI_tk()
        gui.run()


if __name__ == "__main__":
    main()