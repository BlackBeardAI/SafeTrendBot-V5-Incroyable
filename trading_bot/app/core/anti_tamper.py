"""
Anti-Tamper (NEUTRALISÉ) — ne fait plus rien.
"""
from pathlib import Path
from typing import Optional


class AntiTamper:
    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or Path(__file__).parent.parent.parent

    def check_all(self) -> bool:
        return True

    def verify_integrity(self) -> bool:
        return True

    def scan_debugger(self) -> bool:
        return False

    def scan_vm(self) -> bool:
        return False