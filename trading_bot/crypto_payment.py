"""
CryptoPayment Manager — Paiement crypto + gestion à distance
=============================================================

Ce module gère:
- Génération d'adresses de paiement crypto (BTC, ETH, USDT-TRC20)
- Vérification des paiements via APIs publiques (BlockCypher, Etherscan, TronGrid)
- Notification Telegram à l'admin quand un paiement est reçu
- Génération manuelle de licence par l'admin après confirmation

Usage (par l'admin uniquement):
    python crypto_payment.py new --email client@example.com --amount 99 --currency USDT
    → Génère une adresse USDT TRC20, envoie les instructions au client

    python crypto_payment.py check --address YOUR_ADDRESS
    → Vérifie si le paiement a été reçu

    python crypto_payment.py confirm --address YOUR_ADDRESS --license XXXX-XXXX
    → Marque le paiement comme confirmé, envoie la licence au client
"""

import sys
import json
import hashlib
import secrets
import string
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

PAYMENTS_FILE = Path("payments.json")
PRICES = {
    "basic": {"eur": 99, "usd": 109, "description": "SafeTrendBot V5 — 1 PC"},
    "pro": {"eur": 199, "usd": 219, "description": "SafeTrendBot V5 — 3 PCs"},
    "extreme": {"eur": 349, "usd": 379, "description": "SafeTrendBot V5 — Mode EXTREME"},
}

# APIs publiques (gratuites, pas de clé API requise)
BTC_API = "https://api.blockcypher.com/v1/btc/main/addrs/{address}/balance"
ETH_API = "https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest"
TRON_API = "https://apilist.tronscanapi.com/api/account/tokens?address={address}&start=0&limit=20"

# Telegram admin notification
TELEGRAM_ADMIN_BOT_TOKEN = ""  # À configurer
TELEGRAM_ADMIN_CHAT_ID = ""    # À configurer


# ─────────────────────────────────────────────────────────────────────────────
# STOCKAGE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Payment:
    id: str
    email: str
    tier: str
    amount_crypto: float
    currency: str          # BTC, ETH, USDT
    address: str
    status: str           # pending, paid, confirmed, expired
    created_at: str
    paid_at: Optional[str] = None
    tx_hash: Optional[str] = None
    license_key: Optional[str] = None
    notes: str = ""


class PaymentStore:
    def __init__(self, path: Path = PAYMENTS_FILE):
        self.path = path
        self.payments: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            self.payments = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.payments = {}

    def _save(self):
        self.path.write_text(json.dumps(self.payments, indent=2), encoding="utf-8")

    def add(self, p: Payment):
        self.payments[p.id] = asdict(p)
        self._save()

    def get(self, payment_id: str) -> Optional[Payment]:
        data = self.payments.get(payment_id)
        return Payment(**data) if data else None

    def get_by_address(self, address: str) -> Optional[Payment]:
        for data in self.payments.values():
            if data.get("address") == address:
                return Payment(**data)
        return None

    def update_status(self, payment_id: str, status: str, **kwargs):
        if payment_id in self.payments:
            self.payments[payment_id]["status"] = status
            for k, v in kwargs.items():
                self.payments[payment_id][k] = v
            self._save()

    def list_pending(self) -> List[Payment]:
        return [Payment(**v) for v in self.payments.values() if v.get("status") == "pending"]


# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION D'ADRESSES
# ─────────────────────────────────────────────────────────────────────────────

def generate_payment_address(currency: str) -> str:
    """
    Génère une adresse de paiement unique.
    Simplifié: en production, utilise une vraie wallet HD (Electrum, MetaMask, etc.)
    """
    # En mode simplifié, on génère un hash unique comme identifiant
    # Le vrai système utiliserait une seed phrase BIP39 + dérivation
    random_bytes = secrets.token_bytes(32)

    if currency == "BTC":
        # Fake Bitcoin address (simplifié)
        h = hashlib.new("ripemd160", random_bytes).hexdigest()
        return f"1{h[:33]}"
    elif currency == "ETH":
        # Fake Ethereum address
        h = hashlib.sha256(random_bytes).hexdigest()
        return f"0x{h[:40]}"
    elif currency in ("USDT", "TRX"):
        # Fake Tron address (USDT TRC20)
        h = hashlib.sha256(random_bytes).hexdigest()
        return f"T{h[:33]}"
    else:
        raise ValueError(f"Currency non supportée: {currency}")


def get_crypto_amount(fiat_amount: float, currency: str) -> float:
    """Convertit montant fiat en crypto (prix approximatif)."""
    # En production: appeler CoinGecko API
    rates = {
        "BTC": 65000.0,   # USD
        "ETH": 3500.0,
        "USDT": 1.0,
    }
    rate = rates.get(currency, 1.0)
    return round(fiat_amount / rate, 8)


# ─────────────────────────────────────────────────────────────────────────────
# VÉRIFICATION PAIEMENTS (APIs publiques)
# ─────────────────────────────────────────────────────────────────────────────

def check_btc_payment(address: str) -> tuple:
    """Vérifie si un paiement BTC a été reçu."""
    try:
        resp = requests.get(BTC_API.format(address=address), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            balance_sat = data.get("balance", 0)
            balance_btc = balance_sat / 100_000_000
            return balance_btc > 0, balance_btc, None
    except Exception as e:
        return False, 0, str(e)
    return False, 0, None


def check_eth_payment(address: str) -> tuple:
    """Vérifie si un paiement ETH a été reçu."""
    try:
        resp = requests.get(ETH_API.format(address=address), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "1":
                balance_wei = int(data.get("result", 0))
                balance_eth = balance_wei / 1e18
                return balance_eth > 0, balance_eth, None
    except Exception as e:
        return False, 0, str(e)
    return False, 0, None


def check_usdt_trc20(address: str) -> tuple:
    """Vérifie si un paiement USDT TRC20 a été reçu."""
    try:
        resp = requests.get(TRON_API.format(address=address), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for token in data.get("data", []):
                if token.get("tokenId") == "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t":  # USDT TRC20
                    balance = float(token.get("balance", 0)) / (10 ** token.get("tokenDecimal", 6))
                    return balance > 0, balance, None
    except Exception as e:
        return False, 0, str(e)
    return False, 0, None


def check_payment(payment: Payment) -> tuple:
    """Vérifie le paiement selon la crypto."""
    if payment.currency == "BTC":
        return check_btc_payment(payment.address)
    elif payment.currency == "ETH":
        return check_eth_payment(payment.address)
    elif payment.currency in ("USDT", "TRX"):
        return check_usdt_trc20(payment.address)
    return False, 0, "Currency inconnue"


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM NOTIFICATIONS (Admin uniquement)
# ─────────────────────────────────────────────────────────────────────────────

def notify_admin(message: str):
    """Envoie une notification à l'admin via Telegram."""
    if not TELEGRAM_ADMIN_BOT_TOKEN or not TELEGRAM_ADMIN_CHAT_ID:
        print(f"[TELEGRAM ADMIN] {message}")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_ADMIN_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_ADMIN_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
    except Exception:
        print(f"[TELEGRAM] Échec envoi: {message}")


# ─────────────────────────────────────────────────────────────────────────────
# WORKFLOW PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def create_payment_request(email: str, tier: str = "basic", currency: str = "USDT") -> Payment:
    """
    Crée une demande de paiement pour un client.
    À utiliser par l'admin uniquement.
    """
    store = PaymentStore()
    price = PRICES.get(tier, PRICES["basic"])
    fiat = price["usd"]

    crypto_amount = get_crypto_amount(fiat, currency)
    address = generate_payment_address(currency)

    payment_id = hashlib.sha256(f"{email}{time.time()}{secrets.token_hex(8)}".encode()).hexdigest()[:16]

    payment = Payment(
        id=payment_id,
        email=email,
        tier=tier,
        amount_crypto=crypto_amount,
        currency=currency,
        address=address,
        status="pending",
        created_at=datetime.utcnow().isoformat(),
    )

    store.add(payment)

    # Notifier l'admin
    msg = (
        f"💰 *Nouveau paiement en attente*\n\n"
        f"Client: `{email}`\n"
        f"Tier: `{tier}`\n"
        f"Montant: `{crypto_amount} {currency}`\n"
        f"Adresse: `{address}`\n\n"
        f"ID: `{payment_id}`\n\n"
        f"Commande admin pour confirmer:\n"
        f"`python crypto_payment.py confirm --id {payment_id} --license XXXX-XXXX`"
    )
    notify_admin(msg)

    print(f"✅ Demande de paiement créée:")
    print(f"   ID: {payment_id}")
    print(f"   Client: {email}")
    print(f"   Adresse: {address}")
    print(f"   Montant: {crypto_amount} {currency}")
    print(f"\n   Envoyez ces instructions au client:")
    print(f"   → Envoyez {crypto_amount} {currency} à l'adresse {address}")
    print(f"   → Contactez-nous une fois le paiement effectué")

    return payment


def confirm_payment(payment_id: str, license_key: str):
    """
    Confirme un paiement et associe une licence.
    À utiliser par l'admin manuellement après vérification.
    """
    store = PaymentStore()
    payment = store.get(payment_id)
    if not payment:
        print(f"❌ Paiement introuvable: {payment_id}")
        return False

    if payment.status not in ("pending", "paid"):
        print(f"❌ Statut invalide: {payment.status}")
        return False

    store.update_status(
        payment_id,
        status="confirmed",
        license_key=license_key,
        paid_at=datetime.utcnow().isoformat(),
    )

    # Notifier admin
    msg = (
        f"✅ *Paiement confirmé*\n\n"
        f"Client: `{payment.email}`\n"
        f"Licence: `{license_key}`\n"
        f"Tier: `{payment.tier}`\n\n"
        f"Envoyez la licence au client!"
    )
    notify_admin(msg)

    print(f"✅ Paiement confirmé!")
    print(f"   Client: {payment.email}")
    print(f"   Licence: {license_key}")
    print(f"\n   → Envoyez cette licence au client via email")
    print(f"   → Le build sera généré avec cette licence")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CryptoPayment Manager")
    sub = parser.add_subparsers(dest="cmd")

    # new
    new_p = sub.add_parser("new", help="Créer une demande de paiement")
    new_p.add_argument("--email", required=True)
    new_p.add_argument("--tier", choices=["basic", "pro", "extreme"], default="basic")
    new_p.add_argument("--currency", choices=["BTC", "ETH", "USDT"], default="USDT")

    # check
    check_p = sub.add_parser("check", help="Vérifier un paiement")
    check_p.add_argument("--id", help="ID du paiement")
    check_p.add_argument("--address", help="Adresse crypto")

    # confirm
    conf_p = sub.add_parser("confirm", help="Confirmer un paiement")
    conf_p.add_argument("--id", required=True)
    conf_p.add_argument("--license", required=True)

    # list
    list_p = sub.add_parser("list", help="Lister les paiements en attente")

    # prices
    price_p = sub.add_parser("prices", help="Afficher les prix")

    args = parser.parse_args()

    if args.cmd == "new":
        create_payment_request(args.email, args.tier, args.currency)
    elif args.cmd == "check":
        store = PaymentStore()
        if args.id:
            p = store.get(args.id)
        elif args.address:
            p = store.get_by_address(args.address)
        else:
            print("--id ou --address requis")
            sys.exit(1)

        if not p:
            print("❌ Paiement introuvable")
            sys.exit(1)

        paid, amount, err = check_payment(p)
        print(f"Statut: {'✅ PAYÉ' if paid else '⏳ EN ATTENTE'}")
        if paid:
            print(f"Montant reçu: {amount} {p.currency}")
        if err:
            print(f"Erreur API: {err}")
    elif args.cmd == "confirm":
        confirm_payment(args.id, args.license)
    elif args.cmd == "list":
        store = PaymentStore()
        pending = store.list_pending()
        print(f"📋 {len(pending)} paiements en attente:")
        for p in pending:
            print(f"   {p.id} | {p.email} | {p.amount_crypto} {p.currency} | {p.address}")
    elif args.cmd == "prices":
        print("💰 Tarifs SafeTrendBot:")
        for tier, info in PRICES.items():
            print(f"   {tier.upper()}: ${info['usd']} ({info['description']})")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
