"""
SafeTrendBot Headless — Mode serveur/sans GUI
=============================================
"""

import sys
import os
import time
import signal
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.trading_engine import TradingEngine

# Configuration logging
LOG_DIR = Path.home() / ".safetrendbot"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("SafeTrendBot")


class SafeTrendBotServer:
    """Bot en mode serveur (headless)."""
    
    def __init__(self):
        self.running = False
        self.engine: TradingEngine = None
        
        # Handle Ctrl+C
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Signal {signum} reçu — arrêt...")
        self.stop()
    
    def start(self):
        """Démarre le bot."""
        logger.info("=" * 50)
        logger.info("SafeTrendBot V5 — Mode Headless")
        logger.info("=" * 50)
        
        logger.info("Mode libre — démarrage")
        # Démarrer moteur
        self.engine = TradingEngine()
        self.engine.start()
        self.running = True
        
        logger.info("🚀 Bot démarré — Ctrl+C pour arrêter")
        
        # Boucle principale
        while self.running:
            time.sleep(1)
            
            # Status periodically
            if self.engine and hasattr(self.engine, 'broker') and self.engine.broker:
                try:
                    info = self.engine.broker.get_account_info()
                    if info:
                        logger.debug(f"Balance: {info.get('balance', 0):.2f} | "
                                   f"Equity: {info.get('equity', 0):.2f}")
                except:
                    pass
        
        return True
    
    def stop(self):
        """Arrête le bot."""
        logger.info("⏹️ Arrêt en cours...")
        self.running = False
        
        if self.engine:
            self.engine.stop()
        
        logger.info("✅ Bot arrêté")


def main():
    server = SafeTrendBotServer()
    
    try:
        server.start()
    except Exception as e:
        logger.exception(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()