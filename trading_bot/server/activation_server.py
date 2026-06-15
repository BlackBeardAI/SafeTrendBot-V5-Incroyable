"""
SafeTrendBot Activation Server — Serveur d'activation en ligne
===============================================================
Héberger sur VPS/Cloud pour gérer les licences à distance.

Endpoints:
- POST /api/activate     → Active une licence
- POST /api/heartbeat   → Ping pour maintenir la connexion
- POST /api/revoke      → Révoque une licence
- GET  /api/status      → Statut d'une licence
- GET  /api/stats       → Statistiques admin

⚠️安保: Protéger cet endpoint avec un token admin!
"""

import os
import sys
import json
import hmac
import hashlib
import sqlite3
import secrets
import logging
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Tuple

from flask import Flask, request, jsonify, g

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

APP = Flask(__name__)

# Clés secrètes (remplacer en prod!)
SECRET_KEY = os.environ.get("SAFETRENDBOT_SECRET", "change_me_in_production_abc123xyz")
ADMIN_TOKEN = os.environ.get("SAFETRENDBOT_ADMIN_TOKEN", secrets.token_hex(32))

# Database
DATABASE = os.environ.get("SAFETRENDBOT_DB", "licenses.db")

# Rate limiting
RATE_LIMIT_WINDOW = 60  # secondes
RATE_LIMIT_MAX = 10     # requêtes

# Config
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
PORT = int(os.environ.get("PORT", 5000))


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ActivationServer")


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def get_db() -> sqlite3.Connection:
    """Retourne la connexion DB pour ce thread."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, timeout=30)
        g.db.row_factory = sqlite3.Row
    return g.db


@APP.teardown_appcontext
def close_db(error):
    """Ferme la connexion à la fin de la requête."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initialise le schéma de la DB."""
    conn = get_db()
    conn.executescript('''
        -- Table principale des licences
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            license_type TEXT DEFAULT 'standard',
            hw_token TEXT,
            hw_fingerprint TEXT,
            machine_name TEXT,
            os_info TEXT,
            activated_at TEXT,
            expires_at TEXT,
            revoked INTEGER DEFAULT 0,
            revoked_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_heartbeat TEXT
        );
        
        -- Table des activations (historique)
        CREATE TABLE IF NOT EXISTS activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT,
            hw_token TEXT,
            hw_fingerprint TEXT,
            machine_info TEXT,
            ip_address TEXT,
            activated_at TEXT DEFAULT (datetime('now')),
            is_current INTEGER DEFAULT 0,
            FOREIGN KEY (license_key) REFERENCES licenses(key)
        );
        
        -- Table des heartbeat
        CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            uptime_seconds INTEGER,
            ip_address TEXT,
            version TEXT,
            FOREIGN KEY (license_key) REFERENCES licenses(key)
        );
        
        -- Table des tentatives échouées (rate limiting)
        CREATE TABLE IF NOT EXISTS failed_attempts (
            ip TEXT PRIMARY KEY,
            attempts INTEGER DEFAULT 0,
            first_attempt TEXT,
            last_attempt TEXT
        );
        
        -- Index pour performances
        CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(email);
        CREATE INDEX IF NOT EXISTS idx_licenses_hw ON licenses(hw_token);
        CREATE INDEX IF NOT EXISTS idx_activations_key ON activations(license_key);
        CREATE INDEX IF NOT EXISTS idx_heartbeats_key ON heartbeats(license_key);
    ''')
    conn.commit()
    logger.info("Database initialisée")


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def verify_signature(payload: dict, signature: str) -> bool:
    """Vérifie la signature HMAC d'un payload."""
    msg = json.dumps(payload, sort_keys=True)
    expected = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha3_256).hexdigest()
    return hmac.compare_digest(expected, signature)


def require_admin(f):
    """Décorateur: exige le token admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(token, ADMIN_TOKEN):
            logger.warning(f"Admin access denied from {request.remote_addr}")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def rate_limit(f):
    """Décorateur: limite les requêtes par IP."""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        now = datetime.now()
        
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM failed_attempts WHERE ip = ?", (ip,)
        ).fetchone()
        
        if row:
            attempts = row["attempts"]
            last = datetime.fromisoformat(row["last_attempt"])
            
            # Reset si fenêtre passée
            if (now - last).total_seconds() > RATE_LIMIT_WINDOW:
                conn.execute(
                    "UPDATE failed_attempts SET attempts = 0 WHERE ip = ?", (ip,)
                )
                conn.commit()
                attempts = 0
            
            if attempts >= RATE_LIMIT_MAX:
                logger.warning(f"Rate limit exceeded for {ip}")
                return jsonify({
                    "error": "Too many requests",
                    "retry_after": RATE_LIMIT_WINDOW
                }), 429
        
        return f(*args, **kwargs)
    return decorated


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def create_license_token(license_key: str, hw_fingerprint: str) -> str:
    """Crée un token signé pour cette activation."""
    data = f"{license_key}:{hw_fingerprint}:{datetime.now().isoformat()}"
    sig = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha3_256).hexdigest()
    return f"{license_key}:{sig[:32]}"


def validate_hw_fingerprint(hw_token: str, server_token: str) -> bool:
    """Valide que le hw_token correspond."""
    # Le client envoie hw_token calculé depuis hw_fingerprint
    # Le serveur le compare avec ce qu'il a stocké
    if not server_token:
        return True  # Première activation, accepter
    return hmac.compare_digest(hw_token, server_token)


def log_failed_attempt(ip: str):
    """Log une tentative échouée."""
    conn = get_db()
    now = datetime.now().isoformat()
    
    conn.execute('''
        INSERT INTO failed_attempts (ip, attempts, first_attempt, last_attempt)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(ip) DO UPDATE SET
            attempts = attempts + 1,
            last_attempt = ?
    ''', (ip, now, now, now))
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# API PUBLICS (appelés par les clients)
# ═══════════════════════════════════════════════════════════════════════════════

@APP.route("/api/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@APP.route("/api/activate", methods=["POST"])
@rate_limit
def activate():
    """
    Active une licence sur une machine.
    
    Payload:
    {
        "license_key": "STB5-XXXX-XXXX-XXXX",
        "email": "client@example.com",
        "hw_token": "sha3_hash_du_hardware",
        "hw_fingerprint": "cpu_mac_disk_ids",
        "machine_name": "PC-JEAN",
        "os_info": "Windows 11",
        "version": "5.3.0"
    }
    
    Response:
    {
        "success": true,
        "token": "signed_activation_token",
        "expires_at": "2025-12-31T23:59:59"
    }
    """
    data = request.get_json() or {}
    
    # Extraire champs
    license_key = data.get("license_key", "").strip()
    email = data.get("email", "").strip()
    hw_token = data.get("hw_token", "")
    hw_fingerprint = data.get("hw_fingerprint", "")
    machine_name = data.get("machine_name", "Unknown")
    os_info = data.get("os_info", "")
    version = data.get("version", "")
    
    # Validation
    if not license_key:
        log_failed_attempt(request.remote_addr)
        return jsonify({"error": "license_key required"}), 400
    
    if not hw_token:
        log_failed_attempt(request.remote_addr)
        return jsonify({"error": "hw_token required"}), 400
    
    # Vérifier format clé
    import re
    if not re.match(r"^STB5-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$", license_key, re.I):
        log_failed_attempt(request.remote_addr)
        return jsonify({"error": "Invalid license key format"}), 400
    
    conn = get_db()
    
    # Récupérer licence
    lic = conn.execute(
        "SELECT * FROM licenses WHERE key = ?", (license_key,)
    ).fetchone()
    
    if not lic:
        logger.warning(f"Activation attempt with unknown key: {license_key}")
        log_failed_attempt(request.remote_addr)
        return jsonify({"error": "Invalid license key"}), 404
    
    # Vérifier si révoquée
    if lic["revoked"]:
        logger.warning(f"Activation attempt on revoked key: {license_key}")
        return jsonify({
            "error": "License has been revoked",
            "revoked_at": lic["revoked_at"]
        }), 403
    
    # Vérifier expiration
    if lic["expires_at"]:
        expires = datetime.fromisoformat(lic["expires_at"])
        if datetime.now() > expires:
            return jsonify({
                "error": "License has expired",
                "expired_at": lic["expires_at"]
            }), 403
    
    # Vérifier hardware binding
    if lic["hw_token"] and lic["hw_token"] != hw_token:
        # Hardware différent — vérifier si c'est un transfert non autorisé
        logger.warning(
            f"Hardware mismatch for {license_key}: "
            f"expected {lic['hw_token'][:16]}..., got {hw_token[:16]}..."
        )
        return jsonify({
            "error": "License bound to different hardware",
            "hint": "Contact support to transfer license"
        }), 403
    
    # Créer le token d'activation
    activation_token = create_license_token(license_key, hw_fingerprint)
    
    # Enregistrer l'activation
    now = datetime.now().isoformat()
    
    # Marquer les anciennes activations comme non courantes
    conn.execute(
        "UPDATE activations SET is_current = 0 WHERE license_key = ?",
        (license_key,)
    )
    
    # Nouvelle activation
    conn.execute('''
        INSERT INTO activations 
        (license_key, hw_token, hw_fingerprint, machine_info, ip_address, is_current)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (license_key, hw_token, hw_fingerprint, 
          f"{machine_name} | {os_info} | v{version}",
          request.remote_addr))
    
    # Mettre à jour licence si première fois
    if not lic["hw_token"]:
        conn.execute('''
            UPDATE licenses 
            SET hw_token = ?, hw_fingerprint = ?, machine_name = ?, 
                os_info = ?, activated_at = ?
            WHERE key = ?
        ''', (hw_token, hw_fingerprint, machine_name, os_info, now, license_key))
    
    # Update last heartbeat
    conn.execute(
        "UPDATE licenses SET last_heartbeat = ? WHERE key = ?",
        (now, license_key)
    )
    
    conn.commit()
    
    logger.info(f"Activated: {license_key} on {machine_name} ({request.remote_addr})")
    
    return jsonify({
        "success": True,
        "token": activation_token,
        "activated_at": now,
        "expires_at": lic["expires_at"],
        "license_type": lic["license_type"]
    })


@APP.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    """
    Heartbeat pour maintenir la connexion et rapporter le statut.
    
    Payload:
    {
        "license_key": "STB5-...",
        "token": "activation_token",
        "uptime_seconds": 3600,
        "version": "5.3.0"
    }
    """
    data = request.get_json() or {}
    
    license_key = data.get("license_key", "")
    token = data.get("token", "")
    uptime = data.get("uptime_seconds", 0)
    version = data.get("version", "")
    
    if not license_key:
        return jsonify({"error": "license_key required"}), 400
    
    conn = get_db()
    
    # Vérifier licence
    lic = conn.execute(
        "SELECT * FROM licenses WHERE key = ?", (license_key,)
    ).fetchone()
    
    if not lic:
        return jsonify({"error": "License not found"}), 404
    
    if lic["revoked"]:
        return jsonify({
            "error": "License revoked",
            "action": "stop"
        }), 403
    
    now = datetime.now().isoformat()
    
    # Log heartbeat
    conn.execute('''
        INSERT INTO heartbeats (license_key, uptime_seconds, ip_address, version)
        VALUES (?, ?, ?, ?)
    ''', (license_key, uptime, request.remote_addr, version))
    
    # Update last heartbeat
    conn.execute(
        "UPDATE licenses SET last_heartbeat = ? WHERE key = ?",
        (now, license_key)
    )
    
    conn.commit()
    
    return jsonify({
        "ok": True,
        "server_time": now,
        "message": "Heartbeat received"
    })


@APP.route("/api/check", methods=["POST"])
def check():
    """
    Vérifie rapidement si la licence est toujours valide.
    Plus léger que heartbeat - pour vérifications périodiques.
    """
    data = request.get_json() or {}
    license_key = data.get("license_key", "")
    
    if not license_key:
        return jsonify({"error": "license_key required"}), 400
    
    conn = get_db()
    lic = conn.execute(
        "SELECT key, revoked, expires_at, last_heartbeat FROM licenses WHERE key = ?",
        (license_key,)
    ).fetchone()
    
    if not lic:
        return jsonify({"valid": False, "reason": "not_found"})
    
    if lic["revoked"]:
        return jsonify({"valid": False, "reason": "revoked"})
    
    if lic["expires_at"]:
        if datetime.now() > datetime.fromisoformat(lic["expires_at"]):
            return jsonify({"valid": False, "reason": "expired"})
    
    return jsonify({"valid": True})


@APP.route("/api/revoke-self", methods=["POST"])
def revoke_self():
    """
    Permet au client de se désinscrire (révoquer sa propre licence).
    Utile si le client veut réactiver sur une autre machine.
    """
    data = request.get_json() or {}
    license_key = data.get("license_key", "")
    reason = data.get("reason", "User requested")
    
    if not license_key:
        return jsonify({"error": "license_key required"}), 400
    
    conn = get_db()
    
    # Marquer comme révoquée
    conn.execute('''
        UPDATE licenses 
        SET revoked = 1, revoked_at = ?, hw_token = NULL
        WHERE key = ?
    ''', (datetime.now().isoformat(), license_key))
    
    conn.commit()
    
    logger.info(f"Self-revoked: {license_key} - Reason: {reason}")
    
    return jsonify({"success": True, "message": "License revoked"})


# ═══════════════════════════════════════════════════════════════════════════════
# API ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@APP.route("/api/admin/stats", methods=["GET"])
@require_admin
def admin_stats():
    """Statistiques globales."""
    conn = get_db()
    
    total = conn.execute("SELECT COUNT(*) as c FROM licenses").fetchone()["c"]
    active = conn.execute(
        "SELECT COUNT(*) as c FROM licenses WHERE revoked = 0"
    ).fetchone()["c"]
    revoked = conn.execute(
        "SELECT COUNT(*) as c FROM licenses WHERE revoked = 1"
    ).fetchone()["c"]
    
    recent_activations = conn.execute('''
        SELECT COUNT(*) as c FROM activations 
        WHERE activated_at > datetime('now', '-24 hours')
    ''').fetchone()["c"]
    
    active_machines = conn.execute('''
        SELECT COUNT(DISTINCT hw_token) as c FROM licenses 
        WHERE revoked = 0 AND hw_token IS NOT NULL
    ''').fetchone()["c"]
    
    return jsonify({
        "total_licenses": total,
        "active_licenses": active,
        "revoked_licenses": revoked,
        "recent_activations_24h": recent_activations,
        "active_machines": active_machines
    })


@APP.route("/api/admin/licenses", methods=["GET"])
@require_admin
def admin_list_licenses():
    """Liste toutes les licences."""
    conn = get_db()
    
    licenses = conn.execute('''
        SELECT * FROM licenses ORDER BY created_at DESC
    ''').fetchall()
    
    return jsonify({
        "licenses": [dict(row) for row in licenses]
    })


@APP.route("/api/admin/license/<key>", methods=["GET"])
@require_admin
def admin_get_license(key):
    """Détail d'une licence."""
    conn = get_db()
    
    lic = conn.execute(
        "SELECT * FROM licenses WHERE key = ?", (key,)
    ).fetchone()
    
    if not lic:
        return jsonify({"error": "Not found"}), 404
    
    activations = conn.execute('''
        SELECT * FROM activations WHERE license_key = ? 
        ORDER BY activated_at DESC LIMIT 10
    ''', (key,)).fetchall()
    
    heartbeats = conn.execute('''
        SELECT * FROM heartbeats WHERE license_key = ? 
        ORDER BY timestamp DESC LIMIT 50
    ''', (key,)).fetchall()
    
    return jsonify({
        "license": dict(lic),
        "activations": [dict(row) for row in activations],
        "recent_heartbeats": [dict(row) for row in heartbeats]
    })


@APP.route("/api/admin/create", methods=["POST"])
@require_admin
def admin_create_license():
    """Crée une nouvelle licence."""
    data = request.get_json() or {}
    
    import re
    key = data.get("key", "")
    
    # Générer clé si non fournie
    if not key:
        chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # Pas de O, I, L
        parts = ["STB5"]
        for _ in range(3):
            parts.append("".join(secrets.choice(chars) for _ in range(4)))
        key = "-".join(parts)
    
    email = data.get("email", "")
    expiry_days = data.get("expiry_days")
    license_type = data.get("type", "standard")
    
    expires_at = None
    if expiry_days:
        expires_at = (datetime.now() + timedelta(days=expiry_days)).isoformat()
    
    conn = get_db()
    
    try:
        conn.execute('''
            INSERT INTO licenses (key, email, license_type, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (key, email, license_type, expires_at))
        conn.commit()
        
        logger.info(f"Created license: {key} for {email}")
        
        return jsonify({
            "success": True,
            "key": key,
            "email": email,
            "expires_at": expires_at
        })
    except sqlite3.IntegrityError:
        return jsonify({"error": "License key already exists"}), 409


@APP.route("/api/admin/revoke/<key>", methods=["POST"])
@require_admin
def admin_revoke_license(key):
    """Révoque une licence (admin only)."""
    conn = get_db()
    
    conn.execute('''
        UPDATE licenses 
        SET revoked = 1, revoked_at = ?, hw_token = NULL
        WHERE key = ?
    ''', (datetime.now().isoformat(), key))
    
    conn.commit()
    
    logger.warning(f"Admin revoked: {key}")
    
    return jsonify({"success": True})


@APP.route("/api/admin/delete/<key>", methods=["DELETE"])
@require_admin
def admin_delete_license(key):
    """Supprime une licence (admin only)."""
    conn = get_db()
    
    conn.execute("DELETE FROM heartbeats WHERE license_key = ?", (key,))
    conn.execute("DELETE FROM activations WHERE license_key = ?", (key,))
    conn.execute("DELETE FROM licenses WHERE key = ?", (key,))
    conn.commit()
    
    logger.warning(f"Admin deleted: {key}")
    
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════════════════════
# CORS & ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

@APP.after_request
def add_cors(response):
    """Ajoute les headers CORS."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Token"
    return response


@APP.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@APP.errorhandler(500)
def server_error(e):
    logger.exception("Server error")
    return jsonify({"error": "Internal server error"}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Init DB
    init_db()
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          SafeTrendBot Activation Server                     ║
╠══════════════════════════════════════════════════════════════╣
║  Port: {PORT:<51}║
║  Admin Token: {ADMIN_TOKEN[:32]}...                       ║
║  Database: {DATABASE:<46}║
╚══════════════════════════════════════════════════════════════╝

Endpoints:
  POST /api/activate     - Activer une licence
  POST /api/heartbeat    - Heartbeat
  POST /api/check        - Vérifier validité
  POST /api/revoke-self  - Auto-révocation
  GET  /api/admin/stats  - Stats (admin)
  POST /api/admin/create - Créer licence (admin)
  POST /api/admin/revoke/<key> - Révoquer (admin)
    """)
    
    APP.run(host="0.0.0.0", port=PORT, debug=DEBUG)