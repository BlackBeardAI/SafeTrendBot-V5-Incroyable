"""
SafeTrendBot V5 — Client Manager
================================
Gestionnaire de base de données clients.

Fonctionnalités:
- Enregistrement de chaque vente
- Suivi des licences
- Historique complet
- Export et reporting
- Recherche par nom/email/clé
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent
CLIENTS_DB = BASE_DIR / "clients.db"


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def get_db():
    """Connexion à la base de données."""
    conn = sqlite3.connect(str(CLIENTS_DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise le schéma de la base de données."""
    conn = get_db()
    conn.executescript('''
        -- Table principale des clients
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Infos client
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            country TEXT,
            notes TEXT,
            
            -- Infos vente
            sale_date TEXT NOT NULL,
            sale_price_usd REAL,
            sale_price_eur REAL,
            currency TEXT DEFAULT 'USD',
            payment_method TEXT,
            payment_tx TEXT,  -- Hash transaction crypto
            
            -- Licence
            license_key TEXT UNIQUE NOT NULL,
            license_issued_at TEXT,
            license_expires_at TEXT,
            
            -- Build
            build_file TEXT,
            build_version TEXT,
            build_platform TEXT DEFAULT 'windows',
            
            -- Hardware (pour tracking)
            hw_id TEXT,
            hw_token TEXT,
            first_activation TEXT,
            activation_count INTEGER DEFAULT 0,
            
            -- Statut
            status TEXT DEFAULT 'active',  -- active, suspended, revoked
            revoked_at TEXT,
            revoke_reason TEXT,
            
            -- Métadonnées
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Table des activations (historique)
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            hw_id TEXT,
            hw_token TEXT,
            os_info TEXT,
            activation_date TEXT DEFAULT (datetime('now')),
            ip_address TEXT,
            success INTEGER DEFAULT 1,
            error_message TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        
        -- Table des licences vendues (backup)
        CREATE TABLE IF NOT EXISTS licenses_sold (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            sale_date TEXT,
            price_usd REAL,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        
        -- Table des rappels
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            reminder_date TEXT,
            reminder_type TEXT,  -- followup, renewal, support
            message TEXT,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        
        -- Index
        CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
        CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);
        CREATE INDEX IF NOT EXISTS idx_clients_license ON clients(license_key);
        CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
    ''')
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# CLIENT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Client:
    """Représente un client."""
    id: Optional[int] = None
    name: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""
    notes: str = ""
    
    sale_date: str = ""
    sale_price_usd: float = 0.0
    sale_price_eur: float = 0.0
    currency: str = "USD"
    payment_method: str = ""
    payment_tx: str = ""
    
    license_key: str = ""
    license_issued_at: str = ""
    license_expires_at: Optional[str] = None
    
    build_file: str = ""
    build_version: str = "5.3.0"
    build_platform: str = "windows"
    
    hw_id: str = ""
    hw_token: str = ""
    first_activation: Optional[str] = None
    activation_count: int = 0
    
    status: str = "active"
    revoked_at: Optional[str] = None
    revoke_reason: str = ""
    
    created_at: str = ""
    updated_at: str = ""


class ClientManager:
    """
    Gestionnaire de la base de données clients.
    
    Usage:
        cm = ClientManager()
        
        # Ajouter un client
        client_id = cm.add_client(
            name="Jean Dupont",
            email="jean@email.com",
            license_key="STB5-XXXX-XXXX-XXXX",
            sale_price_usd=297
        )
        
        # Rechercher
        results = cm.search("Dupont")
        
        # Voir détails
        client = cm.get_client(client_id)
        
        # Lister tous
        all_clients = cm.get_all_clients()
    """
    
    def __init__(self):
        init_db()
    
    def add_client(self, 
                   name: str,
                   email: str = "",
                   phone: str = "",
                   license_key: str = "",
                   sale_price_usd: float = 0.0,
                   sale_price_eur: float = 0.0,
                   currency: str = "USD",
                   payment_method: str = "crypto",
                   payment_tx: str = "",
                   sale_date: str = None,
                   build_file: str = "",
                   build_version: str = "5.3.0",
                   notes: str = "",
                   country: str = "") -> int:
        """
        Ajoute un nouveau client à la base.
        
        Returns: client_id (int)
        """
        if sale_date is None:
            sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO clients (
                name, email, phone, country, notes,
                sale_date, sale_price_usd, sale_price_eur, currency,
                payment_method, payment_tx,
                license_key, license_issued_at,
                build_file, build_version, build_platform,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, email, phone, country, notes,
            sale_date, sale_price_usd, sale_price_eur, currency,
            payment_method, payment_tx,
            license_key, datetime.now().isoformat(),
            build_file, build_version, "windows",
            "active"
        ))
        
        client_id = cursor.lastrowid
        
        # Aussi ajouter dans licenses_sold
        cursor.execute('''
            INSERT INTO licenses_sold (license_key, client_id, sale_date, price_usd, status)
            VALUES (?, ?, ?, ?, 'active')
        ''', (license_key, client_id, sale_date, sale_price_usd))
        
        conn.commit()
        conn.close()
        
        return client_id
    
    def get_client(self, client_id: int) -> Optional[Dict]:
        """Récupère les infos d'un client par ID."""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_client_by_license(self, license_key: str) -> Optional[Dict]:
        """Récupère un client par clé de licence."""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM clients WHERE license_key = ?", (license_key,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_client_by_email(self, email: str) -> Optional[Dict]:
        """Récupère un client par email."""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM clients WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    
    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Recherche un client par nom, email ou clé de licence.
        
        Args:
            query: Texte à rechercher
            limit: Nombre max de résultats
            
        Returns: Liste de clients
        """
        conn = get_db()
        search_term = f"%{query}%"
        rows = conn.execute('''
            SELECT * FROM clients 
            WHERE name LIKE ? OR email LIKE ? OR license_key LIKE ? OR phone LIKE ?
            ORDER BY sale_date DESC
            LIMIT ?
        ''', (search_term, search_term, search_term, search_term, limit)).fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_clients(self, status: str = None, limit: int = 100) -> List[Dict]:
        """
        Liste tous les clients.
        
        Args:
            status: Filtrer par statut (active/suspended/revoked)
            limit: Nombre max de résultats
        """
        conn = get_db()
        
        if status:
            rows = conn.execute('''
                SELECT * FROM clients 
                WHERE status = ?
                ORDER BY sale_date DESC
                LIMIT ?
            ''', (status, limit)).fetchall()
        else:
            rows = conn.execute('''
                SELECT * FROM clients 
                ORDER BY sale_date DESC
                LIMIT ?
            ''', (limit,)).fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    
    def update_client(self, client_id: int, **kwargs) -> bool:
        """
        Met à jour les infos d'un client.
        
        Args:
            client_id: ID du client
            **kwargs: Champs à mettre à jour
        """
        if not kwargs:
            return False
        
        # Construire la requête UPDATE
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [client_id]
        
        conn = get_db()
        conn.execute(
            f"UPDATE clients SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values
        )
        conn.commit()
        affected = conn.total_changes
        conn.close()
        
        return affected > 0
    
    def record_activation(self, client_id: int, hw_id: str = "", hw_token: str = "",
                         os_info: str = "", ip_address: str = "") -> bool:
        """Enregistre une activation (premier lancement par le client)."""
        conn = get_db()
        
        # Mettre à jour le client
        conn.execute('''
            UPDATE clients 
            SET first_activation = COALESCE(first_activation, datetime('now')),
                activation_count = activation_count + 1,
                hw_id = COALESCE(hw_id, ?),
                hw_token = COALESCE(hw_token, ?),
                updated_at = datetime('now')
            WHERE id = ?
        ''', (hw_id, hw_token, client_id))
        
        # Ajouter dans l'historique des activations
        conn.execute('''
            INSERT INTO activations (client_id, hw_id, hw_token, os_info, ip_address)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_id, hw_id, hw_token, os_info, ip_address))
        
        conn.commit()
        conn.close()
        return True
    
    def revoke_license(self, client_id: int, reason: str = "") -> bool:
        """
        Révoque la licence d'un client.
        
        Args:
            client_id: ID du client
            reason: Raison de la révocation
        """
        conn = get_db()
        
        conn.execute('''
            UPDATE clients 
            SET status = 'revoked', 
                revoked_at = datetime('now'),
                revoke_reason = ?,
                updated_at = datetime('now')
            WHERE id = ?
        ''', (reason, client_id))
        
        # Mettre à jour licenses_sold
        client = self.get_client(client_id)
        if client:
            conn.execute('''
                UPDATE licenses_sold 
                SET status = 'revoked' 
                WHERE license_key = ?
            ''', (client['license_key'],))
        
        conn.commit()
        conn.close()
        return True
    
    def delete_client(self, client_id: int, soft: bool = True) -> bool:
        """
        Supprime un client.
        
        Args:
            client_id: ID du client
            soft: Si True, marque comme 'deleted'; si False, supprime réellement
        """
        if soft:
            return self.update_client(client_id, status="deleted")
        else:
            conn = get_db()
            conn.execute("DELETE FROM activations WHERE client_id = ?", (client_id,))
            conn.execute("DELETE FROM reminders WHERE client_id = ?", (client_id,))
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()
            conn.close()
            return True
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques globales."""
        conn = get_db()
        
        total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        active_clients = conn.execute(
            "SELECT COUNT(*) FROM clients WHERE status = 'active'"
        ).fetchone()[0]
        revoked_clients = conn.execute(
            "SELECT COUNT(*) FROM clients WHERE status = 'revoked'"
        ).fetchone()[0]
        
        total_revenue_usd = conn.execute(
            "SELECT SUM(sale_price_usd) FROM clients WHERE status != 'deleted'"
        ).fetchone()[0] or 0
        
        total_revenue_eur = conn.execute(
            "SELECT SUM(sale_price_eur) FROM clients WHERE status != 'deleted'"
        ).fetchone()[0] or 0
        
        recent_sales = conn.execute('''
            SELECT COUNT(*) FROM clients 
            WHERE sale_date > datetime('now', '-30 days')
        ''').fetchone()[0]
        
        conn.close()
        
        return {
            "total_clients": total_clients,
            "active_clients": active_clients,
            "revoked_clients": revoked_clients,
            "total_revenue_usd": round(total_revenue_usd, 2),
            "total_revenue_eur": round(total_revenue_eur, 2),
            "recent_sales_30d": recent_sales,
            "avg_sale_usd": round(total_revenue_usd / total_clients, 2) if total_clients > 0 else 0
        }
    
    def get_recent_clients(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """Retourne les ventes récentes."""
        conn = get_db()
        rows = conn.execute('''
            SELECT * FROM clients 
            WHERE sale_date > datetime('now', ?)
            ORDER BY sale_date DESC
            LIMIT ?
        ''', (f'-{days} days', limit)).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def export_csv(self, filepath: str = None) -> str:
        """Exporte tous les clients en CSV."""
        import csv
        
        if filepath is None:
            filepath = f"clients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        clients = self.get_all_clients(limit=10000)
        
        if not clients:
            return ""
        
        # Déterminer les colonnes
        columns = [
            "id", "name", "email", "phone", "country",
            "sale_date", "sale_price_usd", "sale_price_eur", "currency",
            "payment_method", "payment_tx",
            "license_key", "license_issued_at",
            "build_version", "build_platform",
            "hw_id", "first_activation", "activation_count",
            "status", "created_at"
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(clients)
        
        return filepath
    
    def add_reminder(self, client_id: int, reminder_type: str, 
                     message: str, reminder_date: str = None) -> int:
        """Ajoute un rappel pour un client."""
        if reminder_date is None:
            reminder_date = datetime.now().strftime("%Y-%m-%d")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reminders (client_id, reminder_type, message, reminder_date)
            VALUES (?, ?, ?, ?)
        ''', (client_id, reminder_type, message, reminder_date))
        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reminder_id
    
    def get_reminders(self, client_id: int = None, pending: bool = True) -> List[Dict]:
        """Récupère les rappels."""
        conn = get_db()
        
        if client_id:
            query = "SELECT * FROM reminders WHERE client_id = ?"
            params = [client_id]
        else:
            query = "SELECT * FROM reminders"
            params = []
        
        if pending:
            query += " AND completed = 0 AND reminder_date <= date('now')"
        
        query += " ORDER BY reminder_date ASC"
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════════════════════════════════
# GUI CLIENT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

def launch_gui():
    """Lance l'interface graphique du gestionnaire de clients."""
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    
    # Initialiser la DB
    init_db()
    cm = ClientManager()
    
    # Fenêtre principale
    root = tk.Tk()
    root.title("SafeTrendBot V5 — Gestion des Clients")
    root.geometry("1200x700")
    root.configure(bg='#1a1a2e')
    
    # Variables
    search_var = tk.StringVar()
    selected_client_id = None
    
    # ─── Header ───
    header = tk.Frame(root, bg='#16213e', pady=10)
    header.pack(fill='x')
    
    tk.Label(header, text="👥 Gestion des Clients", font=('Arial', 18, 'bold'),
            fg='#00d9ff', bg='#16213e').pack(side='left', padx=20)
    
    # Stats
    stats_frame = tk.Frame(header, bg='#16213e')
    stats_frame.pack(side='right', padx=20)
    
    def refresh_stats():
        stats = cm.get_stats()
        stats_label.config(
            text=f"Total: {stats['total_clients']} | "
                 f"Actifs: {stats['active_clients']} | "
                 f"Revenus: ${stats['total_revenue_usd']:.2f}"
        )
    
    stats_label = tk.Label(stats_frame, text="", fg='#888', bg='#16213e')
    stats_label.pack()
    
    # ─── Search Bar ───
    search_frame = tk.Frame(root, bg='#1a1a2e', pady=10)
    search_frame.pack(fill='x', padx=20)
    
    tk.Entry(search_frame, textvariable=search_var, width=40,
            bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff',
            font=('Arial', 11)).pack(side='left', padx=5)
    
    def do_search():
        query = search_var.get()
        if query:
            results = cm.search(query)
            update_client_list(results)
        else:
            update_client_list(cm.get_all_clients())
    
    tk.Button(search_frame, text="🔍 Rechercher", command=do_search,
             bg='#0f3460', fg='#fff').pack(side='left', padx=5)
    
    tk.Button(search_frame, text="↻", command=lambda: (search_var.set(""), update_client_list(cm.get_all_clients())),
             bg='#333', fg='#fff', width=3).pack(side='left')
    
    # ─── Main Content ───
    content = tk.Frame(root, bg='#1a1a2e')
    content.pack(fill='both', expand=True, padx=20, pady=10)
    
    # Liste des clients (gauche)
    list_frame = tk.Frame(content, bg='#0d1117')
    list_frame.pack(side='left', fill='both', expand=True)
    
    # Treeview
    columns = ("name", "email", "license", "sale_date", "price", "status")
    tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)
    
    tree.heading("name", text="Nom")
    tree.heading("email", text="Email")
    tree.heading("license", text="Licence")
    tree.heading("sale_date", text="Date vente")
    tree.heading("price", text="Prix (USD)")
    tree.heading("status", text="Statut")
    
    tree.column("name", width=150)
    tree.column("email", width=180)
    tree.column("license", width=150)
    tree.column("sale_date", width=120)
    tree.column("price", width=80)
    tree.column("status", width=80)
    
    scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    tree.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')
    
    def update_client_list(clients: List[Dict]):
        tree.delete(*tree.get_children())
        for c in clients:
            status_color = {'active': '#2ecc71', 'revoked': '#e74c3c', 'suspended': '#f39c12'}
            status_text = {'active': '✅ Actif', 'revoked': '❌ Révoqué', 'suspended': '⏸️ Suspendu'}
            
            tree.insert('', 'end', values=(
                c.get('name', ''),
                c.get('email', ''),
                c.get('license_key', ''),
                c.get('sale_date', '')[:10] if c.get('sale_date') else '',
                f"${c.get('sale_price_usd', 0):.2f}",
                status_text.get(c.get('status', 'active'), c.get('status', ''))
            ), tags=(c.get('status', 'active'),))
    
    def on_client_select(event):
        nonlocal selected_client_id
        selection = tree.selection()
        if selection:
            item = tree.item(selection[0])
            values = item['values']
            # Rechercher le client par licence
            license_key = values[2]
            client = cm.get_client_by_license(license_key)
            if client:
                selected_client_id = client['id']
                show_client_details(client)
    
    tree.bind('<<TreeviewSelect>>', on_client_select)
    
    # ─── Client Details (droite) ───
    details_frame = tk.LabelFrame(content, text="Détails Client", font=('Arial', 12, 'bold'),
                                   fg='#00d9ff', bg='#1a1a2e', padx=15, pady=10)
    details_frame.pack(side='right', fill='both', padx=(10, 0))
    
    details_text = tk.Text(details_frame, width=45, height=25, bg='#0d1117',
                           fg='#e0e0e0', font=('Consolas', 9), wrap='word')
    details_text.pack(fill='both', expand=True)
    
    def show_client_details(client: Dict):
        details_text.delete('1.0', 'end')
        if not client:
            details_text.insert('end', "Sélectionnez un client")
            return
        
        details = f"""╔══════════════════════════════════════╗
║           INFORMATIONS CLIENT           ║
╚══════════════════════════════════════╝

ID: {client.get('id')}
Nom: {client.get('name')}
Email: {client.get('email', 'N/A')}
Téléphone: {client.get('phone', 'N/A')}
Pays: {client.get('country', 'N/A')}

═══════════════════════════════════════
                  VENTE
═══════════════════════════════════════

Date: {client.get('sale_date', 'N/A')}
Prix USD: ${client.get('sale_price_usd', 0):.2f}
Prix EUR: €{client.get('sale_price_eur', 0):.2f}
Méthode: {client.get('payment_method', 'N/A')}
Tx: {client.get('payment_tx', 'N/A')[:20]}...

═══════════════════════════════════════
                  LICENCE
═══════════════════════════════════════

Clé: {client.get('license_key')}
Émise: {client.get('license_issued_at', 'N/A')[:19]}
Expire: {client.get('license_expires_at', 'Jamais')}

═══════════════════════════════════════
                ACTIVATION
═══════════════════════════════════════

HW-ID: {client.get('hw_id', 'N/A')[:20]}...
Première: {client.get('first_activation', 'Jamais')[:19]}
Count: {client.get('activation_count', 0)}

═══════════════════════════════════════
                 STATUS
═══════════════════════════════════════

Statut: {client.get('status', 'active').upper()}
Révoqué: {client.get('revoked_at', 'N/A')[:19] if client.get('revoked_at') else 'Non'}
Raison: {client.get('revoke_reason', 'N/A')}
"""
        details_text.insert('end', details)
    
    # ─── Bottom Actions ───
    actions = tk.Frame(root, bg='#16213e', pady=10)
    actions.pack(fill='x')
    
    def add_new_client():
        """Ouvre le formulaire d'ajout."""
        add_win = tk.Toplevel(root)
        add_win.title("Ajouter un Client")
        add_win.geometry("500x600")
        add_win.configure(bg='#1a1a2e')
        
        # Champs
        fields = {}
        
        row = 0
        for label, key, default in [
            ("Nom complet *", "name", ""),
            ("Email", "email", ""),
            ("Téléphone", "phone", ""),
            ("Pays", "country", ""),
            ("Clé de licence *", "license_key", "STB5-"),
            ("Prix USD", "sale_price_usd", "297"),
            ("Transaction Tx", "payment_tx", ""),
            ("Fichier Build", "build_file", ""),
            ("Notes", "notes", ""),
        ]:
            tk.Label(add_win, text=label, fg='#888', bg='#1a1a2e').grid(row=row, column=0, sticky='w', pady=5, padx=10)
            e = tk.Entry(add_win, width=40, bg='#0d1117', fg='#00d9ff', insertbackground='#00d9ff')
            e.insert(0, default)
            e.grid(row=row, column=1, pady=5, padx=10)
            fields[key] = e
            row += 1
        
        def save_client():
            try:
                client_id = cm.add_client(
                    name=fields['name'].get(),
                    email=fields['email'].get(),
                    phone=fields['phone'].get(),
                    country=fields['country'].get(),
                    license_key=fields['license_key'].get(),
                    sale_price_usd=float(fields['sale_price_usd'].get() or 0),
                    payment_tx=fields['payment_tx'].get(),
                    build_file=fields['build_file'].get(),
                    notes=fields['notes'].get(),
                )
                
                messagebox.showinfo("✅ Succès", f"Client ajouté (ID: {client_id})")
                add_win.destroy()
                update_client_list(cm.get_all_clients())
                refresh_stats()
                
            except Exception as ex:
                messagebox.showerror("❌ Erreur", str(ex))
        
        tk.Button(add_win, text="💾 Ajouter le Client", command=save_client,
                 bg='#27ae60', fg='#fff', font=('Arial', 12, 'bold'),
                 padx=20, pady=10).grid(row=row, column=0, columnspan=2, pady=20)
    
    def revoke_selected():
        if not selected_client_id:
            messagebox.showwarning("⚠️", "Sélectionnez un client")
            return
        
        if messagebox.askyesno("Confirmer", "Révoquer cette licence?"):
            cm.revoke_license(selected_client_id, "Révocation manuelle")
            update_client_list(cm.get_all_clients())
            refresh_stats()
            messagebox.showinfo("✅", "Licence révoquée")
    
    def export_all():
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"clients_export_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if filepath:
            cm.export_csv(filepath)
            messagebox.showinfo("✅", f"Exporté: {filepath}")
    
    tk.Button(actions, text="➕ Nouveau Client", command=add_new_client,
             bg='#27ae60', fg='#fff', padx=15, pady=8).pack(side='left', padx=5)
    
    tk.Button(actions, text="❌ Révoquer", command=revoke_selected,
             bg='#e74c3c', fg='#fff', padx=15, pady=8).pack(side='left', padx=5)
    
    tk.Button(actions, text="📊 Statistiques", 
             command=lambda: messagebox.showinfo("📊", str(cm.get_stats())),
             bg='#0f3460', fg='#fff', padx=15, pady=8).pack(side='left', padx=5)
    
    tk.Button(actions, text="📤 Export CSV", command=export_all,
             bg='#0f3460', fg='#fff', padx=15, pady=8).pack(side='left', padx=5)
    
    # Initial load
    update_client_list(cm.get_all_clients())
    refresh_stats()
    
    root.mainloop()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Client Manager")
    parser.add_argument("--gui", action="store_true", help="Lancer l'interface graphique")
    args = parser.parse_args()
    
    if args.gui:
        launch_gui()
    else:
        # Mode CLI simple
        cm = ClientManager()
        stats = cm.get_stats()
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║        SafeTrendBot V5 — Client Manager                   ║
╠══════════════════════════════════════════════════════════════╣
║  Commandes disponibles:                                     ║
║    python client_manager.py --gui    → Interface graphique ║
║    python client_manager.py --list   → Liste des clients   ║
║    python client_manager.py --stats  → Statistiques        ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        print("\n📊 STATISTIQUES:")
        print(f"   Total clients: {stats['total_clients']}")
        print(f"   Clients actifs: {stats['active_clients']}")
        print(f"   Clients révoqués: {stats['revoked_clients']}")
        print(f"   Revenus totaux: ${stats['total_revenue_usd']:.2f}")
        print(f"   Ventes (30j): {stats['recent_sales_30d']}")