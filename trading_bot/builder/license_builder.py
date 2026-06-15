"""
SafeTrendBot License Builder — Générateur de builds protégés
============================================================
Cet outil génère des versions protégées du bot pour distribution.

FONCTIONNEMENT:
1. Génère une clé de licence unique
2. Compile le code avec Cython (obfuscation)
3. Pack avec PyArmor ou PyInstaller (binaire)
4. Injecte la clé dans le binaire
5. Crée un installeur protégé

⚠️ CET OUTIL EST POUR USAGE INTERNE — NE PAS DISTRIBUER AUX CLIENTS
"""

import sys
import os
import re
import json
import hashlib
import hmac
import secrets
import string
import zipfile
import tarfile
import shutil
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = "5.3.0"
PROJECT_ROOT = Path(__file__).parent.parent
BUILD_OUTPUT = PROJECT_ROOT / "builds"
RELEASES_DIR = PROJECT_ROOT / "releases"

@dataclass
class BuildConfig:
    """Configuration pour un build."""
    version: str = VERSION
    platform: str = "windows"  # windows, linux, macos
    license_key: str = ""      # Clé générée
    expiry_days: Optional[int] = None  # None = illimité
    email: str = ""
    obfuscate: bool = True
    compile_cython: bool = True
    pyarmor: bool = True
    output_name: str = ""
    
    def __post_init__(self):
        if not self.output_name:
            self.output_name = f"SafeTrendBot-{self.version}-{self.platform}-x64"


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE KEY GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class LicenseGenerator:
    """Génère des clés de licence sécurisées."""
    
    # Clé secrète maître pour signer les licences (remplacer en prod!)
    MASTER_KEY = "SafeTrendBot_MasterKey_2024_ChangeMe!"
    
    @staticmethod
    def generate_key(prefix: str = "STB5") -> str:
        """Génère une clé au format STB5-XXXX-XXXX-XXXX."""
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('O', '').replace('I', '').replace('L', '')  # Éviter confusion
        
        parts = []
        for _ in range(3):
            part = ''.join(secrets.choice(chars) for _ in range(4))
            parts.append(part)
        
        return f"{prefix}-{'-'.join(parts)}"
    
    @classmethod
    def create_license(cls, key: str, email: str = "", 
                      expiry_days: Optional[int] = None,
                      hw_bind: bool = True) -> Dict:
        """Crée un payload de licence signé."""
        import base64
        
        payload = {
            "key": key,
            "email": email,
            "created": datetime.now().isoformat(),
            "hw_bind": hw_bind,
            "version_min": VERSION,
        }
        
        if expiry_days:
            payload["expires"] = (datetime.now() + timedelta(days=expiry_days)).isoformat()
        
        # Signer le payload
        msg = json.dumps(payload, sort_keys=True)
        sig = hmac.new(
            cls.MASTER_KEY.encode(),
            msg.encode(),
            hashlib.sha3_512
        ).hexdigest()[:64]
        
        payload["sig"] = sig
        
        # Encoder pour injection
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        
        return {
            "payload": payload,
            "encoded": encoded,
            "sig": sig
        }
    
    @classmethod
    def verify_key_format(cls, key: str) -> bool:
        """Vérifie le format de clé."""
        pattern = r"^STB5-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        return bool(re.match(pattern, key, re.I))
    
    @classmethod
    def revoke_key(cls, key: str) -> str:
        """Génère une révocation pour une clé (pour blacklist server)."""
        msg = f"REVOKE:{key}:{datetime.now().isoformat()}"
        sig = hashlib.sha3_256(msg.encode()).hexdigest()
        return sig


# ═══════════════════════════════════════════════════════════════════════════════
# CODE OBFUSCATOR
# ═══════════════════════════════════════════════════════════════════════════════

class CodeObfuscator:
    """Obfusque le code Python avant compilation."""
    
    CRITICAL_MODULES = [
        "app/core/license_manager.py",
        "app/core/trading_engine.py",
        "app/core/anti_tamper.py",
    ]
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def obfuscate_pyarmor(self, output_dir: Path) -> bool:
        """Obfusque avec PyArmor."""
        print("  → PyArmor obfuscation...")
        
        # Modules à obfusquer
        modules = " ".join(self.CRITICAL_MODULES)
        
        cmd = f'pyarmor gen --output "{output_dir}" {modules}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"    ⚠️ PyArmor erreur: {result.stderr}")
            return False
        
        print("    ✅ PyArmor OK")
        return True
    
    def compile_cython(self, output_dir: Path) -> bool:
        """Compile les modules critiques avec Cython."""
        print("  → Cython compilation...")
        
        # Créer setup.py temporaire
        setup_content = '''
from setuptools import setup
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import os

modules = [
    "app/core/license_manager.py",
    "app/core/trading_engine.py",
]

setup(
    name="SafeTrendBot_Critical",
    ext_modules=cythonize(
        modules,
        compiler_directives={
            'language_level': "3",
            'embedsignature': False,
            'boundscheck': False,
            'wraparound': False,
            'cdivision': True,
        },
        annotate=False,
    ),
    cmdclass={'build_ext': build_ext},
)
'''
        setup_file = self.project_root / "setup_build.py"
        setup_file.write_text(setup_content)
        
        try:
            # Build
            result = subprocess.run(
                [sys.executable, "setup_build.py", "build_ext", "--inplace"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("    ✅ Cython OK")
                return True
            else:
                print(f"    ⚠️ Cython: {result.stderr[:200]}")
                return False
        finally:
            if setup_file.exists():
                setup_file.unlink()
    
    def rename_imports(self, file_path: Path):
        """Renomme les imports pour compliquer le reverse engineering."""
        content = file_path.read_text()
        
        # Remplacer imports explicites
        replacements = {
            "from license_manager import": "from ._lm import",
            "import license_manager": "import ._lm as license_manager",
            "from trading_engine import": "from ._te import",
            "import trading_engine": "import ._te as trading_engine",
        }
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        file_path.write_text(content)


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD PACKAGER
# ═══════════════════════════════════════════════════════════════════════════════

class BuildPackager:
    """Crée le package final (exécutable)."""
    
    def __init__(self, project_root: Path, config: BuildConfig):
        self.project_root = project_root
        self.config = config
        self.work_dir: Optional[Path] = None
    
    def prepare(self) -> bool:
        """Prépare l'environnement de build."""
        print(f"\n{'='*60}")
        print(f"  Build: {self.config.output_name}")
        print(f"  Plateforme: {self.config.platform}")
        print(f"{'='*60}\n")
        
        # Créer répertoire de travail
        self.work_dir = BUILD_OUTPUT / f"tmp_{int(time.time())}"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Copier les sources
        print("  → Copie des sources...")
        shutil.copytree(
            self.project_root / "app",
            self.work_dir / "app",
            dirs_exist_ok=True
        )
        
        # Copier les scripts principaux
        for f in ["main.py", "headless.py"]:
            src = self.project_root / f
            if src.exists():
                shutil.copy(src, self.work_dir / f)
        
        # Copier requirements.txt
        req = self.project_root / "requirements.txt"
        if req.exists():
            shutil.copy(req, self.work_dir / "requirements.txt")
        
        # Injecter la licence
        self._inject_license()
        
        print("    ✅ Préparation OK")
        return True
    
    def _inject_license(self):
        """Injecte la clé de licence dans le code."""
        print("  → Injection licence...")
        
        # Lire le license_manager
        lm_file = self.work_dir / "app" / "core" / "license_manager.py"
        if not lm_file.exists():
            print("    ⚠️ license_manager.py non trouvé")
            return
        
        content = lm_file.read_text()
        
        # Remplacer les placeholders
        content = content.replace(
            '__LICENSE_SIG__',
            self.config.license_key
        )
        
        if self.config.expiry_days:
            expiry = (datetime.now() + timedelta(days=self.config.expiry_days)).isoformat()
            content = content.replace(
                '__LICENSE_EXPIRY__',
                f'"{expiry}"'
            )
        else:
            content = content.replace(
                '__LICENSE_EXPIRY__',
                'None'
            )
        
        lm_file.write_text(content)
        
        print(f"    ✅ Clé injectée: {self.config.license_key}")
    
    def build_pyinstaller(self) -> Optional[Path]:
        """Build avec PyInstaller."""
        print("  → Build PyInstaller...")
        
        if not self.work_dir:
            return None
        
        # Créer spec file
        spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{self.work_dir / "main.py"}'],
    pathex=['{self.work_dir}'],
    binaries=[],
    datas=[
        ('{self.work_dir / "app"}', 'app'),
    ],
    hiddenimports=[
        'MetaTrader5',
        'MetaTrader5.x64',
        'pandas',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={{}},
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.config.output_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{self.project_root / "assets" / "icon.ico"}',
)
'''
        spec_file = self.work_dir / f"{self.config.output_name}.spec"
        spec_file.write_text(spec_content)
        
        # Lancer PyInstaller
        result = subprocess.run(
            [
                "pyinstaller",
                str(spec_file),
                "--distpath", str(BUILD_OUTPUT),
                "--workpath", str(BUILD_OUTPUT / "build"),
                "--noconfirm",
            ],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            output = BUILD_OUTPUT / self.config.output_name
            if self.config.platform == "windows":
                output = BUILD_OUTPUT / f"{self.config.output_name}.exe"
            
            print(f"    ✅ Build OK: {output}")
            return output
        else:
            print(f"    ❌ Erreur: {result.stderr[:500]}")
            return None
    
    def cleanup(self):
        """Nettoie les fichiers temporaires."""
        if self.work_dir and self.work_dir.exists():
            shutil.rmtree(self.work_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════════
# LICENSE MANAGER DB (Pour tracking des licences)
# ═══════════════════════════════════════════════════════════════════════════════

class LicenseDatabase:
    """Gère la base de données des licences générées."""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (PROJECT_ROOT / "licenses_generated.json")
        self.licenses: Dict[str, dict] = {}
        self._load()
    
    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path) as f:
                    self.licenses = json.load(f)
            except:
                self.licenses = {}
    
    def _save(self):
        with open(self.db_path, "w") as f:
            json.dump(self.licenses, f, indent=2)
    
    def add(self, key: str, email: str = "", expiry_days: Optional[int] = None,
            build_info: dict = None):
        """Ajoute une licence à la DB."""
        self.licenses[key] = {
            "email": email,
            "created": datetime.now().isoformat(),
            "expiry_days": expiry_days,
            "expires": (datetime.now() + timedelta(days=expiry_days)).isoformat() if expiry_days else None,
            "build_info": build_info or {},
            "revoked": False,
            "activations": [],
        }
        self._save()
    
    def revoke(self, key: str):
        """Révoque une licence."""
        if key in self.licenses:
            self.licenses[key]["revoked"] = True
            self.licenses[key]["revoked_at"] = datetime.now().isoformat()
            self._save()
    
    def add_activation(self, key: str, hw_id: str, machine_info: dict):
        """Note une activation."""
        if key in self.licenses:
            self.licenses[key]["activations"].append({
                "hw_id": hw_id,
                "machine": machine_info,
                "at": datetime.now().isoformat(),
            })
            self._save()
    
    def get(self, key: str) -> Optional[dict]:
        return self.licenses.get(key)
    
    def list_all(self) -> List[dict]:
        return [
            {"key": k, **v}
            for k, v in self.licenses.items()
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BUILDER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class SafeTrendBotBuilder:
    """
    Classe principale du Builder.
    Orchestre la génération de builds protégés.
    """
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or PROJECT_ROOT
        self.license_db = LicenseDatabase()
        self.obfuscator = CodeObfuscator(self.project_root)
        
        # Préparer les répertoires
        BUILD_OUTPUT.mkdir(parents=True, exist_ok=True)
        RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    
    def build(self, config: BuildConfig) -> Tuple[bool, str]:
        """
        Génère un build complet.
        
        Returns: (success, message)
        """
        import time
        
        start_time = time.time()
        
        # 1. Générer clé si non fournie
        if not config.license_key:
            config.license_key = LicenseGenerator.generate_key()
        
        # Valider clé
        if not LicenseGenerator.verify_key_format(config.license_key):
            return False, f"Format de clé invalide: {config.license_key}"
        
        # 2. Créer licence signée
        license_data = LicenseGenerator.create_license(
            config.license_key,
            email=config.email,
            expiry_days=config.expiry_days
        )
        
        print(f"\n🔑 Licence: {config.license_key}")
        print(f"   Email: {config.email or 'N/A'}")
        if config.expiry_days:
            print(f"   Expire: {license_data['payload']['expires']}")
        
        # 3. Enregistrer dans la DB
        self.license_db.add(
            config.license_key,
            email=config.email,
            expiry_days=config.expiry_days,
            build_info={
                "version": config.version,
                "platform": config.platform,
                "output": config.output_name,
            }
        )
        
        # 4. Préparer le build
        packager = BuildPackager(self.project_root, config)
        
        if not packager.prepare():
            return False, "Erreur préparation"
        
        # 5. Obfusquer si demandé
        if config.obfuscate:
            if config.pyarmor:
                self.obfuscator.obfuscate_pyarmor(packager.work_dir)
            if config.compile_cython:
                self.obfuscator.compile_cython(packager.work_dir)
        
        # 6. Build PyInstaller
        output = packager.build_pyinstaller()
        packager.cleanup()
        
        if output:
            elapsed = time.time() - start_time
            print(f"\n✅ BUILD COMPLET en {elapsed:.1f}s")
            print(f"   Output: {output}")
            print(f"   Licence: {config.license_key}")
            
            return True, str(output)
        else:
            return False, "Build PyInstaller échoué"
    
    def build_batch(self, count: int, email_prefix: str = "client",
                   expiry_days: Optional[int] = None,
                   platform: str = "windows") -> List[dict]:
        """Génère plusieurs builds d'un coup."""
        results = []
        
        for i in range(count):
            print(f"\n{'='*50}")
            print(f"  Build {i+1}/{count}")
            print(f"{'='*50}")
            
            key = LicenseGenerator.generate_key()
            email = f"{email_prefix}{i+1}@example.com"
            
            config = BuildConfig(
                license_key=key,
                email=email,
                expiry_days=expiry_days,
                platform=platform,
                output_name=f"SafeTrendBot-{VERSION}-{platform}-x64-{i+1:03d}"
            )
            
            success, msg = self.build(config)
            results.append({
                "key": key,
                "email": email,
                "success": success,
                "output": msg
            })
            
            # Pause entre builds
            if i < count - 1:
                time.sleep(1)
        
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Interface CLI pour le builder."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SafeTrendBot License Builder")
    subparsers = parser.add_subparsers(dest="command", help="Commandes")
    
    # Commande: generate-key
    key_parser = subparsers.add_parser("generate-key", help="Génère une clé")
    key_parser.add_argument("-n", "--count", type=int, default=1, help="Nombre de clés")
    key_parser.add_argument("--prefix", default="STB5", help="Préfixe")
    
    # Commande: build
    build_parser = subparsers.add_parser("build", help="Génère un build")
    build_parser.add_argument("-k", "--key", help="Clé de licence")
    build_parser.add_argument("-e", "--email", default="", help="Email client")
    build_parser.add_argument("--days", type=int, help="Jours avant expiration")
    build_parser.add_argument("-p", "--platform", default="windows", 
                             choices=["windows", "linux", "macos"],
                             help="Plateforme cible")
    
    # Commande: batch
    batch_parser = subparsers.add_parser("batch", help="Génère plusieurs builds")
    batch_parser.add_argument("-n", "--count", type=int, default=10, help="Nombre")
    batch_parser.add_argument("--email-prefix", default="client", help="Préfixe email")
    batch_parser.add_argument("--days", type=int, help="Jours avant expiration")
    batch_parser.add_argument("-p", "--platform", default="windows")
    
    # Commande: list
    list_parser = subparsers.add_parser("list", help="Liste les licences")
    
    # Commande: revoke
    revoke_parser = subparsers.add_parser("revoke", help="Révoque une licence")
    revoke_parser.add_argument("key", help="Clé à révoquer")
    
    args = parser.parse_args()
    
    builder = SafeTrendBotBuilder()
    
    if args.command == "generate-key":
        for _ in range(args.count):
            key = LicenseGenerator.generate_key(args.prefix)
            print(key)
    
    elif args.command == "build":
        config = BuildConfig(
            license_key=args.key or LicenseGenerator.generate_key(),
            email=args.email,
            expiry_days=args.days,
            platform=args.platform
        )
        success, msg = builder.build(config)
        print(f"\n{'✅' if success else '❌'} {msg}")
        sys.exit(0 if success else 1)
    
    elif args.command == "batch":
        results = builder.build_batch(
            count=args.count,
            email_prefix=args.email_prefix,
            expiry_days=args.days,
            platform=args.platform
        )
        
        # Résumé
        success_count = sum(1 for r in results if r["success"])
        print(f"\n{'='*50}")
        print(f"  RÉSULTAT: {success_count}/{args.count} builds réussis")
        print(f"{'='*50}")
        
        # Sauvegarder CSV
        csv_file = RELEASES_DIR / f"licenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_file, "w") as f:
            f.write("key,email,success,output\n")
            for r in results:
                f.write(f'{r["key"]},{r["email"]},{r["success"]},{r["output"]}\n')
        print(f"  CSV: {csv_file}")
    
    elif args.command == "list":
        licenses = builder.license_db.list_all()
        print(f"\n📋 {len(licenses)} licence(s)")
        for lic in licenses:
            status = "✅" if not lic.get("revoked") else "❌ RÉVOQUÉE"
            exp = lic.get("expires", "Jamais")
            print(f"  {status} {lic['key']} | {lic['email']} | Expire: {exp}")
    
    elif args.command == "revoke":
        builder.license_db.revoke(args.key)
        sig = LicenseGenerator.revoke_key(args.key)
        print(f"✅ Clé révoquée: {args.key}")
        print(f"   Signature révocation: {sig}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()