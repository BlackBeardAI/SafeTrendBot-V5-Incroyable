"""
Activation Server — Backend Python pour le système de licence.
À héberger sur un VPS (PythonAnywhere, Heroku, VPS perso).
API: /api/activate, /api/heartbeat, /api/revoke
"""
from flask import Flask, request, jsonify
from functools import wraps
import hashlib
import hmac
import json
import base64
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Set
import sqlite3
import os

app = Flask(__name__)

# CONFIG — À MODIFIER
ADMIN_TOKEN = os.environ.get("SAFETRENDBOT_ADMIN_TOKEN", "change_me_in_production_12345")
SECRET_KEY = os.environ.get("SAFETRENDBOT_SECRET", "super_secret_key_change_me")
DATABASE = os.environ.get("SAFETRENDBOT_DB", "licenses.db")


@dataclass
class LicenseRecord:
    key: str
    email: str
    type: str
    hw_id: Optional[str]
    activated_at: Optional[str]
    expires: Optional[str]
    revoked: bool
    activations: int
    last_heartbeat: Optional[str]


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                type TEXT NOT NULL,
                hw_id TEXT,
                activated_at TEXT,
                expires TEXT,
                revoked INTEGER DEFAULT 0,
                activations INTEGER DEFAULT 0,
                last_heartbeat TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT,
                hw_id TEXT,
                machine TEXT,
                os TEXT,
                activated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (license_key) REFERENCES licenses(key)
            )
        ''')


def sign_license(payload: dict) -> str:
    """Signe un payload avec HMAC"""
    payload_json = json.dumps(payload, sort_keys=True)
    sig = hmac.new(SECRET_KEY.encode(), payload_json.encode(), hashlib.sha256).hexdigest()[:32]
    data = {"payload": payload, "sig": sig}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(token, ADMIN_TOKEN):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# API PUBLIQUE (appelée par les clients)
# ============================================================================

@app.route("/api/activate", methods=["POST"])
def activate():
    """Active une licence sur une nouvelle machine"""
    data = request.get_json() or {}
    license_key = data.get("license_key", "").strip()
    hw_id = data.get("hw_id", "").strip()
    machine = data.get("machine", "unknown")
    os_name = data.get("os", "unknown")

    if not license_key or not hw_id:
        return jsonify({"success": False, "message": "Clé ou HW ID manquant"}), 400

    with get_db() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE key = ?", (license_key,)).fetchone()

        if not row:
            return jsonify({"success": False, "message": "Clé invalide"}), 404

        lic = dict(row)

        if lic["revoked"]:
            return jsonify({"success": False, "message": "Licence révoquée"}), 403

        if lic["hw_id"] and lic["hw_id"] != hw_id:
            # Déjà activée sur une autre machine
            if lic["activations"] >= 3:
                return jsonify({"success": False, "message": "Trop d'activations. Contactez le support."}), 403
            # Autoriser le transfert (mais loguer)
            conn.execute("INSERT INTO activations (license_key, hw_id, machine, os) VALUES (?, ?, ?, ?)",
                        (license_key, hw_id, machine, os_name))
            conn.execute("UPDATE licenses SET hw_id = ?, activations = activations + 1, activated_at = ? WHERE key = ?",
                        (hw_id, datetime.utcnow().isoformat(), license_key))
        else:
            # Première activation ou même machine
            if not lic["hw_id"]:
                conn.execute("UPDATE licenses SET hw_id = ?, activations = 1, activated_at = ? WHERE key = ?",
                            (hw_id, datetime.utcnow().isoformat(), license_key))
            conn.execute("INSERT INTO activations (license_key, hw_id, machine, os) VALUES (?, ?, ?, ?)",
                        (license_key, hw_id, machine, os_name))

        # Générer la licence signée
        payload = {
            "email": lic["email"],
            "type": lic["type"],
            "hw_id": hw_id,
            "issued": datetime.utcnow().isoformat(),
            "expires": lic["expires"],
            "version": "5.0",
        }
        signed = sign_license(payload)

        return jsonify({
            "success": True,
            "message": "Activation réussie",
            "signed_license": signed,
        })


@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    """Ping régulier du client"""
    data = request.get_json() or {}
    license_hash = data.get("license_hash", "")

    with get_db() as conn:
        conn.execute(
            "UPDATE licenses SET last_heartbeat = ? WHERE key LIKE ?",
            (datetime.utcnow().isoformat(), f"%{license_hash}%")
        )
    return jsonify({"ok": True})


# ============================================================================
# API ADMIN (génération, révocation, stats)
# ============================================================================

@app.route("/admin/generate", methods=["POST"])
@require_admin
def generate_license():
    """Génère une nouvelle clé de licence"""
    data = request.get_json() or {}
    email = data.get("email", "")
    license_type = data.get("type", "lifetime")
    expires_days = data.get("expires_days")

    if not email:
        return jsonify({"error": "Email requis"}), 400

    key = "STB-" + hashlib.sha256(f"{email}{datetime.utcnow().isoformat()}{SECRET_KEY}".encode()).hexdigest()[:16].upper()

    expires = None
    if expires_days:
        expires = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO licenses (key, email, type, expires) VALUES (?, ?, ?, ?)",
            (key, email, license_type, expires)
        )

    return jsonify({
        "key": key,
        "email": email,
        "type": license_type,
        "expires": expires,
    })


@app.route("/admin/revoke", methods=["POST"])
@require_admin
def revoke_license():
    """Révoque une licence"""
    data = request.get_json() or {}
    key = data.get("key", "")

    with get_db() as conn:
        conn.execute("UPDATE licenses SET revoked = 1 WHERE key = ?", (key,))
        updated = conn.total_changes

    return jsonify({"revoked": updated > 0, "key": key})


@app.route("/admin/stats", methods=["GET"])
@require_admin
def stats():
    """Statistiques des licences"""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM licenses WHERE revoked = 0 AND hw_id IS NOT NULL").fetchone()[0]
        revoked = conn.execute("SELECT COUNT(*) FROM licenses WHERE revoked = 1").fetchone()[0]
        trials = conn.execute("SELECT COUNT(*) FROM licenses WHERE type = 'trial'").fetchone()[0]

    return jsonify({
        "total": total,
        "active": active,
        "revoked": revoked,
        "trials": trials,
    })


@app.route("/admin/list", methods=["GET"])
@require_admin
def list_licenses():
    """Liste toutes les licences"""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
        licenses = [dict(r) for r in rows]
    return jsonify({"licenses": licenses})


# ============================================================================
# LANCEMENT
# ============================================================================

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
