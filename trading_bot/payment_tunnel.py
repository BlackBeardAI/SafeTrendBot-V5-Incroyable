"""
Payment Tunnel — Paiement crypto automatisé + livraison auto
==========================================================

Workflow complet sans intervention humaine:
    1. Client visite la page de vente
    2. Choisi un tier + rentre son email
    3. Paie en crypto (via NowPayments ou Coinbase Commerce)
    4. Webhook reçu → confirmation automatique
    5. Builder génère le build avec licence unique
    6. Email envoyé au client avec le ZIP + instructions

API utilisée: NowPayments (facile, KYC optionnel)
    - Crée un compte: https://nowpayments.io
    - Récupère API key
    - Configure le webhook URL

Usage:
    python payment_tunnel.py serve
    → Démarre le serveur webhook sur port 8080

    python payment_tunnel.py test --email client@ex.com --tier extreme
    → Simule un paiement pour test
"""

import os
import sys
import json
import hashlib
import hmac
import smtplib
import secrets
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, asdict

# ─── CONFIG ───

# NowPayments API
NOWPAYMENTS_API_KEY = os.environ.get("NOWPAYMENTS_API_KEY", "")
NOWPAYMENTS_WEBHOOK_SECRET = os.environ.get("NOWPAYMENTS_WEBHOOK_SECRET", "")

# Email SMTP (Gmail, Outlook, ou SMTP perso)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER)

# Builder config
BUILDER_DIR = Path(__file__).parent
BUILDS_DIR = BUILDER_DIR / "builds"

# Fichier de stockage des paiements
PAYMENTS_DB = BUILDER_DIR / "payment_tunnel_db.json"


@dataclass
class PaymentRecord:
    payment_id: str
    email: str
    tier: str
    amount_usd: float
    crypto_currency: str
    crypto_amount: float
    status: str  # pending, paid, confirmed, delivered
    build_path: str = ""
    license_key: str = ""
    created_at: str = ""
    paid_at: str = ""
    delivered_at: str = ""
    tx_hash: str = ""
    error: str = ""


class PaymentTunnel:
    """Tunnel de paiement automatisé SafeTrendBot."""

    def __init__(self):
        self.payments: Dict[str, dict] = {}
        self._load_db()

    def _load_db(self):
        if PAYMENTS_DB.exists():
            self.payments = json.loads(PAYMENTS_DB.read_text(encoding="utf-8"))

    def _save_db(self):
        PAYMENTS_DB.write_text(json.dumps(self.payments, indent=2), encoding="utf-8")

    # ─────────────────────────────────────────────────────────────────────────
    # ÉTAPE 1: Créer une demande de paiement
    # ─────────────────────────────────────────────────────────────────────────

    def create_payment_request(self, email: str, tier: str) -> dict:
        """
        Crée une demande de paiement NowPayments.
        Retourne l'URL de paiement à montrer au client.
        """
        import requests

        tier_prices = {"basic": 99, "pro": 199, "extreme": 349}
        amount = tier_prices.get(tier, 99)

        payment_id = f"STB_{secrets.token_hex(8).upper()}"

        # Sauvegarder la demande
        self.payments[payment_id] = asdict(PaymentRecord(
            payment_id=payment_id,
            email=email,
            tier=tier,
            amount_usd=amount,
            crypto_currency="USDT",
            crypto_amount=amount,
            status="pending",
            created_at=datetime.utcnow().isoformat(),
        ))
        self._save_db()

        if not NOWPAYMENTS_API_KEY:
            # Mode démo: retourne un lien de paiement simulé
            return {
                "payment_id": payment_id,
                "payment_url": f"https://nowpayments.io/payment/?iid={payment_id}",
                "amount": amount,
                "currency": "USDT",
                "email": email,
                "tier": tier,
                "mode": "demo",
            }

        # Appel API NowPayments
        try:
            resp = requests.post(
                "https://api.nowpayments.io/v1/payment",
                headers={"x-api-key": NOWPAYMENTS_API_KEY},
                json={
                    "price_amount": amount,
                    "price_currency": "usd",
                    "pay_currency": "usdttrc20",
                    "ipn_callback_url": f"https://217.160.191.107:8080/webhook",
                    "order_id": payment_id,
                    "order_description": f"SafeTrendBot {tier.upper()}",
                    "customer_email": email,
                },
                timeout=30,
            )
            data = resp.json()
            return {
                "payment_id": payment_id,
                "payment_url": data.get("invoice_url", ""),
                "pay_address": data.get("pay_address", ""),
                "amount": data.get("pay_amount", amount),
                "currency": "USDT_TRC20",
                "email": email,
                "tier": tier,
            }
        except Exception as e:
            return {"error": str(e), "payment_id": payment_id}

    # ─────────────────────────────────────────────────────────────────────────
    # ÉTAPE 2: Recevoir le webhook (paiement confirmé)
    # ─────────────────────────────────────────────────────────────────────────

    def handle_webhook(self, payload: dict, signature: str = "") -> bool:
        """
        Traite le webhook de NowPayments.
        Si le paiement est confirmé → génère le build + envoie email.
        """
        payment_id = payload.get("order_id", "")
        payment_status = payload.get("payment_status", "")

        if payment_id not in self.payments:
            print(f"❌ Paiement inconnu: {payment_id}")
            return False

        record = self.payments[payment_id]

        if payment_status in ("finished", "confirmed", "sending"):
            print(f"✅ Paiement confirmé: {payment_id}")
            record["status"] = "paid"
            record["paid_at"] = datetime.utcnow().isoformat()
            record["tx_hash"] = payload.get("pay_hash", "")
            self._save_db()

            # AUTOMATIQUE: générer build + envoyer
            self._auto_deliver(payment_id)
            return True

        elif payment_status in ("failed", "expired", "refunded"):
            record["status"] = payment_status
            self._save_db()
            return False

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # ÉTAPE 3: Générer le build et envoyer
    # ─────────────────────────────────────────────────────────────────────────

    def _auto_deliver(self, payment_id: str):
        """Génère le build et envoie par email automatiquement."""
        record = self.payments.get(payment_id)
        if not record:
            return

        email = record["email"]
        tier = record["tier"]

        print(f"📦 Génération du build pour {email}...")

        # Générer le build
        try:
            sys.path.insert(0, str(BUILDER_DIR))
            from builder import build_single

            result = build_single(tier, email)
            if not result.get("success"):
                record["error"] = "Build failed"
                self._save_db()
                return

            zip_path = result.get("zip", "")
            license_key = result.get("license", "")

            record["build_path"] = zip_path
            record["license_key"] = license_key
            record["status"] = "delivered"
            record["delivered_at"] = datetime.utcnow().isoformat()
            self._save_db()

            # Envoyer l'email
            self._send_email(email, tier, license_key, zip_path)

            print(f"✅ Livraison terminée: {email}")

        except Exception as e:
            record["error"] = str(e)
            self._save_db()
            print(f"❌ Erreur livraison: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # ÉTAPE 4: Email client
    # ─────────────────────────────────────────────────────────────────────────

    def _send_email(self, to_email: str, tier: str, license_key: str, build_path: str):
        """Envoi de l'email avec le build au client."""
        if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
            print("⚠️  SMTP non configuré — email non envoyé")
            print(f"   Configure: SMTP_HOST, SMTP_USER, SMTP_PASSWORD")
            return False

        tier_labels = {"basic": "Basic", "pro": "Pro", "extreme": "EXTREME"}
        label = tier_labels.get(tier, tier)

        subject = f"🤖 SafeTrendBot V5 — Votre licence {label}"

        body = f"""Bonjour,

Votre paiement pour SafeTrendBot V5 {label} a été confirmé.

Voici votre licence: {license_key}

Votre build personnalisé est prêt. Il ne fonctionnera que sur l'ordinateur où vous l'activez la première fois.

INSTRUCTIONS:
1. Téléchargez le fichier ZIP attaché
2. Extrayez-le sur votre ordinateur
3. Double-cliquez sur SafeTrendBot_{tier}.exe
4. La licence s'activera automatiquement

⚠️ IMPORTANT:
- Ce build est à usage unique (1 PC uniquement)
- Gardez votre licence dans un endroit sûr
- En cas de réinstallation, contactez le support

Support: contact@safetrendbot.com

Merci pour votre achat!
SafeTrendBot Team
"""

        try:
            msg = f"Subject: {subject}\n\n{body}"
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(FROM_EMAIL, [to_email], msg.encode("utf-8"))
            print(f"   📧 Email envoyé à {to_email}")
            return True
        except Exception as e:
            print(f"   ❌ Email échoué: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # API Flask/FastAPI pour le webhook
    # ─────────────────────────────────────────────────────────────────────────

    def get_status(self, payment_id: str) -> dict:
        return self.payments.get(payment_id, {})


# ─────────────────────────────────────────────────────────────────────────────
# SERVEUR WEBHOOK (Flask)
# ─────────────────────────────────────────────────────────────────────────────

def run_webhook_server(port: int = 8080):
    """Démarre le serveur webhook pour recevoir les notifications NowPayments."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("❌ Flask manquant — pip install flask")
        sys.exit(1)

    app = Flask(__name__)
    tunnel = PaymentTunnel()

    @app.route("/webhook", methods=["POST"])
    def webhook():
        payload = request.get_json(force=True, silent=True) or {}
        signature = request.headers.get("x-nowpayments-sig", "")
        ok = tunnel.handle_webhook(payload, signature)
        return jsonify({"success": ok})

    @app.route("/pay", methods=["POST"])
    def create_payment():
        data = request.get_json(force=True, silent=True) or {}
        email = data.get("email", "")
        tier = data.get("tier", "basic")
        result = tunnel.create_payment_request(email, tier)
        return jsonify(result)

    @app.route("/status/<payment_id>", methods=["GET"])
    def status(payment_id):
        return jsonify(tunnel.get_status(payment_id))

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "payments": len(tunnel.payments)})

    print(f"🌐 Webhook server: http://0.0.0.0:{port}")
    print(f"   Webhook URL: http://217.160.191.107:{port}/webhook")
    print(f"   Create payment: POST http://217.160.191.107:{port}/pay")
    app.run(host="0.0.0.0", port=port)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SafeTrendBot Payment Tunnel")
    sub = parser.add_subparsers(dest="cmd")

    serve_p = sub.add_parser("serve", help="Démarrer le serveur webhook")
    serve_p.add_argument("--port", type=int, default=8080)

    test_p = sub.add_parser("test", help="Simuler un paiement (test)")
    test_p.add_argument("--email", required=True)
    test_p.add_argument("--tier", default="basic")

    status_p = sub.add_parser("status", help="Voir le statut d'un paiement")
    status_p.add_argument("--id", required=True)

    args = parser.parse_args()

    tunnel = PaymentTunnel()

    if args.cmd == "serve":
        run_webhook_server(args.port)
    elif args.cmd == "test":
        result = tunnel.create_payment_request(args.email, args.tier)
        print(json.dumps(result, indent=2))
        # Simuler confirmation
        if "payment_id" in result:
            tunnel.handle_webhook({
                "order_id": result["payment_id"],
                "payment_status": "finished",
            })
    elif args.cmd == "status":
        print(json.dumps(tunnel.get_status(args.id), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
