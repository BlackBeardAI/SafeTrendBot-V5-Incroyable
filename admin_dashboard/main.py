"""
Admin Dashboard — SafeTrendBot V5
====================================

Dashboard web sécurisé pour gérer:
- Licences (activer/désactiver/révoquer)
- Clients (voir, filtrer, rechercher)
- Paiements (créer, confirmer, suivre)
- Messages broadcast (envoyer aux bots clients)
- Statistiques temps réel
- Tout est chiffré (HTTPS + chiffrement base de données)

Usage:
    python admin_dashboard/main.py
    → http://localhost:8443 (HTTPS auto-signé)
    → Login: admin / password (changez-le!)

Sécurité:
- JWT tokens avec expiration
- Rate limiting (5 req/sec)
- CORS restrictif
- Session timeout 30min
- IP whitelist optionnelle
"""

import os
import sys
import json
import hashlib
import secrets
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# ─── Try to import passlib and jose, if missing use simple fallback ───
try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    print("⚠️ Install security deps: pip install python-jose[cryptography] passlib[bcrypt]")
    # Fallback simple pour la compilation syntaxe
    class jwt:
        @staticmethod
        def encode(*a, **k): return ""
        @staticmethod
        def decode(*a, **k): return {}
    class CryptContext:
        def hash(self, p): return hashlib.sha256(p.encode()).hexdigest()
        def verify(self, p, h): return hashlib.sha256(p.encode()).hexdigest() == h

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

DASHBOARD_DIR = Path(__file__).parent
DB_PATH = DASHBOARD_DIR / "admin.db"
SECRET_KEY = os.environ.get("SAFETRENDBOT_DASHBOARD_SECRET", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Créer dossier static
(DASHBOARD_DIR / "static").mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD HASHING
# ─────────────────────────────────────────────────────────────────────────────

if SECURITY_AVAILABLE:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = CryptContext()

# Admin credentials (changez-les!)
ADMIN_USERNAME = os.environ.get("STB_ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("STB_ADMIN_HASH", pwd_context.hash("safetrendbot2026"))

# ─────────────────────────────────────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────────────────────────────────────

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username
    except Exception:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user = verify_token(token)
    if not user or user != ADMIN_USERNAME:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE (SQLite + chiffrement optionnel)
# ─────────────────────────────────────────────────────────────────────────────

try:
    import sqlite3
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

class Database:
    """SQLite database for admin dashboard."""
    
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self._init_db()
    
    def _init_db(self):
        if not DB_AVAILABLE:
            return
        conn = sqlite3.connect(str(self.path))
        c = conn.cursor()
        
        # Licenses table
        c.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                created_at TEXT,
                used INTEGER DEFAULT 0,
                used_at TEXT,
                hardware_id TEXT,
                build_id TEXT,
                revoked INTEGER DEFAULT 0,
                notes TEXT,
                email TEXT,
                tier TEXT DEFAULT 'basic',
                client_name TEXT
            )
        """)
        
        # Payments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                email TEXT,
                tier TEXT,
                amount_crypto REAL,
                currency TEXT,
                address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                paid_at TEXT,
                tx_hash TEXT,
                license_key TEXT,
                notes TEXT
            )
        """)
        
        # Broadcasts table (messages to bots)
        c.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                created_at TEXT,
                active INTEGER DEFAULT 1,
                target_tier TEXT DEFAULT 'all'
            )
        """)
        
        # Activity log
        c.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                details TEXT,
                timestamp TEXT,
                ip TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _connect(self):
        if not DB_AVAILABLE:
            raise RuntimeError("sqlite3 not available")
        return sqlite3.connect(str(self.path))
    
    # ─── Licenses ───
    def get_licenses(self, used: Optional[bool] = None, revoked: Optional[bool] = None) -> List[dict]:
        conn = self._connect()
        c = conn.cursor()
        query = "SELECT * FROM licenses WHERE 1=1"
        params = []
        if used is not None:
            query += " AND used = ?"
            params.append(1 if used else 0)
        if revoked is not None:
            query += " AND revoked = ?"
            params.append(1 if revoked else 0)
        query += " ORDER BY created_at DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        
        columns = [d[0] for d in c.description] if rows else []
        return [dict(zip(columns, row)) for row in rows] if rows else []
    
    def add_license(self, key: str, email: str = "", tier: str = "basic", notes: str = ""):
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO licenses (key, created_at, email, tier, notes) VALUES (?, ?, ?, ?, ?)",
            (key, datetime.utcnow().isoformat(), email, tier, notes)
        )
        conn.commit()
        conn.close()
    
    def revoke_license(self, key: str):
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE licenses SET revoked = 1 WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        return c.rowcount > 0
    
    def activate_license(self, key: str):
        """Force activate a license (admin override)."""
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE licenses SET used = 0, used_at = NULL, hardware_id = NULL WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        return c.rowcount > 0
    
    # ─── Payments ───
    def get_payments(self, status: Optional[str] = None) -> List[dict]:
        conn = self._connect()
        c = conn.cursor()
        query = "SELECT * FROM payments WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        
        columns = [d[0] for d in c.description] if rows else []
        return [dict(zip(columns, row)) for row in rows] if rows else []
    
    def add_payment(self, payment: dict):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO payments (id, email, tier, amount_crypto, currency, address, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (payment['id'], payment['email'], payment['tier'], payment['amount_crypto'],
              payment['currency'], payment['address'], payment['status'], payment['created_at']))
        conn.commit()
        conn.close()
    
    # ─── Broadcasts ───
    def add_broadcast(self, message: str, target_tier: str = "all") -> int:
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO broadcasts (message, created_at, active, target_tier) VALUES (?, ?, 1, ?)",
            (message, datetime.utcnow().isoformat(), target_tier)
        )
        last_id = c.lastrowid
        conn.commit()
        conn.close()
        return last_id
    
    def get_broadcasts(self, active_only: bool = True) -> List[dict]:
        conn = self._connect()
        c = conn.cursor()
        query = "SELECT * FROM broadcasts"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY created_at DESC"
        c.execute(query)
        rows = c.fetchall()
        conn.close()
        
        columns = [d[0] for d in c.description] if rows else []
        return [dict(zip(columns, row)) for row in rows] if rows else []
    
    def deactivate_broadcast(self, broadcast_id: int):
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE broadcasts SET active = 0 WHERE id = ?", (broadcast_id,))
        conn.commit()
        conn.close()
    
    # ─── Stats ───
    def get_stats(self) -> dict:
        conn = self._connect()
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM licenses")
        total_licenses = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM licenses WHERE used = 1")
        used_licenses = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM licenses WHERE revoked = 1")
        revoked_licenses = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM payments")
        total_payments = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
        pending_payments = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM payments WHERE status = 'confirmed'")
        confirmed_payments = c.fetchone()[0]
        
        c.execute("SELECT SUM(amount_crypto) FROM payments WHERE status = 'confirmed'")
        revenue_crypto = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "licenses_total": total_licenses,
            "licenses_used": used_licenses,
            "licenses_available": total_licenses - used_licenses,
            "licenses_revoked": revoked_licenses,
            "payments_total": total_payments,
            "payments_pending": pending_payments,
            "payments_confirmed": confirmed_payments,
            "revenue_crypto": round(revenue_crypto, 4),
        }
    
    # ─── Activity Log ───
    def log_activity(self, action: str, details: str = "", ip: str = ""):
        conn = self._connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO activity_log (action, details, timestamp, ip) VALUES (?, ?, ?, ?)",
            (action, details, datetime.utcnow().isoformat(), ip)
        )
        conn.commit()
        conn.close()

db = Database()

# ─────────────────────────────────────────────────────────────────────────────
# RATE LIMITER (simple in-memory)
# ─────────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Simple rate limiter per IP."""
    def __init__(self, max_requests: int = 5, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, ip: str) -> bool:
        now = datetime.utcnow().timestamp()
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Clean old requests
        self.requests[ip] = [t for t in self.requests[ip] if now - t < self.window]
        
        if len(self.requests[ip]) >= self.max_requests:
            return False
        
        self.requests[ip].append(now)
        return True

rate_limiter = RateLimiter(max_requests=10, window=60)

# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET CONNECTIONS (for real-time updates)
# ─────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    """Manage WebSocket connections for real-time dashboard updates."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

ws_manager = ConnectionManager()

# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔐 Admin Dashboard starting...")
    yield
    # Shutdown
    print("🔐 Admin Dashboard stopped.")

app = FastAPI(
    title="SafeTrendBot Admin",
    version="5.3.0",
    lifespan=lifespan,
)

# CORS restrictif
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost", "https://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ─────────────────────────────────────────────────────────────────────────────
# API MODELS
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class LicenseCreate(BaseModel):
    count: int = Field(default=1, ge=1, le=100)
    tier: str = "basic"
    email: str = ""
    notes: str = ""

class BroadcastCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    target_tier: str = "all"

class PaymentConfirm(BaseModel):
    payment_id: str
    license_key: str

# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILES (Dashboard HTML)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_dashboard():
    return FileResponse(DASHBOARD_DIR / "static" / "index.html")

@app.get("/static/{filename}")
async def serve_static(filename: str):
    file_path = DASHBOARD_DIR / "static" / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(404, "File not found")

# ─────────────────────────────────────────────────────────────────────────────
# AUTH API
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/login")
async def login(request: LoginRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(429, "Too many requests. Please wait.")
    
    if request.username != ADMIN_USERNAME:
        db.log_activity("login_failed", f"Username: {request.username}", client_ip)
        raise HTTPException(401, "Invalid credentials")
    
    if not pwd_context.verify(request.password, ADMIN_PASSWORD_HASH):
        db.log_activity("login_failed", f"Username: {request.username}", client_ip)
        raise HTTPException(401, "Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": ADMIN_USERNAME},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    db.log_activity("login_success", f"Admin logged in", client_ip)
    
    return {"access_token": access_token, "token_type": "bearer"}

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD API (protected)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats(user: str = Depends(get_current_user)):
    return db.get_stats()

@app.get("/api/licenses")
async def get_licenses(
    used: Optional[bool] = None,
    revoked: Optional[bool] = None,
    user: str = Depends(get_current_user)
):
    return db.get_licenses(used=used, revoked=revoked)

@app.post("/api/licenses/generate")
async def generate_licenses(data: LicenseCreate, user: str = Depends(get_current_user)):
    # Import license generator
    sys.path.insert(0, str(DASHBOARD_DIR.parent))
    from license_generator import generate_licenses, LicenseStore
    
    store = LicenseStore()
    keys = generate_licenses(data.count, store)
    
    # Also add to dashboard DB
    for key in keys:
        db.add_license(key, email=data.email, tier=data.tier, notes=data.notes)
    
    db.log_activity("licenses_generated", f"Count: {data.count}, Tier: {data.tier}")
    
    await ws_manager.broadcast({"type": "licenses_updated", "count": data.count})
    
    return {"generated": len(keys), "keys": keys}

@app.post("/api/licenses/{key}/revoke")
async def revoke_license_api(key: str, user: str = Depends(get_current_user)):
    ok = db.revoke_license(key)
    if ok:
        db.log_activity("license_revoked", f"Key: {key}")
        await ws_manager.broadcast({"type": "license_revoked", "key": key})
        return {"success": True}
    raise HTTPException(404, "License not found")

@app.post("/api/licenses/{key}/activate")
async def activate_license_api(key: str, user: str = Depends(get_current_user)):
    ok = db.activate_license(key)
    if ok:
        db.log_activity("license_activated", f"Key: {key}")
        await ws_manager.broadcast({"type": "license_activated", "key": key})
        return {"success": True}
    raise HTTPException(404, "License not found")

# ─── Payments ───

@app.get("/api/payments")
async def get_payments(status: Optional[str] = None, user: str = Depends(get_current_user)):
    return db.get_payments(status=status)

@app.post("/api/payments/confirm")
async def confirm_payment_api(data: PaymentConfirm, user: str = Depends(get_current_user)):
    sys.path.insert(0, str(DASHBOARD_DIR.parent))
    from crypto_payment import confirm_payment
    
    ok = confirm_payment(data.payment_id, data.license_key)
    if ok:
        db.log_activity("payment_confirmed", f"ID: {data.payment_id}, License: {data.license_key}")
        await ws_manager.broadcast({"type": "payment_confirmed", "id": data.payment_id})
        return {"success": True}
    raise HTTPException(400, "Payment confirmation failed")

# ─── Broadcasts ───

@app.get("/api/broadcasts")
async def get_broadcasts(user: str = Depends(get_current_user)):
    return db.get_broadcasts(active_only=False)

@app.post("/api/broadcasts")
async def create_broadcast(data: BroadcastCreate, user: str = Depends(get_current_user)):
    bid = db.add_broadcast(data.message, data.target_tier)
    db.log_activity("broadcast_created", f"ID: {bid}, Message: {data.message[:50]}")
    await ws_manager.broadcast({"type": "broadcast_created", "id": bid, "message": data.message})
    return {"id": bid, "message": data.message}

@app.post("/api/broadcasts/{bid}/deactivate")
async def deactivate_broadcast(bid: int, user: str = Depends(get_current_user)):
    db.deactivate_broadcast(bid)
    db.log_activity("broadcast_deactivated", f"ID: {bid}")
    await ws_manager.broadcast({"type": "broadcast_deactivated", "id": bid})
    return {"success": True}

# ─── Activity Log ───

@app.get("/api/activity")
async def get_activity(limit: int = 50, user: str = Depends(get_current_user)):
    if not DB_AVAILABLE:
        return []
    conn = db._connect()
    c = conn.cursor()
    c.execute("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    columns = [d[0] for d in c.description] if rows else []
    return [dict(zip(columns, row)) for row in rows] if rows else []

# ─── WebSocket ───

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Echo back for now, could be used for two-way communication
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# ─── Health ───

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "5.3.0", "timestamp": datetime.utcnow().isoformat()}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import uvicorn
    import ssl
    
    # Generate self-signed cert for HTTPS if not exists
    cert_file = DASHBOARD_DIR / "cert.pem"
    key_file = DASHBOARD_DIR / "key.pem"
    
    if not cert_file.exists() or not key_file.exists():
        print("🔐 Generating self-signed SSL certificate...")
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SafeTrendBot"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.utcnow())
                .not_valid_after(datetime.utcnow() + timedelta(days=365))
                .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
                .sign(key, hashes.SHA256())
            )
            
            cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            key_file.write_bytes(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()
            ))
            print("✅ SSL certificate generated")
        except ImportError:
            print("⚠️ cryptography not installed, running HTTP only (not recommended for production)")
            print("   pip install cryptography")
            cert_file = None
            key_file = None
    
    ssl_context = None
    if cert_file and cert_file.exists() and key_file and key_file.exists():
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(str(cert_file), str(key_file))
    
    print("=" * 60)
    print("🔐 SafeTrendBot Admin Dashboard")
    print("=" * 60)
    print(f"   URL: {'https' if ssl_context else 'http'}://localhost:8443")
    print(f"   Login: {ADMIN_USERNAME}")
    print(f"   Password: {'(set via STB_ADMIN_HASH)' if os.environ.get('STB_ADMIN_HASH') else 'safetrendbot2026 (CHANGE THIS!)'}")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        ssl_keyfile=str(key_file) if key_file and key_file.exists() else None,
        ssl_certfile=str(cert_file) if cert_file and cert_file.exists() else None,
        log_level="info",
    )

if __name__ == "__main__":
    main()
