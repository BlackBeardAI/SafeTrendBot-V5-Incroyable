"""
Anti-Tamper — détecte les modifications du code et les tentatives de reverse engineering.
"""
import hashlib
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime


class AntiTamper:
    """
    Protège contre :
    - Modification des fichiers sources
    - Debuggers (gdb, windbg)
    - VMs / sandboxes
    - Hooking de fonctions
    """

    # Fichiers critiques à protéger
    PROTECTED_FILES = [
        "app/core/trading_engine_v4.py",
        "app/core/license_manager.py",
        "app/core/strategies.py",
        "main.py",
    ]

    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or Path(__file__).parent.parent.parent
        self._expected_hashes: Dict[str, str] = {}
        self._debugger_detected = False
        self._vm_detected = False

    # ========================================================================
    # FILE INTEGRITY CHECK
    # ========================================================================

    def compute_file_hash(self, filepath: Path) -> str:
        """Hash SHA-256 d'un fichier"""
        h = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    def save_baseline(self, manifest_path: Optional[Path] = None):
        """Sauvegarde les hashes de référence (à faire au build)"""
        manifest = manifest_path or self.root / "manifest.json"
        hashes = {}
        for rel_path in self.PROTECTED_FILES:
            full_path = self.root / rel_path
            if full_path.exists():
                hashes[rel_path] = self.compute_file_hash(full_path)
        import json
        manifest.write_text(json.dumps({
            "version": "5.0.0",
            "generated": datetime.utcnow().isoformat(),
            "files": hashes,
        }, indent=2))
        return hashes

    def verify_integrity(self) -> bool:
        """Vérifie que les fichiers n'ont pas été modifiés"""
        manifest_path = self.root / "manifest.json"
        if not manifest_path.exists():
            # En mode dev, on accepte. En prod, c'est fatal.
            return True

        import json
        manifest = json.loads(manifest_path.read_text())
        expected = manifest.get("files", {})

        for rel_path, expected_hash in expected.items():
            full_path = self.root / rel_path
            if not full_path.exists():
                return False
            actual = self.compute_file_hash(full_path)
            if actual != expected_hash:
                return False
        return True

    # ========================================================================
    # DEBUGGER DETECTION
    # ========================================================================

    def detect_debugger(self) -> bool:
        """Détecte si un debugger est attaché"""
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                return kernel32.IsDebuggerPresent() != 0
            except Exception:
                pass
        elif sys.platform == "linux":
            # Vérifier /proc/self/status pour TracerPid
            try:
                status = Path('/proc/self/status').read_text()
                for line in status.split('\n'):
                    if line.startswith('TracerPid:'):
                        tracer = int(line.split(':')[1].strip())
                        if tracer != 0:
                            return True
            except Exception:
                pass
            # Vérifier si gdb est attaché
            try:
                import os
                if 'DEBUGINFOD_URLS' in os.environ or 'gdb' in os.environ.get('_', ''):
                    return True
            except Exception:
                pass
        return False

    # ========================================================================
    # VM / SANDBOX DETECTION
    # ========================================================================

    def detect_vm(self) -> bool:
        """Détecte si on tourne dans une VM ou sandbox"""
        indicators = []

        # Vérifier les processus connus de VMs
        vm_processes = {'vmtoolsd', 'vmwaretray', 'vboxservice', 'qemu-ga',
                         'vdagent', 'xenservice'}
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() in vm_processes:
                    indicators.append(f"VM process: {proc.info['name']}")
        except ImportError:
            pass

        # Vérifier les fichiers de VM
        vm_files = [
            Path("/usr/bin/VBoxService"),
            Path("/usr/bin/vmware-toolbox-cmd"),
            Path("C:/Program Files/VMware/VMware Tools"),
        ]
        for f in vm_files:
            if f.exists():
                indicators.append(f"VM file: {f}")

        # Mémoire < 2GB = probablement sandbox
        try:
            import psutil
            mem = psutil.virtual_memory().total
            if mem < 2 * 1024 * 1024 * 1024:
                indicators.append(f"Low RAM: {mem / 1024**3:.1f} GB")
        except Exception:
            pass

        # CPU count = 1 ou 2 = probablement VM/sandbox
        import multiprocessing
        if multiprocessing.cpu_count() <= 2:
            indicators.append(f"Low CPU count: {multiprocessing.cpu_count()}")

        self._vm_detected = len(indicators) > 1
        return self._vm_detected

    # ========================================================================
    # CHECKS COMBINÉS
    # ========================================================================

    def full_check(self) -> tuple:
        """
        Lance tous les checks anti-tamper.
        Retourne (is_safe, violations_list).
        """
        violations = []

        if not self.verify_integrity():
            violations.append("Fichiers modifiés — intégrité compromise")

        if self.detect_debugger():
            violations.append("Debugger détecté")
            self._debugger_detected = True

        if self.detect_vm():
            violations.append("VM/Sandbox détectée")

        # Vérifier le nombre de sessions (pas plus de 1)
        try:
            import psutil
            current_pid = os.getpid()
            python_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline'])
                                if p.info['name'] and 'python' in p.info['name'].lower()
                                and p.info['pid'] != current_pid]
            # Si plus de 3 processus Python avec 'safetrendbot' dans cmdline
            bot_processes = [p for p in python_processes
                               if p.info['cmdline'] and any('safetrendbot' in str(arg).lower()
                                                            for arg in p.info['cmdline'])]
            if len(bot_processes) > 2:
                violations.append(f"Trop d'instances: {len(bot_processes)}")
        except Exception:
            pass

        return len(violations) == 0, violations

    def raise_if_tampered(self):
        """Lève une exception si tampering détecté"""
        safe, violations = self.full_check()
        if not safe:
            msg = "SafeTrendBot — Accès refusé:\n" + "\n".join(f"  • {v}" for v in violations)
            raise RuntimeError(msg)
