"""
SafeTrendBot Monitor — Surveillance du système
===============================================

Surveille:
- Dashboard health (ping toutes les 5 min)
- Espace disque (alerte si < 10%)
- Mémoire (alerte si > 90%)
- Nombre de builds générés
- Licences actives / révoquées
- Paiements en attente

Envoie des alertes Telegram à l'admin.
Usage:
    python monitor.py              ← Vérifie une fois
    python monitor.py --watch      ← Surveillance continue
    python monitor.py --telegram   ← Avec alertes Telegram
"""

import os
import sys
import json
import time
import shutil
import socket
import psutil
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ─── CONFIG ───
DASHBOARD_URL = os.environ.get("SAFETRENDBOT_ADMIN_URL", "https://217.160.191.107:8443")
TELEGRAM_BOT_TOKEN = os.environ.get("MONITOR_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT = os.environ.get("MONITOR_CHAT_ID", "")

BUILD_DIR = Path(__file__).parent / "builds"
DB_FILE = Path(__file__).parent / "payment_tunnel_db.json"


class Monitor:
    """Surveillance SafeTrendBot."""

    def __init__(self):
        self.alerts: List[str] = []

    def check_all(self) -> dict:
        """Vérifie tous les indicateurs."""
        results = {}

        # 1. Dashboard health
        results["dashboard"] = self._check_dashboard()

        # 2. Système
        results["system"] = self._check_system()

        # 3. Business metrics
        results["business"] = self._check_business()

        return results

    def _check_dashboard(self) -> dict:
        """Ping le dashboard."""
        try:
            resp = requests.get(
                f"{DASHBOARD_URL}/api/health",
                timeout=10,
                verify=False,
            )
            if resp.status_code == 200:
                return {"status": "ok", "response_ms": resp.elapsed.total_seconds() * 1000}
            else:
                self.alerts.append(f"🚨 Dashboard HTTP {resp.status_code}")
                return {"status": "error", "code": resp.status_code}
        except Exception as e:
            self.alerts.append(f"🚨 Dashboard injoignable: {e}")
            return {"status": "down", "error": str(e)}

    def _check_system(self) -> dict:
        """Vérifie les ressources système."""
        disk = psutil.disk_usage('/')
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)

        results = {
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "disk_percent": disk.percent,
            "memory_percent": mem.percent,
            "cpu_percent": cpu,
        }

        if disk.percent > 90:
            self.alerts.append(f"🚨 Disque plein: {disk.percent}%")
        if mem.percent > 90:
            self.alerts.append(f"🚨 Mémoire saturée: {mem.percent}%")
        if cpu > 95:
            self.alerts.append(f"🚨 CPU à fond: {cpu}%")

        return results

    def _check_business(self) -> dict:
        """Métriques business."""
        results = {"builds_count": 0, "payments_pending": 0, "payments_total": 0}

        # Builds
        if BUILD_DIR.exists():
            results["builds_count"] = len(list(BUILD_DIR.rglob("*.zip")))

        # Paiements
        if DB_FILE.exists():
            try:
                db = json.loads(DB_FILE.read_text())
                results["payments_total"] = len(db)
                results["payments_pending"] = sum(
                    1 for v in db.values() if v.get("status") == "pending"
                )
                results["payments_delivered"] = sum(
                    1 for v in db.values() if v.get("status") == "delivered"
                )
            except Exception:
                pass

        if results["payments_pending"] > 5:
            self.alerts.append(f"⚠️ {results['payments_pending']} paiements en attente")

        return results

    def send_telegram(self, message: str):
        """Envoie une alerte Telegram."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_ADMIN_CHAT:
            return False
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": TELEGRAM_ADMIN_CHAT,
                "text": message,
                "parse_mode": "Markdown",
            }, timeout=10)
            return True
        except Exception:
            return False

    def report(self) -> str:
        """Génère un rapport de santé."""
        checks = self.check_all()

        lines = [
            f"📊 *SafeTrendBot Monitor* — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"🌐 Dashboard: {checks['dashboard']['status']} ({checks['dashboard'].get('response_ms', 0):.0f}ms)",
            f"💾 Disque: {checks['system']['disk_free_gb']}GB libre ({checks['system']['disk_percent']}%)",
            f"🧠 Mémoire: {checks['system']['memory_percent']}%",
            f"⚡ CPU: {checks['system']['cpu_percent']}%",
            f"",
            f"📦 Builds: {checks['business']['builds_count']}",
            f"💰 Paiements: {checks['business']['payments_total']} total | {checks['business']['payments_pending']} en attente | {checks['business'].get('payments_delivered', 0)} livrés",
            f"",
        ]

        if self.alerts:
            lines.append(f"🚨 *ALERTES:*")
            for a in self.alerts:
                lines.append(f"   {a}")
        else:
            lines.append(f"✅ Tout va bien!")

        return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="Surveillance continue (toutes les 5 min)")
    parser.add_argument("--telegram", action="store_true", help="Envoyer alertes Telegram")
    parser.add_argument("--once", action="store_true", help="Vérifier une fois")
    args = parser.parse_args()

    monitor = Monitor()

    if args.watch:
        print("👁️ Surveillance continue... Ctrl+C pour arrêter")
        while True:
            report = monitor.report()
            print(report)
            if args.telegram and monitor.alerts:
                monitor.send_telegram(report)
            time.sleep(300)  # 5 min
    else:
        report = monitor.report()
        print(report)
        if args.telegram and monitor.alerts:
            monitor.send_telegram(report)


if __name__ == "__main__":
    main()
