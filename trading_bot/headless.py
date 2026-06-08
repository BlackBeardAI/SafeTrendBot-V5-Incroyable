"""
Launcher headless pour VPS/cloud.
Permet de faire tourner SafeTrendBot V5 sans interface graphique.
Usage: python headless.py [--config path] [--paper] [--symbols EURUSD,GBPUSD]
"""
import sys
import os
import time
import signal
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

from app.core.config_manager import config_manager
from app.core.trading_engine_v4 import TradingEngineV4, BotState


def check_license():
    """Vérifie la licence — même en mode headless"""
    from app.core.license_manager import LicenseManager
    from app.core.anti_tamper import AntiTamper
    try:
        at = AntiTamper()
        at.raise_if_tampered()
    except RuntimeError as e:
        print(f"[SECURITY] {e}")
        sys.exit(1)

    lm = LicenseManager(secret_key="safetrendbot_v5_secret_2026")
    valid, message = lm.validate_license()
    if valid:
        print(f"[LICENSE] {message}")
        return True

    # Essai gratuit automatique en headless
    print(f"[LICENSE] {message}")
    print("[LICENSE] Essai gratuit de 7 jours activé (headless)")
    lm.start_trial(days=7)
    return True


class HeadlessRunner:
    def __init__(self, paper=False, symbols=None):
        self.engine = TradingEngineV4()
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        if paper:
            self.engine.set_mode('paper')
        if symbols:
            for sym in self.engine.config.symbols:
                sym.enabled = sym.symbol in symbols

        # Connexion des signaux vers console
        self.engine.status_changed.connect(self._on_status)
        self.engine.log_message.connect(self._on_log)
        self.engine.position_opened.connect(self._on_position)
        self.engine.position_closed.connect(self._on_position_closed)
        self.engine.regime_changed.connect(self._on_regime)
        self.engine.performance_updated.connect(self._on_perf)

    def _signal_handler(self, signum, frame):
        print(f"\\nSignal {signum} reçu — arrêt...")
        self.running = False
        self.engine.stop()

    def _on_status(self, status):
        print(f"[STATUS] {status.state.value} | {status.today_trades} trades | PnL: {status.today_pnl:+.2f}")

    def _on_log(self, level, msg):
        print(f"[{level.upper():8}] {msg}")

    def _on_position(self, pos):
        print(f"[TRADE] {'PAPER ' if pos.get('paper') else ''}{pos['direction']} {pos['symbol']} @ {pos['price']:.5f}")

    def _on_position_closed(self, pos):
        print(f"[CLOSE] {pos['symbol']} | PnL: {pos.get('profit', 0):+.2f} | {pos['reason']}")

    def _on_regime(self, regime, conf, reasons):
        print(f"[REGIME] {regime} ({conf:.0%}) — {reasons[0] if reasons else ''}")

    def _on_perf(self, perf):
        if perf.trades_count % 5 == 0 and perf.trades_count > 0:
            print(f"[PERF] WinRate: {perf.win_rate}% | Sharpe: {perf.sharpe} | PF: {perf.profit_factor} | MaxDD: {perf.max_drawdown}%")

    def run(self):
        # Vérification licence
        check_license()

        print("=" * 50)
        print("SafeTrendBot V5 — Mode Headless")
        print("=" * 50)
        print(f"Mode: {self.engine.mode}")
        print(f"Symboles: {[s.symbol for s in self.engine.config.symbols if s.enabled]}")
        print("Appuyez sur Ctrl+C pour arrêter")
        print("=" * 50)

        if not self.engine.start():
            print("ERREUR: Échec du démarrage du moteur")
            return 1

        while self.running and self.engine.state not in (BotState.STOPPED, BotState.ERROR):
            time.sleep(1)

        print("\\nArrêt complet.")
        return 0


def main():
    parser = argparse.ArgumentParser(description='SafeTrendBot V5 Headless')
    parser.add_argument('--paper', action='store_true', help='Mode paper trading')
    parser.add_argument('--symbols', type=str, help='Symboles (comma-separated)')
    parser.add_argument('--config', type=str, help='Chemin config.json alternatif')
    args = parser.parse_args()

    if args.config:
        os.environ['SAFETRENDBOT_CONFIG'] = args.config

    symbols = args.symbols.split(',') if args.symbols else None
    runner = HeadlessRunner(paper=args.paper, symbols=symbols)
    return runner.run()


if __name__ == '__main__':
    sys.exit(main())
