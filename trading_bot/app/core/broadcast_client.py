"""
Broadcast Client — Réception des messages admin sur le bot client
==================================================================

Ce module permet au bot SafeTrendBot de recevoir les messages
broadcast envoyés par l'admin via le dashboard.

Deux modes de fonctionnement:
1. Online: requête HTTP vers le serveur d'activation
2. Offline: lecture d'un fichier local de broadcast

Les messages s'affichent dans l'UI du bot au démarrage
et dans la barre de statut.

Usage dans main.py:
    from app.core.broadcast_client import BroadcastClient
    bc = BroadcastClient()
    messages = bc.get_active_broadcasts()
    for msg in messages:
        show_notification(msg)
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

BROADCAST_LOCAL_FILE = Path.home() / ".safetrendbot" / "broadcasts.json"
BROADCAST_API_URL = os.environ.get("SAFETRENDBOT_BROADCAST_API", "")


class BroadcastClient:
    """Client pour récupérer les messages broadcast de l'admin."""

    def __init__(self, tier: str = "basic"):
        self.tier = tier
        BROADCAST_LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)

    def get_active_broadcasts(self) -> List[str]:
        """Récupère les messages broadcast actifs pour ce tier."""
        messages = []

        # 1. Essayer online (si serveur configuré)
        if BROADCAST_API_URL:
            try:
                online = self._fetch_online()
                if online:
                    messages.extend(online)
            except Exception:
                pass

        # 2. Fallback offline (fichier local)
        local = self._fetch_local()
        if local:
            messages.extend(local)

        return messages

    def _fetch_online(self) -> List[str]:
        """Récupère depuis l'API du dashboard admin."""
        try:
            resp = requests.get(
                f"{BROADCAST_API_URL}/api/broadcasts",
                timeout=5,
                headers={"X-Bot-Tier": self.tier}
            )
            if resp.status_code == 200:
                data = resp.json()
                return [b["message"] for b in data if b.get("active")]
        except Exception:
            pass
        return []

    def _fetch_local(self) -> List[str]:
        """Récupère depuis le fichier local."""
        if not BROADCAST_LOCAL_FILE.exists():
            return []
        try:
            data = json.loads(BROADCAST_LOCAL_FILE.read_text(encoding="utf-8"))
            broadcasts = data.get("broadcasts", [])
            # Filtrer par tier et actifs
            active = [b for b in broadcasts if b.get("active") and
                      (b.get("target_tier") == "all" or b.get("target_tier") == self.tier)]
            return [b["message"] for b in active]
        except Exception:
            return []

    def save_local_broadcasts(self, broadcasts: List[dict]):
        """Sauvegarde des broadcasts locaux (injectés au build)."""
        data = {"broadcasts": broadcasts, "updated_at": datetime.utcnow().isoformat()}
        BROADCAST_LOCAL_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def show_notification(self, message: str, title: str = "📢 Message Admin"):
        """Affiche une notification dans le bot (PyQt ou console)."""
        # En mode PyQt
        try:
            from PyQt6.QtWidgets import QMessageBox
            # Ne pas bloquer le démarrage
            print(f"\n{'='*50}")
            print(f"{title}")
            print(f"{'='*50}")
            print(message)
            print(f"{'='*50}\n")
        except ImportError:
            # Mode console
            print(f"\n{'='*50}")
            print(f"{title}")
            print(f"{'='*50}")
            print(message)
            print(f"{'='*50}\n")


def check_broadcasts_at_startup(tier: str = "basic"):
    """
    Vérifie et affiche les broadcasts au démarrage du bot.
    À appeler dans main.py au lancement.
    """
    bc = BroadcastClient(tier)
    messages = bc.get_active_broadcasts()
    if messages:
        for msg in messages:
            bc.show_notification(msg)
    return messages


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", default="basic")
    parser.add_argument("--save", help="Sauvegarder un message local")
    args = parser.parse_args()

    bc = BroadcastClient(args.tier)

    if args.save:
        bc.save_local_broadcasts([{"message": args.save, "active": True, "target_tier": "all"}])
        print("✅ Message sauvegardé")
    else:
        msgs = bc.get_active_broadcasts()
        if msgs:
            for m in msgs:
                print(f"📢 {m}")
        else:
            print("Aucun message broadcast actif.")


if __name__ == "__main__":
    main()
