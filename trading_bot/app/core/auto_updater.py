"""
AutoUpdater — Mise à jour automatique des bots clients
=========================================================

Vérifie périodiquement si une nouvelle version est disponible
et met à jour automatiquement le bot client.

Le serveur admin publie un fichier VERSION avec:
    {
        "version": "5.3.1",
        "download_url": "https://.../patch_v5.3.1.zip",
        "changelog": "Bug fixes...",
        "mandatory": false
    }

Le bot vérifie au démarrage et toutes les 24h.
Si une mise à jour est disponible, il la télécharge et l'applique.

Usage dans main.py:
    from app.core.auto_updater import AutoUpdater
    updater = AutoUpdater(current_version="5.3.0")
    if updater.check_and_update():
        restart_bot()
"""

import sys
import os
import json
import hashlib
import shutil
import zipfile
import tempfile
import requests
from pathlib import Path
from typing import Optional, Dict


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

UPDATE_SERVER = os.environ.get("SAFETRENDBOT_UPDATE_URL", "")
VERSION_FILE = Path.home() / ".safetrendbot" / "version.json"
UPDATE_DIR = Path.home() / ".safetrendbot" / "updates"


class AutoUpdater:
    """Gestionnaire de mise à jour automatique."""

    def __init__(self, current_version: str, tier: str = "basic"):
        self.current_version = current_version
        self.tier = tier
        self.new_version: Optional[str] = None
        self.update_info: Optional[dict] = None

        UPDATE_DIR.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Vérification
    # ─────────────────────────────────────────────────────────────────────────

    def check_update(self) -> bool:
        """Vérifie si une mise à jour est disponible."""
        if not UPDATE_SERVER:
            return False

        try:
            resp = requests.get(
                f"{UPDATE_SERVER}/version.json",
                timeout=10,
                headers={"X-Bot-Tier": self.tier, "X-Bot-Version": self.current_version}
            )
            if resp.status_code == 200:
                data = resp.json()
                server_version = data.get("version", "")
                if self._is_newer(server_version, self.current_version):
                    self.new_version = server_version
                    self.update_info = data
                    return True
        except Exception:
            pass

        return False

    def _is_newer(self, new: str, current: str) -> bool:
        """Compare deux versions semver."""
        try:
            def parse(v):
                return [int(x) for x in v.split(".")]
            return parse(new) > parse(current)
        except ValueError:
            return new != current

    # ─────────────────────────────────────────────────────────────────────────
    # Téléchargement
    # ─────────────────────────────────────────────────────────────────────────

    def download_update(self) -> Optional[Path]:
        """Télécharge le patch de mise à jour."""
        if not self.update_info:
            return None

        url = self.update_info.get("download_url")
        if not url:
            return None

        try:
            print(f"📥 Téléchargement v{self.new_version}...")
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200:
                patch_file = UPDATE_DIR / f"patch_v{self.new_version}.zip"
                patch_file.write_bytes(resp.content)
                print(f"   ✅ Patch téléchargé: {patch_file}")
                return patch_file
        except Exception as e:
            print(f"   ❌ Échec téléchargement: {e}")

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Application
    # ─────────────────────────────────────────────────────────────────────────

    def apply_update(self, patch_file: Path) -> bool:
        """Applique le patch téléchargé."""
        try:
            print(f"🔧 Application du patch v{self.new_version}...")

            # Extraire dans un dossier temp
            temp_dir = UPDATE_DIR / f"extract_{self.new_version}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            with zipfile.ZipFile(patch_file, 'r') as zf:
                zf.extractall(temp_dir)

            # Vérifier checksum si fourni
            expected_hash = self.update_info.get("sha256", "")
            if expected_hash:
                actual_hash = hashlib.sha256(patch_file.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    print("   ❌ Checksum invalide! Mise à jour annulée.")
                    return False

            # Remplacer les fichiers (stratégie: backup + swap)
            self._replace_files(temp_dir)

            # Sauvegarder la nouvelle version
            VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            VERSION_FILE.write_text(json.dumps({
                "version": self.new_version,
                "updated_at": datetime.utcnow().isoformat(),
            }), encoding="utf-8")

            print(f"   ✅ Mise à jour v{self.new_version} appliquée!")
            print("   🔄 Redémarrage requis.")

            # Nettoyer
            patch_file.unlink(missing_ok=True)
            shutil.rmtree(temp_dir, ignore_errors=True)

            return True

        except Exception as e:
            print(f"   ❌ Échec application: {e}")
            return False

    def _replace_files(self, patch_dir: Path):
        """Remplace les fichiers du bot par ceux du patch."""
        bot_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else ROOT

        for src_file in patch_dir.rglob("*"):
            if src_file.is_file():
                rel = src_file.relative_to(patch_dir)
                dst = bot_dir / rel

                # Backup ancien fichier
                if dst.exists():
                    backup = dst.with_suffix(dst.suffix + ".backup")
                    shutil.copy2(dst, backup)

                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst)

    # ─────────────────────────────────────────────────────────────────────────
    # Full workflow
    # ─────────────────────────────────────────────────────────────────────────

    def check_and_update(self, force: bool = False) -> bool:
        """
        Vérifie et applique une mise à jour si disponible.
        Retourne True si une mise à jour a été appliquée (redémarrage nécessaire).
        """
        if not self.check_update():
            return False

        print(f"📢 Nouvelle version disponible: v{self.new_version}")
        print(f"   Actuelle: v{self.current_version}")
        print(f"   Changelog: {self.update_info.get('changelog', 'N/A')}")

        # Si mandatory, forcer la mise à jour
        if self.update_info.get("mandatory", False):
            print("   ⚠️ Cette mise à jour est OBLIGATOIRE.")
            force = True

        if not force:
            # En mode GUI, demander confirmation
            print("   Utilisez --update pour appliquer.")
            return False

        patch = self.download_update()
        if patch:
            return self.apply_update(patch)

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Version saved locally
    # ─────────────────────────────────────────────────────────────────────────

    def get_saved_version(self) -> str:
        """Lit la version sauvegardée localement."""
        if VERSION_FILE.exists():
            try:
                data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
                return data.get("version", self.current_version)
            except Exception:
                pass
        return self.current_version


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="5.3.0")
    parser.add_argument("--tier", default="basic")
    parser.add_argument("--check", action="store_true", help="Vérifier uniquement")
    parser.add_argument("--update", action="store_true", help="Appliquer si disponible")
    args = parser.parse_args()

    updater = AutoUpdater(args.version, args.tier)

    if args.check:
        if updater.check_update():
            print(f"📢 Mise à jour disponible: v{updater.new_version}")
        else:
            print("✅ À jour.")
    elif args.update:
        ok = updater.check_and_update(force=True)
        if ok:
            print("🔄 Mise à jour appliquée. Redémarrez le bot.")
        else:
            print("Pas de mise à jour ou échec.")
    else:
        parser.print_help()


if __name__ == "__main__":
    from datetime import datetime
    main()
