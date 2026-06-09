"""
RemoteAdmin — Gestion à distance de SafeTrendBot V5
====================================================

Bot Telegram privé pour l'administrateur.
Permet de gérer les licences, les clients et les paiements
depuis n'importe où, depuis son téléphone.

Commandes admin:
    /start          → Menu principal
    /status         → Statistiques globales
    /clients        → Liste des clients actifs
    /pending        → Paiements en attente
    /revoke KEY     → Révoquer une licence
    /confirm ID     → Confirmer un paiement + générer licence
    /newpayment     → Créer une demande de paiement
    /broadcast      → Envoyer un message à tous les clients

Configuration:
    Exportez ces variables d'environnement:
    export SAFETRENDBOT_ADMIN_BOT_TOKEN="123456:ABC..."
    export SAFETRENDBOT_ADMIN_CHAT_ID="123456789"

⚠️  SEUL l'admin peut utiliser ce bot.
    Le chat_id est vérifié à chaque commande.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  python-telegram-bot manquant — pip install python-telegram-bot")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ADMIN_BOT_TOKEN = os.environ.get("SAFETRENDBOT_ADMIN_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("SAFETRENDBOT_ADMIN_CHAT_ID", "")

# Fichiers de données
LICENSES_FILE = Path("licenses.json")
PAYMENTS_FILE = Path("payments.json")


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICATION ADMIN
# ─────────────────────────────────────────────────────────────────────────────

def is_admin(update: Update) -> bool:
    """Vérifie que l'utilisateur est bien l'admin."""
    if not ADMIN_CHAT_ID:
        return True  # Mode dev
    user_id = str(update.effective_user.id)
    return user_id == ADMIN_CHAT_ID


async def check_admin(update: Update) -> bool:
    """Vérifie et avertit si non-admin."""
    if not is_admin(update):
        await update.message.reply_text("🚫 Accès refusé. Ce bot est réservé à l'administrateur.")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDES
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    welcome = (
        "🔐 *SafeTrendBot Remote Admin*\n\n"
        "Bienvenue dans le panneau de contrôle.\n"
        "Gérez vos licences et clients à distance.\n\n"
        "*Commandes:*\n"
        "📊 `/status` — Statistiques\n"
        "👥 `/clients` — Clients actifs\n"
        "⏳ `/pending` — Paiements en attente\n"
        "🚫 `/revoke KEY` — Révoquer licence\n"
        "✅ `/confirm ID` — Confirmer paiement\n"
        "💰 `/newpayment EMAIL TIER` — Nouveau client\n"
        "📢 `/broadcast MSG` — Message global\n"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    # Stats licences
    licenses = load_licenses()
    total = len(licenses)
    used = sum(1 for v in licenses.values() if v.get("used"))
    available = total - used

    # Stats paiements
    payments = load_payments()
    pending = sum(1 for v in payments.values() if v.get("status") == "pending")
    confirmed = sum(1 for v in payments.values() if v.get("status") == "confirmed")

    msg = (
        "📊 *Statistiques SafeTrendBot*\n\n"
        f"*Licences:*\n"
        f"   Total: `{total}`\n"
        f"   Utilisées: `{used}`\n"
        f"   Disponibles: `{available}`\n\n"
        f"*Paiements:*\n"
        f"   En attente: `{pending}`\n"
        f"   Confirmés: `{confirmed}`\n\n"
        f"_Mis à jour: {datetime.now().strftime('%H:%M')}_"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    licenses = load_licenses()
    active = [v for v in licenses.values() if v.get("used")]

    if not active:
        await update.message.reply_text("👥 Aucun client actif pour le moment.")
        return

    msg = f"👥 *Clients actifs ({len(active)})*\n\n"
    for lic in active[:20]:  # Max 20 pour éviter message trop long
        hw = lic.get("hardware_id", "?")[:12]
        date = lic.get("used_at", "?")[:10]
        msg += f"• `{lic['key']}` | HW: `{hw}...` | {date}\n"

    if len(active) > 20:
        msg += f"\n... et {len(active) - 20} autres"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    payments = load_payments()
    pending = [v for v in payments.values() if v.get("status") == "pending"]

    if not pending:
        await update.message.reply_text("⏳ Aucun paiement en attente.")
        return

    msg = f"⏳ *Paiements en attente ({len(pending)})*\n\n"
    for p in pending:
        msg += (
            f"ID: `{p['id']}`\n"
            f"   Client: `{p['email']}`\n"
            f"   Montant: `{p['amount_crypto']} {p['currency']}`\n"
            f"   Adresse: `{p['address']}`\n"
            f"   Tier: `{p['tier']}`\n\n"
            f"   _Confirmer: `/confirm {p['id']} XXXX-XXXX`_\n\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/revoke XXXX-XXXX-XXXX-XXXX`")
        return

    license_key = context.args[0]
    licenses = load_licenses()

    if license_key not in licenses:
        await update.message.reply_text(f"❌ Licence introuvable: `{license_key}`")
        return

    licenses[license_key]["revoked"] = True
    save_licenses(licenses)

    await update.message.reply_text(
        f"🚫 *Licence révoquée*\n\n"
        f"`{license_key}`\n\n"
        f"Le client ne pourra plus utiliser le bot.\n"
        f"Prochain lancement = blocage.",
        parse_mode="Markdown"
    )


async def cmd_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/confirm ID_LICENCE KEY`")
        return

    payment_id = context.args[0]
    license_key = context.args[1]

    # Importer crypto_payment pour confirmation
    try:
        from crypto_payment import confirm_payment
        ok = confirm_payment(payment_id, license_key)
        if ok:
            await update.message.reply_text(
                f"✅ *Paiement confirmé*\n\n"
                f"ID: `{payment_id}`\n"
                f"Licence: `{license_key}`\n\n"
                f"→ Générez le build avec cette licence\n"
                f"→ Envoyez au client",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Échec confirmation")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {e}")


async def cmd_newpayment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/newpayment email@example.com basic|pro|extreme`")
        return

    email = context.args[0]
    tier = context.args[1]

    try:
        from crypto_payment import create_payment_request
        payment = create_payment_request(email, tier)

        await update.message.reply_text(
            f"💰 *Nouveau paiement créé*\n\n"
            f"Client: `{email}`\n"
            f"Tier: `{tier}`\n"
            f"ID: `{payment.id}`\n"
            f"Adresse: `{payment.address}`\n"
            f"Montant: `{payment.amount_crypto} {payment.currency}`\n\n"
            f"→ Envoyez les instructions au client",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur: {e}")


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/broadcast Votre message ici`")
        return

    message = " ".join(context.args)

    # Enregistrer le broadcast pour que les clients le voient
    broadcast_file = Path("broadcast.msg")
    broadcast_file.write_text(message, encoding="utf-8")

    await update.message.reply_text(
        f"📢 *Message broadcast enregistré*\n\n"
        f"`{message}`\n\n"
        f"Les clients verront ce message au prochain lancement.",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────

def load_licenses() -> dict:
    if LICENSES_FILE.exists():
        return json.loads(LICENSES_FILE.read_text(encoding="utf-8"))
    return {}


def save_licenses(data: dict):
    LICENSES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_payments() -> dict:
    if PAYMENTS_FILE.exists():
        return json.loads(PAYMENTS_FILE.read_text(encoding="utf-8"))
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot requis: pip install python-telegram-bot")
        sys.exit(1)

    if not ADMIN_BOT_TOKEN:
        print("❌ SAFETRENDBOT_ADMIN_BOT_TOKEN manquant")
        print("   export SAFETRENDBOT_ADMIN_BOT_TOKEN='123456:ABC...'")
        sys.exit(1)

    print("🔐 Démarrage RemoteAdmin SafeTrendBot...")
    print(f"   Token: {ADMIN_BOT_TOKEN[:15]}...")
    print(f"   Admin Chat ID: {ADMIN_CHAT_ID or 'ANY (dev mode)'}")

    app = Application.builder().token(ADMIN_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("clients", cmd_clients))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("revoke", cmd_revoke))
    app.add_handler(CommandHandler("confirm", cmd_confirm))
    app.add_handler(CommandHandler("newpayment", cmd_newpayment))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))

    print("✅ Bot admin prêt!")
    print("   Envoie /start à ton bot Telegram pour commencer.")

    app.run_polling()


if __name__ == "__main__":
    main()
