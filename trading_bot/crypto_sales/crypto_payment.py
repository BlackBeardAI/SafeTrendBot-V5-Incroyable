"""
SafeTrendBot — Système de Paiement Crypto
=========================================
Accepte BTC, ETH, USDT pour achat direct du bot.
Sans abonnement — paiement unique = licence permanente.
"""

import os
import json
import time
import uuid
import hashlib
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import secrets

import requests

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CryptoConfig:
    """Configuration des wallets crypto."""
    # Vos addresses wallet (REMPLACER PAR LES VÔTRES)
    BTC_ADDRESS: str = "bc1qxxzn05t7jvdmz47ncnxlglczhh9aet3gcpt5dx"  # Exemple
    ETH_ADDRESS: str = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"  # Exemple
    USDT_ERC20_ADDRESS: str = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"  # Même qu'ETH
    USDT_TRC20_ADDRESS: str = "TDtd5bLSo7tN2FbKqN8K2M1rXK6M2N5B7j"  # Tron wallet
    
    # API keys (optionnel - pour vérification automatique)
    BLOCKCHAIN_API_KEY: str = ""  # blockchain.info pour BTC, etc.
    CRYPTOCOMPARE_API_KEY: str = ""
    
    # Taux de change (mise à jour automatique)
    CURRENCY_API: str = "https://api.coingecko.com/api/v3"


class PaymentStatus(Enum):
    """Statut d'un paiement."""
    PENDING = "pending"           # En attente de paiement
    PARTIAL = "partial"           # Paiement partiel reçu
    CONFIRMED = "confirmed"       # Confirmé sur blockchain
    COMPLETED = "completed"       # Complété + licence générée
    EXPIRED = "expired"           # Délai dépassé
    CANCELLED = "cancelled"       # Annulé


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

DATABASE_PATH = Path(__file__).parent / "crypto_sales" / "payments.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db():
    """Connexion à la DB."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialise le schéma de la DB."""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            email TEXT,
            order_id TEXT UNIQUE,
            crypto_currency TEXT NOT NULL,
            amount_crypto REAL NOT NULL,
            amount_usd REAL NOT NULL,
            wallet_address TEXT,
            tx_hash TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            confirmed_at TEXT,
            completed_at TEXT,
            expires_at TEXT,
            license_key TEXT,
            metadata TEXT
        );
        
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            email TEXT,
            payment_id TEXT,
            crypto_currency TEXT,
            amount_usd REAL,
            sold_at TEXT DEFAULT (datetime('now')),
            hw_locked INTEGER DEFAULT 0,
            hw_token TEXT,
            activated_at TEXT,
            activated_hwid TEXT,
            revoked INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_payments_email ON payments(email);
        CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
        CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
    ''')
    
    # Prix par défaut
    conn.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES ('price_usd', '297')
    ''')
    conn.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_version', '5.3.0')
    ''')
    
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class PriceManager:
    """Gère les prix en crypto based sur taux de change."""
    
    CACHE_FILE = Path(__file__).parent / "crypto_sales" / ".price_cache"
    CACHE_DURATION = 300  # 5 minutes
    
    def __init__(self, config: CryptoConfig = None):
        self.config = config or CryptoConfig()
        self._load_cache()
    
    def _load_cache(self):
        """Charge le cache des prix."""
        if self.CACHE_FILE.exists():
            try:
                with open(self.CACHE_FILE) as f:
                    cache = json.load(f)
                    if time.time() - cache.get("timestamp", 0) < self.CACHE_DURATION:
                        self.prices = cache.get("prices", {})
                        return
            except:
                pass
        self.prices = {}
        self._fetch_prices()
    
    def _fetch_prices(self):
        """Récupère les prix depuis API."""
        try:
            # CoinGecko gratuit (pas de API key needed)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin,ethereum,tether",
                "vs_currencies": "usd"
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.prices = {
                    "BTC": data.get("bitcoin", {}).get("usd", 0),
                    "ETH": data.get("ethereum", {}).get("usd", 0),
                    "USDT": 1.0,  # USDT = USD
                }
                
                # Sauvegarder cache
                with open(self.CACHE_FILE, "w") as f:
                    json.dump({
                        "timestamp": time.time(),
                        "prices": self.prices
                    }, f)
        except Exception as e:
            logging.warning(f"Erreur fetch prix: {e}")
            # Fallback
            self.prices = {"BTC": 65000, "ETH": 3500, "USDT": 1.0}
    
    def get_price(self, crypto: str) -> float:
        """Retourne le prix en USD d'une crypto."""
        if crypto not in self.prices:
            self._fetch_prices()
        return self.prices.get(crypto, 0)
    
    def get_amount_crypto(self, amount_usd: float, crypto: str) -> float:
        """Calcule combien de crypto pour un montant USD."""
        price = self.get_price(crypto)
        if price == 0:
            return 0
        return round(amount_usd / price, 8)
    
    def get_address(self, crypto: str) -> str:
        """Retourne l'adresse wallet pour une crypto."""
        addresses = {
            "BTC": self.config.BTC_ADDRESS,
            "ETH": self.config.ETH_ADDRESS,
            "USDT_ERC20": self.config.USDT_ERC20_ADDRESS,
            "USDT_TRC20": self.config.USDT_TRC20_ADDRESS,
        }
        return addresses.get(crypto, "")


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class PaymentManager:
    """Gère le cycle de vie des paiements."""
    
    PAYMENT_DURATION = 60 * 60  # 1 heure pour payer
    
    def __init__(self, config: CryptoConfig = None):
        self.config = config or CryptoConfig()
        self.price_manager = PriceManager(config)
        init_database()
    
    def get_price_usd(self) -> float:
        """Retourne le prix en USD."""
        conn = get_db()
        row = conn.execute("SELECT value FROM settings WHERE key = 'price_usd'").fetchone()
        conn.close()
        return float(row["value"]) if row else 297.0
    
    def set_price_usd(self, price: float):
        """Met à jour le prix USD."""
        conn = get_db()
        conn.execute("UPDATE settings SET value = ? WHERE key = 'price_usd'", (str(price),))
        conn.commit()
        conn.close()
    
    def create_payment(self, email: str, crypto_currency: str) -> Dict:
        """
        Crée une demande de paiement.
        
        Returns:
            {
                "order_id": "STB-XXXX",
                "crypto": "BTC",
                "amount_crypto": 0.0045,
                "amount_usd": 297,
                "wallet_address": "bc1q...",
                "qr_data": "bitcoin:bc1q...?amount=0.0045",
                "expires_at": "2024-01-01T12:00:00",
                "payment_id": "uuid"
            }
        """
        amount_usd = self.get_price_usd()
        amount_crypto = self.price_manager.get_amount_crypto(amount_usd, crypto_currency)
        wallet = self.price_manager.get_address(crypto_currency)
        
        if not wallet:
            raise ValueError(f"Crypto non supportée: {crypto_currency}")
        
        # Créer order ID
        order_id = f"STB-{secrets.token_hex(4).upper()}"
        payment_id = str(uuid.uuid4())
        
        # Expiration
        created_at = datetime.now()
        expires_at = created_at + (self.PAYMENT_DURATION / 3600 / 24)
        
        # QR data pour wallet
        if crypto_currency == "BTC":
            qr_data = f"bitcoin:{wallet}?amount={amount_crypto}&label=SafeTrendBot"
        elif crypto_currency == "ETH":
            qr_data = f"ethereum:{wallet}?amount={amount_crypto}"
        elif "USDT" in crypto_currency:
            qr_data = f"ethereum:{wallet}?amount={amount_crypto}"  # Même format
        else:
            qr_data = wallet
        
        # Sauvegarder en DB
        conn = get_db()
        conn.execute('''
            INSERT INTO payments 
            (id, email, order_id, crypto_currency, amount_crypto, amount_usd, 
             wallet_address, status, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (payment_id, email, order_id, crypto_currency, amount_crypto, 
              amount_usd, wallet, PaymentStatus.PENDING.value, expires_at.isoformat()))
        conn.commit()
        conn.close()
        
        return {
            "order_id": order_id,
            "payment_id": payment_id,
            "crypto": crypto_currency,
            "amount_crypto": amount_crypto,
            "amount_usd": amount_usd,
            "wallet_address": wallet,
            "qr_data": qr_data,
            "expires_at": expires_at.isoformat(),
            "price_btc": self.price_manager.get_amount_crypto(amount_usd, "BTC"),
            "price_eth": self.price_manager.get_amount_crypto(amount_usd, "ETH"),
            "price_usdt": amount_usd,  # 1 USDT = 1 USD
        }
    
    def check_payment(self, payment_id: str) -> PaymentStatus:
        """
        Vérifie si un paiement a été confirmé.
        Pour usage manuel ou semi-automatique.
        """
        conn = get_db()
        payment = conn.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()
        conn.close()
        
        if not payment:
            return None
        
        # Vérifier expiration
        if payment["status"] == PaymentStatus.PENDING.value:
            expires = datetime.fromisoformat(payment["expires_at"])
            if datetime.now() > expires:
                self._expire_payment(payment_id)
                return PaymentStatus.EXPIRED
        
        return PaymentStatus(payment["status"])
    
    def confirm_payment(self, payment_id: str, tx_hash: str = None) -> Tuple[bool, str]:
        """
        Confirme un paiement manuellement et génère la licence.
        
        Returns: (success, license_key)
        """
        conn = get_db()
        
        payment = conn.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()
        
        if not payment:
            conn.close()
            return False, "Paiement non trouvé"
        
        if payment["status"] == PaymentStatus.COMPLETED.value:
            conn.close()
            return True, payment["license_key"]
        
        # Vérifier expiration
        if payment["status"] == PaymentStatus.EXPIRED.value:
            conn.close()
            return False, "Paiement expiré"
        
        # Générer licence
        license_key = self._generate_license(payment)
        
        # Mettre à jour paiement
        conn.execute('''
            UPDATE payments 
            SET status = ?, tx_hash = ?, completed_at = ?, license_key = ?
            WHERE id = ?
        ''', (PaymentStatus.COMPLETED.value, tx_hash, 
              datetime.now().isoformat(), license_key, payment_id))
        conn.commit()
        conn.close()
        
        return True, license_key
    
    def confirm_payment_by_tx(self, tx_hash: str) -> Tuple[bool, str]:
        """
        Confirme un paiement via hash de transaction blockchain.
        Nécessite API blockchain (optionnel).
        """
        # Logique pour vérifier sur blockchain
        # Option 1: Utiliser blockstream.io pour BTC
        # Option 2: Utiliser etherscan.io pour ETH/USDT
        
        # Pour l'instant, marque comme confirmé (validation manuelle)
        conn = get_db()
        payment = conn.execute(
            "SELECT * FROM payments WHERE tx_hash = ?", (tx_hash,)
        ).fetchone()
        conn.close()
        
        if payment:
            return self.confirm_payment(payment["id"], tx_hash)
        
        return False, "Transaction non trouvée dans nos records"
    
    def _generate_license(self, payment: sqlite3.Row) -> str:
        """Génère une licence pour ce paiement."""
        from builder.license_builder import LicenseGenerator
        
        # Générer clé
        license_key = LicenseGenerator.generate_key()
        
        # Sauvegarder licence
        conn = get_db()
        conn.execute('''
            INSERT INTO licenses 
            (key, email, payment_id, crypto_currency, amount_usd)
            VALUES (?, ?, ?, ?, ?)
        ''', (license_key, payment["email"], payment["id"], 
              payment["crypto_currency"], payment["amount_usd"]))
        conn.commit()
        conn.close()
        
        return license_key
    
    def _expire_payment(self, payment_id: str):
        """Marque un paiement comme expiré."""
        conn = get_db()
        conn.execute(
            "UPDATE payments SET status = ? WHERE id = ?",
            (PaymentStatus.EXPIRED.value, payment_id)
        )
        conn.commit()
        conn.close()
    
    def get_payment_info(self, payment_id: str) -> Optional[Dict]:
        """Retourne les infos d'un paiement."""
        conn = get_db()
        payment = conn.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,)
        ).fetchone()
        conn.close()
        
        if payment:
            return dict(payment)
        return None
    
    def get_payment_by_order(self, order_id: str) -> Optional[Dict]:
        """Retourne les infos par order ID."""
        conn = get_db()
        payment = conn.execute(
            "SELECT * FROM payments WHERE order_id = ?", (order_id,)
        ).fetchone()
        conn.close()
        
        if payment:
            return dict(payment)
        return None
    
    def get_all_payments(self, status: str = None) -> List[Dict]:
        """Liste tous les paiements."""
        conn = get_db()
        if status:
            payments = conn.execute(
                "SELECT * FROM payments WHERE status = ? ORDER BY created_at DESC",
                (status,)
            ).fetchall()
        else:
            payments = conn.execute(
                "SELECT * FROM payments ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [dict(p) for p in payments]
    
    def get_all_licenses(self) -> List[Dict]:
        """Liste toutes les licences vendues."""
        conn = get_db()
        licenses = conn.execute(
            "SELECT * FROM licenses ORDER BY sold_at DESC"
        ).fetchall()
        conn.close()
        return [dict(l) for l in licenses]
    
    def get_pending_count(self) -> int:
        """Nombre de paiements en attente."""
        conn = get_db()
        count = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'"
        ).fetchone()[0]
        conn.close()
        return count
    
    def get_sales_stats(self) -> Dict:
        """Statistiques de ventes."""
        conn = get_db()
        
        total_sales = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'completed'"
        ).fetchone()[0]
        
        total_revenue = conn.execute(
            "SELECT SUM(amount_usd) FROM payments WHERE status = 'completed'"
        ).fetchone()[0] or 0
        
        pending = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'"
        ).fetchone()[0]
        
        by_crypto = {}
        for crypto in ["BTC", "ETH", "USDT_ERC20", "USDT_TRC20"]:
            count = conn.execute(
                "SELECT COUNT(*) FROM payments WHERE status = 'completed' AND crypto_currency = ?",
                (crypto,)
            ).fetchone()[0]
            if count:
                by_crypto[crypto] = count
        
        conn.close()
        
        return {
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "pending_payments": pending,
            "by_crypto": by_crypto
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE GENERATOR (Local)
# ═══════════════════════════════════════════════════════════════════════════════

class LocalLicenseGenerator:
    """Génère des licences pour le système de vente crypto."""
    
    @staticmethod
    def generate_key(prefix: str = "STB5") -> str:
        """Génère une clé au format STB5-XXXX-XXXX-XXXX."""
        import string
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('O', '').replace('I', '').replace('L', '')
        
        parts = []
        for _ in range(3):
            part = ''.join(secrets.choice(chars) for _ in range(4))
            parts.append(part)
        
        return f"{prefix}-{'-'.join(parts)}"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pm = PaymentManager()
    
    # Prix
    print(f"Prix USD: {pm.get_price_usd()}")
    
    # Créer un paiement test
    payment = pm.create_payment("test@example.com", "BTC")
    print(f"\nPaiement créé:")
    print(f"  Order ID: {payment['order_id']}")
    print(f"  Crypto: {payment['crypto']}")
    print(f"  Montant: {payment['amount_crypto']} {payment['crypto']}")
    print(f"  Wallet: {payment['wallet_address']}")
    print(f"  QR: {payment['qr_data'][:50]}...")
    print(f"  Expire: {payment['expires_at']}")
    
    # Statistiques
    stats = pm.get_sales_stats()
    print(f"\nStats: {stats}")