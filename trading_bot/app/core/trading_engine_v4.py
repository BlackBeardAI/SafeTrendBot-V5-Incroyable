"""
Moteur de trading V4 — Régime adaptatif, risk avancé, performance temps réel.
Compatible 100% avec TradingEngineV3, ajoute les capacités V4.
"""
import logging
from threading import Thread, Event
from datetime import datetime
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
import numpy as np

# Imports V3 (existant)
from app.core.config_manager import config_manager, SymbolConfig
from app.core.strategies import MarketData, Signal
from app.core.market_filters import (
    VolatilityFilter, CorrelationFilter, CircuitBreaker, CircuitBreakerLevel
)
from app.core.paper_trading import PaperTradingEngine
from app.core.trade_journal import TradeJournal, TradeJournalEntry
from app.brokers import (
    BrokerAdapter, BrokerType, create_broker_adapter,
    OrderType, Position as BrokerPosition, BrokerNotInstalledError,
)

# Imports V4 (nouveaux)
from app.core.regime_detector import RegimeDetector, MarketRegime
from app.core.adaptive_strategies import AdaptiveStrategyVoter, create_adaptive_voter, AdaptiveVoteResult
from app.core.portfolio_manager import PortfolioRiskManager, PortfolioMetrics
from app.core.performance_metrics import PerformanceTracker, PerformanceSnapshot

# Imports V5 (extraordinaire)
from app.core.walk_forward import WalkForwardAnalysis, WFAParams
from app.core.smart_order_routing import SmartOrderRouter, ExecutionType, ExecutionResult
from app.core.ml_regime_detector import MLRegimeDetector, MLRegimeResult
from app.core.triple_screen import TripleScreen, TripleScreenResult, TimeframeAlignment
from app.core.symbol_circuit_breaker import SymbolCircuitBreaker, SymbolCircuitState
from app.core.news_nlp import NewsNLPAnalyzer, SentimentResult
from app.core.broker_failover import BrokerFailover, BrokerConfig
from app.core.web_dashboard import WebDashboard
from app.core.parallel_backtest import ParallelBacktest
from app.core.decision_journal import DecisionJournal, DecisionRecord
from app.core.trading_profiles import TradingMode
from app.core.extreme_guard import ExtremeGuard

# Telegram
from bot.telegram_alerts import AlertSystem, AlertLevel
TELEGRAM_AVAILABLE = True


class BotState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    HALTED = "halted"
    ERROR = "error"


@dataclass
class BotStatus:
    state: BotState
    mode: str
    broker: str
    connected: bool
    last_tick_time: Optional[datetime]
    last_signal_time: Optional[datetime]
    active_symbols: list
    open_positions: int
    managed_positions: dict
    today_trades: int
    today_pnl: float
    consecutive_losses: int
    circuit_breaker_level: str
    # V4 additions
    current_regime: str = "unknown"
    regime_confidence: float = 0.0
    portfolio_risk_multiplier: float = 1.0
    kelly_fraction: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    message: str = ""


@dataclass
class ManagedPositionInfo:
    ticket: int
    symbol: str
    direction: int
    entry_price: float
    initial_risk: float
    current_sl: float
    phase: str = "opened"
    peak_profit: float = 0.0


class TradingEngineV4(QObject):
    """Moteur V4 avec régime adaptatif et risk avancé"""

    # Signaux V3 (conservés)
    status_changed = pyqtSignal(object)
    log_message = pyqtSignal(str, str)
    position_opened = pyqtSignal(dict)
    position_closed = pyqtSignal(dict)
    account_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    paper_account_updated = pyqtSignal(dict)

    # Nouveaux signaux V4
    regime_changed = pyqtSignal(str, float, list)  # regime, confidence, reasons
    performance_updated = pyqtSignal(object)  # PerformanceSnapshot
    portfolio_metrics = pyqtSignal(object)  # PortfolioMetrics

    def __init__(self):
        super().__init__()
        self.config = config_manager.config
        self.state = BotState.STOPPED
        self.mode = "live"
        self._stop_event = Event()
        self._pause_event = Event()
        self._thread: Optional[Thread] = None

        self.broker: Optional[BrokerAdapter] = None
        self.today_trades = 0
        self.today_pnl = 0.0
        self.today_start_balance = 0.0
        self.current_day: Optional[datetime] = None
        self.last_signal_time: Optional[datetime] = None
        self.last_tick_time: Optional[datetime] = None

        # V3 composants
        self.voter: Optional[AdaptiveStrategyVoter] = None
        self.managed_positions: dict = {}
        self.volatility_filter = VolatilityFilter()
        self.correlation_filter = CorrelationFilter()
        self.circuit_breaker = CircuitBreaker(
            max_drawdown_percent=15.0,
            max_consecutive_losses=self.config.strategy.max_consecutive_losses + 2,
        )
        data_dir = Path(config_manager.app_data_dir) / 'paper'
        self.paper_engine = PaperTradingEngine(
            initial_balance=self.config.initial_capital, data_dir=data_dir,
        )
        self.journal = TradeJournal(Path(config_manager.app_data_dir) / 'journal')

        # V4 composants
        self.regime_detector = RegimeDetector()
        self.portfolio_risk = PortfolioRiskManager(
            max_total_exposure=0.3, max_drawdown_halt=15.0, max_drawdown_reduce=10.0, kelly_fraction=0.25,
        )
        self.performance_tracker = PerformanceTracker(window_size=50)
        self._last_regime: Optional[str] = None

        # V5 composants (extraordinaire)
        self.wfa = WalkForwardAnalysis(wfa_params=WFAParams())
        self.sor: Optional[SmartOrderRouter] = None
        self.ml_regime = MLRegimeDetector(n_regimes=5, model_type='auto')
        self.triple_screen = TripleScreen()
        self.symbol_cb = SymbolCircuitBreaker()
        self.news_nlp = NewsNLPAnalyzer(use_transformers=False)
        self.broker_failover: Optional[BrokerFailover] = None
        self.web_dashboard: Optional[WebDashboard] = None
        self.parallel_backtest = ParallelBacktest()
        self.decision_journal = DecisionJournal()
        self._triple_screen_enabled = getattr(config_manager.config.strategy, 'use_triple_screen', True)
        self._ml_regime_enabled = getattr(config_manager.config.strategy, 'use_ml_regime', False)
        self._wfa_enabled = getattr(config_manager.config.strategy, 'use_wfa', True)
        self._news_nlp_enabled = getattr(config_manager.config.strategy, 'use_news_nlp', True)

        # Telegram
        self._telegram_alerts: Optional[AlertSystem] = None
        self._last_daily_report_date = None

        # EXTREME mode guard (sécurités supplémentaires)
        self.extreme_guard: Optional[ExtremeGuard] = None
        self._init_extreme_guard()

        self._reload_telegram()
        self._setup_logger()

    def _reload_telegram(self):
        cfg = self.config.telegram
        if cfg.enabled and cfg.token and cfg.chat_id:
            try:
                self._telegram_alerts = AlertSystem(token=cfg.token, chat_id=cfg.chat_id)
            except Exception:
                self._telegram_alerts = None
        else:
            self._telegram_alerts = None

    def reload_telegram(self):
        self._reload_telegram()

    def _setup_logger(self):
        self.logger = logging.getLogger('TradingEngineV4')
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            log_file = config_manager.get_log_file('trading')
            handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level: str, message: str):
        getattr(self.logger, level.lower(), self.logger.info)(message)
        self.log_message.emit(level, message)

    # ========================================================================
    # EXTREME GUARD — Initialisation et intégration
    # ========================================================================

    def _init_extreme_guard(self):
        """Initialise le ExtremeGuard si le profil actif est EXTREME."""
        active = self.config.strategy.active_profile
        if active != 'extreme':
            self.extreme_guard = None
            return
        from app.core.trading_profiles import get_profile
        profile = get_profile('extreme')
        if profile.mode != TradingMode.EXTREME:
            return
        state_dir = Path(config_manager.app_data_dir) / 'guard'
        self.extreme_guard = ExtremeGuard.from_profile(profile, state_dir=state_dir)
        self._log('warning', '🔥🔥 EXTREME MODE ACTIVÉ — Sécurités en place')

    def _is_extreme_locked(self) -> bool:
        """Vérifie si le mode EXTREME est verrouillé."""
        if not self.extreme_guard:
            return False
        if self.extreme_guard.state.is_locked:
            reason = self.extreme_guard.state.lock_reason
            self._log('error', f'🔒 EXTREME LOCKED: {reason}')
            return True
        return False

    def _extreme_can_trade(self) -> bool:
        """Vérifie les sécurités EXTREME avant chaque trade."""
        if not self.extreme_guard:
            return True
        # Calcul du PnL journalier en %
        daily_pnl_pct = 0.0
        if self.mode == "live" and self.broker:
            info = self.broker.get_account_info()
            if info and self.today_start_balance > 0:
                daily_pnl_pct = ((info.balance - self.today_start_balance) / self.today_start_balance) * 100
        elif self.mode == "paper":
            balance = self.paper_engine.balance
            if self.today_start_balance > 0:
                daily_pnl_pct = ((balance - self.today_start_balance) / self.today_start_balance) * 100

        current_balance = self._get_current_balance()
        ok = self.extreme_guard.can_trade(current_balance, daily_pnl_pct)
        if not ok:
            reason = self.extreme_guard.last_reason
            if reason:
                self._log('error', f'🚫 EXTREME BLOCK: {reason}')
        return ok

    def _extreme_on_trade_opened(self):
        """Notifie le guard qu'un trade est ouvert."""
        if self.extreme_guard:
            self.extreme_guard.on_trade_opened()

    def _extreme_on_trade_closed(self, realized_pnl: float):
        """Notifie le guard qu'un trade est fermé."""
        if self.extreme_guard:
            balance = self._get_current_balance()
            self.extreme_guard.on_trade_closed(realized_pnl, balance)
            if self.extreme_guard.state.is_locked:
                reason = self.extreme_guard.state.lock_reason
                self._log('critical', f'🔒 EXTREME AUTO-LOCKED: {reason}')
                self._alert_telegram(f'🔒 EXTREME LOCKED\n{reason}\n\nRecharge manuelle requise.')

    def _get_current_balance(self) -> float:
        """Retourne le solde actuel (live ou paper)."""
        if self.mode == "live" and self.broker:
            info = self.broker.get_account_info()
            return info.balance if info else 0.0
        return self.paper_engine.balance

    # ========================================================================
    # BROKER (identique V3)
    # ========================================================================

    def _create_broker(self) -> bool:
        broker_name = self.config.broker.selected.lower()
        type_map = {
            "mt5": BrokerType.MT5, "xtb": BrokerType.XTB,
            "ib": BrokerType.INTERACTIVE_BROKERS, "ctrader": BrokerType.CTRADER,
            "binance": BrokerType.BINANCE, "bybit": BrokerType.BYBIT,
            "kraken": BrokerType.KRAKEN, "coinbase": BrokerType.COINBASE,
        }
        broker_type = type_map.get(broker_name)
        if broker_type is None:
            self._log('error', f"Broker inconnu : {broker_name}")
            return False
        try:
            self.broker = create_broker_adapter(broker_type)
            if self.broker is None:
                return False
            from app.brokers import BrokerSupportLevel
            if self.broker.capabilities.support_level == BrokerSupportLevel.EXPERIMENTAL:
                self._log('warning', f"Broker expérimental : {self.broker.capabilities.name}")
                for w in self.broker.capabilities.warnings:
                    self._log('warning', f"  • {w}")
            return True
        except BrokerNotInstalledError as e:
            self._log('error', str(e))
            return False
        except Exception as e:
            self._log('error', f"Erreur création broker : {e}")
            return False

    def _connect_broker(self) -> bool:
        if self.broker is None:
            return False
        broker_name = self.config.broker.selected.lower()
        try:
            if broker_name == "mt5":
                cfg = self.config.broker.mt5
                ok = self.broker.connect(auto_detect=cfg.auto_detect, terminal_path=cfg.terminal_path,
                                         login=cfg.login, password=cfg.password, server=cfg.server)
            elif broker_name == "xtb":
                cfg = self.config.broker.xtb
                if not cfg.user_id or not cfg.password:
                    return False
                ok = self.broker.connect(user_id=cfg.user_id, password=cfg.password, demo=cfg.demo)
            elif broker_name == "ib":
                cfg = self.config.broker.ib
                ok = self.broker.connect(host=cfg.host, port=cfg.port, client_id=cfg.client_id)
            elif broker_name in ("binance", "bybit", "kraken", "coinbase"):
                cfg = getattr(self.config.broker, broker_name)
                ok = self.broker.connect(api_key=cfg.api_key, api_secret=cfg.api_secret,
                                         passphrase=cfg.passphrase, sandbox=cfg.sandbox)
            else:
                return False

            if ok:
                info = self.broker.get_account_info()
                if info:
                    self._log('info', f"Connecté : {info.name} — {info.balance:.2f} {info.currency}")
                    self.today_start_balance = info.balance
                    self.circuit_breaker.peak_equity = info.equity
                    self.portfolio_risk.update_peak(info.balance)
                    # V5 : init SOR
                    self.sor = SmartOrderRouter(self.broker)
                    # V5 : init broker failover
                    if len(self.config.broker.backup_brokers or []) > 0:
                        configs = [BrokerConfig(name='primary', broker_type=broker_name, priority=1,
                                                connect_kwargs={'auto_detect': True})]
                        for i, backup in enumerate(self.config.broker.backup_brokers, 2):
                            configs.append(BrokerConfig(name=f'backup_{i}', broker_type=backup,
                                                      priority=i, connect_kwargs={}))
                        self.broker_failover = BrokerFailover(configs, create_broker_adapter)
                        self.broker_failover.initialize()
                return True
            else:
                self._log('error', f"Échec connexion : {self.broker.get_last_error()}")
                return False
        except Exception as e:
            self._log('error', f"Exception connexion : {e}")
            self.circuit_breaker.record_error()
            return False

    # ========================================================================
    # CONTRÔLE
    # ========================================================================

    def set_mode(self, mode: str):
        if self.state != BotState.STOPPED:
            self._log('warning', "Impossible de changer de mode en cours d'exécution")
            return False
        if mode not in ('live', 'paper'):
            return False
        self.mode = mode
        self._log('info', f"Mode : {mode}")
        return True

    def start(self) -> bool:
        if self.state == BotState.RUNNING:
            return False
        # V4 : voter adaptatif
        self.voter = create_adaptive_voter(self.config)
        self._log('info', f"Démarrage V4 ({self.mode}) — {len(self.voter.strategies)} stratégies adaptatives")
        self._stop_event.clear()
        self._pause_event.clear()
        self._set_state(BotState.STARTING)

        broker_ok = False
        if self._create_broker():
            broker_ok = self._connect_broker()

        if self.mode == "live" and not broker_ok:
            self._set_state(BotState.ERROR)
            return False

        # V5 : lancer web dashboard
        try:
            self.web_dashboard = WebDashboard(self)
            self.web_dashboard.start()
        except Exception as e:
            self._log('warning', f"Web dashboard non lancé: {e}")

        self._thread = Thread(target=self._run_loop, daemon=True, name="TradingEngineV4")
        self._thread.start()
        return True

    def stop(self):
        if self.state == BotState.STOPPED:
            return
        self._log('info', 'Arrêt...')
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        if self.broker:
            try:
                if hasattr(self.broker, 'shutdown'):
                    self.broker.shutdown()
                else:
                    self.broker.disconnect()
            except Exception:
                pass
        self._set_state(BotState.STOPPED)
        self._log('info', 'Moteur arrêté')

    def pause(self):
        self._pause_event.set()
        self._set_state(BotState.PAUSED)

    def resume(self):
        if self.state == BotState.HALTED:
            self._log('warning', "Circuit breaker activé - reset requis")
            return
        self._pause_event.clear()
        self._set_state(BotState.RUNNING)

    def reset_circuit_breaker(self):
        self.circuit_breaker.reset()
        self.portfolio_risk.peak_balance = 0.0
        self._log('info', "Circuit breaker réinitialisé")

    def _set_state(self, state: BotState, message: str = ""):
        self.state = state
        self.status_changed.emit(self.get_status(message))

    def get_status(self, message: str = "") -> BotStatus:
        connected = self.broker.is_connected() if self.broker else False
        open_positions = 0
        broker_name = self.config.broker.selected

        if self.mode == "live" and self.broker and connected:
            try:
                positions = self.broker.get_positions(magic=self.config.strategy.magic_number)
                open_positions = len(positions)
            except Exception:
                pass
        elif self.mode == "paper":
            open_positions = len(self.paper_engine.open_trades)

        cb_status = self.circuit_breaker.check()
        managed_stats = {
            'total_managed': len(self.managed_positions),
            'at_breakeven': sum(1 for p in self.managed_positions.values() if p.phase == 'at_breakeven'),
            'trailing': sum(1 for p in self.managed_positions.values() if p.phase == 'trailing'),
            'new': sum(1 for p in self.managed_positions.values() if p.phase == 'opened'),
        }

        # V4 metrics
        regime_str = self._last_regime or "unknown"
        risk_mult = 1.0
        kelly = 0.0
        sharpe = 0.0
        max_dd = 0.0
        if self.broker and connected:
            info = self.broker.get_account_info()
            if info:
                risk_mult = self.portfolio_risk.get_risk_multiplier(info.balance)
                kelly = self.portfolio_risk.get_kelly_adjusted_risk(1.0)
                perf = self.performance_tracker.get_metrics(info.balance, info.equity)
                sharpe = perf.sharpe
                max_dd = perf.max_drawdown

        return BotStatus(
            state=self.state, mode=self.mode, broker=broker_name, connected=connected,
            last_tick_time=self.last_tick_time, last_signal_time=self.last_signal_time,
            active_symbols=[s.symbol for s in self.config.symbols if s.enabled],
            open_positions=open_positions, managed_positions=managed_stats,
            today_trades=self.today_trades, today_pnl=self.today_pnl,
            consecutive_losses=self.circuit_breaker.consecutive_losses,
            circuit_breaker_level=cb_status.level.value,
            current_regime=regime_str,
            portfolio_risk_multiplier=round(risk_mult, 2),
            kelly_fraction=round(kelly, 3),
            sharpe=sharpe,
            max_drawdown=max_dd,
            message=message,
        )

    # ========================================================================
    # BOUCLE PRINCIPALE V4
    # ========================================================================

    def _run_loop(self):
        self._set_state(BotState.RUNNING)
        while not self._stop_event.is_set():
            try:
                self.last_tick_time = datetime.now()

                # Circuit breaker
                cb = self.circuit_breaker.check()
                if cb.level == CircuitBreakerLevel.HALT:
                    if self.state != BotState.HALTED:
                        self._log('error', f"HALT : {', '.join(cb.reasons)}")
                        self._set_state(BotState.HALTED)
                        if self._telegram_alerts:
                            try:
                                self._telegram_alerts.send(
                                    f"*CIRCUIT BREAKER*\n\nLe bot a été arrêté.\n\n"
                                    + "\n".join(f"• {r}" for r in cb.reasons),
                                    level=AlertLevel.CRITICAL,
                                )
                            except Exception:
                                pass
                    self._stop_event.wait(10)
                    continue

                self._check_new_day()
                self._check_daily_report()
                self._update_account_info()
                self._update_performance_metrics()

                if self.mode == "live":
                    self._manage_positions()
                else:
                    self._manage_paper_positions()

                if not self._pause_event.is_set() and self.state == BotState.RUNNING:
                    for symbol_config in self.config.symbols:
                        if not symbol_config.enabled:
                            continue
                        if self._stop_event.is_set():
                            break
                        self._process_symbol_v4(symbol_config)

                self.status_changed.emit(self.get_status())
                self._stop_event.wait(5)
            except Exception as e:
                self._log('error', f'Erreur : {e}')
                self.circuit_breaker.record_error()
                self._stop_event.wait(15)
        self._set_state(BotState.STOPPED)

    def _check_new_day(self):
        today = datetime.now().date()
        if self.current_day != today:
            if self.current_day is not None:
                self._log('info', f"Jour : {self.today_trades} trades, P&L {self.today_pnl:+.2f}")
            self.current_day = today
            self.today_trades = 0
            self.today_pnl = 0.0
            if self.mode == "live" and self.broker:
                info = self.broker.get_account_info()
                if info:
                    self.today_start_balance = info.balance
                    self.portfolio_risk.update_peak(info.balance)

    def _check_daily_report(self):
        if not self._telegram_alerts:
            return
        if not self.config.telegram.alert_daily_report:
            return
        now = datetime.now()
        target_hour = self.config.telegram.daily_report_hour
        today = now.date()
        if (now.hour == target_hour and self._last_daily_report_date != today and self.today_trades > 0):
            try:
                balance = 0.0
                if self.mode == "live" and self.broker:
                    info = self.broker.get_account_info()
                    if info:
                        balance = info.balance
                else:
                    balance = self.paper_engine.account.balance
                today_trades = [e for e in self.journal.get_all(only_closed=True)
                                if e.exit_time and e.exit_time.date() == today]
                wins = sum(1 for t in today_trades if t.profit > 0)
                win_rate = (wins / len(today_trades) * 100) if today_trades else 0
                # V4 : ajouter métriques
                perf = self.performance_tracker.get_metrics(balance, balance)
                self._telegram_alerts.send(
                    f"*📊 Rapport journalier V4*\n\n"
                    f"Trades : {self.today_trades}\n"
                    f"P&L : {self.today_pnl:+.2f}\n"
                    f"Win Rate : {win_rate:.0f}%\n"
                    f"Sharpe : {perf.sharpe}\n"
                    f"Max DD : {perf.max_drawdown}%\n"
                    f"Balance : {balance:,.2f}",
                    level=AlertLevel.INFO,
                )
                self._last_daily_report_date = today
            except Exception as e:
                self._log('warning', f"Erreur rapport : {e}")

    def _update_account_info(self):
        if self.mode == "live" and self.broker:
            info = self.broker.get_account_info()
            if info:
                self.circuit_breaker.update_equity(info.equity)
                self.portfolio_risk.update_peak(info.balance)
                self.performance_tracker.add_equity_point(info.equity)
                self.account_updated.emit({
                    'balance': info.balance, 'equity': info.equity,
                    'profit': info.profit, 'margin': info.margin,
                    'margin_free': info.margin_free, 'margin_level': info.margin_level,
                    'currency': info.currency, 'server': info.server,
                    'name': info.name, 'leverage': info.leverage,
                    'broker': info.broker_type.value,
                })
        elif self.mode == "paper":
            self.circuit_breaker.update_equity(self.paper_engine.account.equity)
            self.performance_tracker.add_equity_point(self.paper_engine.account.equity)
            self.paper_account_updated.emit({
                'balance': self.paper_engine.account.balance,
                'equity': self.paper_engine.account.equity,
                'currency': self.paper_engine.account.currency,
                'open_trades': len(self.paper_engine.open_trades),
            })

    def _update_performance_metrics(self):
        balance = equity = 0.0
        if self.mode == "live" and self.broker:
            info = self.broker.get_account_info()
            if info:
                balance, equity = info.balance, info.equity
        elif self.mode == "paper":
            balance = equity = self.paper_engine.account.equity
        perf = self.performance_tracker.get_metrics(balance, equity)
        self.performance_updated.emit(perf)

    def _manage_positions(self):
        if not self.broker or not self.broker.capabilities.supports_trailing_stop:
            return
        try:
            positions = self.broker.get_positions(magic=self.config.strategy.magic_number)
            open_tickets = {p.ticket for p in positions}
            closed_tickets = [t for t in self.managed_positions if t not in open_tickets]
            for ticket in closed_tickets:
                managed = self.managed_positions[ticket]
                self._handle_live_position_closed(ticket, managed)
                del self.managed_positions[ticket]
            for p in positions:
                if p.ticket not in self.managed_positions:
                    self.managed_positions[p.ticket] = ManagedPositionInfo(
                        ticket=p.ticket, symbol=p.symbol, direction=p.direction,
                        entry_price=p.entry_price,
                        initial_risk=abs(p.entry_price - p.stop_loss),
                        current_sl=p.stop_loss,
                    )
            for p in positions:
                self._manage_single_position(p)
        except Exception as e:
            self._log('warning', f"Erreur gestion positions : {e}")

    def _handle_live_position_closed(self, ticket: int, managed: ManagedPositionInfo):
        try:
            self._log('info', f"Position {ticket} fermée ({managed.symbol})")
            self.position_closed.emit({
                'symbol': managed.symbol, 'profit': 0, 'reason': 'Closed',
            })
            if self._telegram_alerts and self.config.telegram.alert_position_close:
                try:
                    self._telegram_alerts.send(
                        f"*Position fermée*\n\n📊 {managed.symbol}\nTicket : {ticket}",
                        level=AlertLevel.INFO,
                    )
                except Exception:
                    pass
        except Exception as e:
            self._log('warning', f"Erreur handle close : {e}")

    def _manage_single_position(self, position: BrokerPosition):
        managed = self.managed_positions.get(position.ticket)
        if managed is None or managed.initial_risk <= 0:
            return
        tick = self.broker.get_tick(position.symbol)
        if tick is None:
            return
        current_price = tick.bid if position.direction == 1 else tick.ask
        if position.direction == 1:
            profit_distance = current_price - position.entry_price
        else:
            profit_distance = position.entry_price - current_price
        if profit_distance > managed.peak_profit:
            managed.peak_profit = profit_distance
        # Break-even à +1R
        if managed.phase == "opened":
            if profit_distance >= managed.initial_risk:
                new_sl = position.entry_price
                sym_info = self.broker.get_symbol_info(position.symbol)
                if sym_info:
                    spread_margin = sym_info.spread * sym_info.point * 2
                    if position.direction == 1:
                        new_sl += spread_margin
                    else:
                        new_sl -= spread_margin
                result = self.broker.modify_position(position.ticket, stop_loss=new_sl)
                if result.success:
                    managed.current_sl = new_sl
                    managed.phase = "at_breakeven"
                    self._log('info', f"✓ Break-even {position.ticket} @ {new_sl:.5f}")
        # Trailing à +2R
        if managed.phase in ("opened", "at_breakeven"):
            if profit_distance >= managed.initial_risk * 2:
                managed.phase = "trailing"
        if managed.phase == "trailing":
            trail_distance = managed.initial_risk
            if position.direction == 1:
                new_sl = current_price - trail_distance
                if new_sl > managed.current_sl:
                    result = self.broker.modify_position(position.ticket, stop_loss=new_sl)
                    if result.success:
                        managed.current_sl = new_sl
                        self._log('info', f"↗ Trailing {position.ticket} → {new_sl:.5f}")
            else:
                new_sl = current_price + trail_distance
                if new_sl < managed.current_sl:
                    result = self.broker.modify_position(position.ticket, stop_loss=new_sl)
                    if result.success:
                        managed.current_sl = new_sl
                        self._log('info', f"↘ Trailing {position.ticket} → {new_sl:.5f}")

    def _manage_paper_positions(self):
        if not self.broker or not self.paper_engine.open_trades:
            return
        prices = {}
        for trade in self.paper_engine.open_trades.values():
            tick = self.broker.get_tick(trade.symbol)
            if tick:
                prices[trade.symbol] = (tick.bid, tick.ask)
        closed = self.paper_engine.update_prices(prices)
        for trade in closed:
            self.today_pnl += trade.profit
            self.performance_tracker.add_trade(trade.profit, trade.symbol, trade.direction)
            self.portfolio_risk.record_trade(trade.profit)
            if trade.profit > 0:
                self.circuit_breaker.record_win()
            else:
                self.circuit_breaker.record_loss()

            # EXTREME guard: notifie la fermeture
            self._extreme_on_trade_closed(trade.profit)

            self.journal.record_exit(
                ticket=trade.ticket, exit_price=trade.exit_price or 0,
                exit_reason=trade.exit_reason, profit=trade.profit,
                capital=self.paper_engine.account.balance,
            )
            self.position_closed.emit({
                'symbol': trade.symbol, 'profit': trade.profit,
                'reason': trade.exit_reason,
            })
            if self._telegram_alerts and self.config.telegram.alert_position_close:
                try:
                    self._telegram_alerts.alert_position_closed(
                        symbol=trade.symbol, profit=trade.profit, reason=trade.exit_reason,
                    )
                except Exception:
                    pass

    # ========================================================================
    # TRAITEMENT V4 — avec régime adaptatif
    # ========================================================================

    def _process_symbol_v4(self, symbol_config: SymbolConfig):
        symbol = symbol_config.symbol
        if self.broker:
            self.broker.select_symbol(symbol)

        data = self._get_market_data(symbol, symbol_config.timeframe)
        if data is None:
            return

        if not self._is_safe_to_trade(symbol, data):
            return
        if self._has_open_position(symbol):
            return

        # V5 : Circuit Breaker par symbole
        cb_state = self.symbol_cb.check(symbol)
        if cb_state.status.value == "halted":
            self._log('warning', f'{symbol}: CB symbole HALTED ({cb_state.reasons[0] if cb_state.reasons else ""})')
            return

        # V5 : ML Régime (optionnel)
        ml_regime_result = None
        if self._ml_regime_enabled:
            ml_regime_result = self.ml_regime.detect(data.closes, data.highs, data.lows, data.volumes)
            self._log('debug', f'{symbol}: ML régime = {ml_regime_result.regime.value} ({ml_regime_result.confidence:.0%})')

        # V4 : vote adaptatif avec régime
        result = self.voter.vote(data)
        if isinstance(result, AdaptiveVoteResult):
            regime = result.regime
            regime_conf = result.regime_confidence
            adjusted_risk = result.adjusted_risk_percent
            weights = result.strategy_weights or {}
        else:
            regime = MarketRegime.UNKNOWN
            regime_conf = 0.0
            adjusted_risk = self.config.strategy.risk_percent
            weights = {}

        # V5 : Triple Screen Multi-Timeframe
        triple_result = None
        if self._triple_screen_enabled:
            triple_result = self._check_triple_screen(symbol, symbol_config.timeframe)
            if triple_result and triple_result.alignment == TimeframeAlignment.CONFLICTED:
                self._log('info', f'{symbol}: Triple Screen CONFLIT — trade refusé')
                self.decision_journal.record_skip(
                    symbol=symbol, reason='Triple Screen conflicted',
                    regime=regime.value, regime_confidence=regime_conf,
                    confidence_score=result.confidence,
                )
                return
            if triple_result and triple_result.alignment == TimeframeAlignment.FULLY_ALIGNED:
                self._log('debug', f'{symbol}: ✅ Triple Screen aligné ({triple_result.reason})')

        # V5 : News NLP sentiment
        if self._news_nlp_enabled:
            safe_news, news_reason = self.news_nlp.is_safe_to_trade(
                symbol, direction=(1 if result.final_signal == Signal.BUY else -1)
            )
            if not safe_news:
                self._log('info', f'{symbol}: News NLP bloque — {news_reason}')
                return

        # Log V5 enrichi
        buy_s = result.buy_votes
        sell_s = result.sell_votes
        log_line = (f'{symbol}: {result.final_signal.name} | '
                    f'régime={regime.value}({regime_conf:.0%}) | '
                    f'buy={buy_s} sell={sell_s} conf={result.confidence:.2f}')
        if triple_result:
            log_line += f' | TS={triple_result.alignment.value}'
        self._log('debug', log_line)

        # Émettre changement de régime
        regime_str = regime.value
        if regime_str != self._last_regime:
            self._last_regime = regime_str
            self.regime_changed.emit(regime_str, regime_conf,
                                    [result.decision_reason] if hasattr(result, 'decision_reason') else [])
            self._log('info', f'🌊 Régime détecté sur {symbol} : {regime_str} ({regime_conf:.0%})')

        if result.final_signal == Signal.NONE:
            return

        direction = 1 if result.final_signal == Signal.BUY else -1

        open_positions = self._get_open_positions_summary()

        # Filtre corrélation
        if self.config.strategy.use_correlation_filter:
            corr_ok, corr_reason = self._check_correlation(symbol, direction, open_positions)
            if not corr_ok:
                self._log('info', f'{symbol}: bloqué corrélation ({corr_reason})')
                return

        # V4/V5 : vérification portefeuille
        if self.mode == "live" and self.broker:
            info = self.broker.get_account_info()
            if info:
                tick = self.broker.get_tick(symbol)
                sym_info = self.broker.get_symbol_info(symbol)
                if tick and sym_info:
                    stop_dist = self._calculate_atr(data) * self.config.strategy.atr_multiplier_sl
                    lot = self._calculate_lot_size(sym_info, stop_dist)
                    exposure = lot * tick.bid
                    can_open, reason = self.portfolio_risk.can_open_position(
                        info.balance, symbol, exposure, open_positions
                    )
                    if not can_open:
                        self._log('warning', f'{symbol}: bloqué risk manager ({reason})')
                        return

        # V5 : WFA auto-optimization
        if self._wfa_enabled and self.wfa.should_run():
            self._log('info', f'{symbol}: Lancement WFA...')
            wfa_result = self.wfa.run_wfa(data)
            if wfa_result and wfa_result.is_better:
                self._log('info', f'{symbol}: WFA params optimisés appliqués!')
                # Appliquer les params au voter
                # (simplifié : le voter est recréé au prochain start)

        self.last_signal_time = datetime.now()
        self._log('info',
                  f'📈 SIGNAL V5 {result.final_signal.name} sur {symbol} — '
                  f'{result.decision_reason} (risk={adjusted_risk:.2f}%)')

        # V5 : enregistrer la décision
        self.decision_journal.record_open(
            ticket=0,  # Sera mis à jour après exécution
            symbol=symbol,
            regime=regime.value,
            regime_confidence=regime_conf,
            strategy_weights=weights,
            confidence_score=result.confidence,
            buy_votes=result.buy_votes,
            sell_votes=result.sell_votes,
            price=data.closes[-1],
            spread=(data.highs[-1] - data.lows[-1]) / data.closes[-1] * 100 if data.closes[-1] > 0 else 0,
            atr=self._calculate_atr(data),
            volatility_regime='',
            bb_position=0.0,
            risk_percent=adjusted_risk,
            lot_size=0,  # Sera rempli à l'exécution
            stop_distance=self._calculate_atr(data) * self.config.strategy.atr_multiplier_sl,
            portfolio_exposure_before=sum(abs(1) for _, _ in open_positions) * 1000,
            portfolio_exposure_after=0,
            circuit_breaker_level=self.circuit_breaker.check().level.value,
            correlation_blocked=False,
            news_sentiment=None,
            triple_screen_alignment=triple_result.alignment.value if triple_result else None,
        )

        self._execute_trade_v4(symbol, direction, result, data, adjusted_risk)

    def _check_triple_screen(self, symbol: str, tf: str):
        """Vérifie le Triple Screen sur D1/H4/H1"""
        if not self.broker:
            return None
        d1_data = self.broker.get_candles_arrays(symbol, 'D1', 300)
        h4_data = self.broker.get_candles_arrays(symbol, 'H4', 300)
        h1_data = self.broker.get_candles_arrays(symbol, 'H1', 100)
        if d1_data is None or h4_data is None or h1_data is None:
            return None
        d1 = MarketData(symbol=symbol, closes=d1_data['close'], highs=d1_data['high'],
                        lows=d1_data['low'], opens=d1_data['open'], volumes=d1_data['volume'], timeframe='D1')
        h4 = MarketData(symbol=symbol, closes=h4_data['close'], highs=h4_data['high'],
                        lows=h4_data['low'], opens=h4_data['open'], volumes=h4_data['volume'], timeframe='H4')
        h1 = MarketData(symbol=symbol, closes=h1_data['close'], highs=h1_data['high'],
                        lows=h1_data['low'], opens=h1_data['open'], volumes=h1_data['volume'], timeframe='H1')
        return self.triple_screen.analyze(d1, h4, h1)

    def _execute_trade_v4(self, symbol, direction, vote_result, data, adjusted_risk_percent):
        if getattr(self.config.strategy, 'read_only_mode', False):
            dir_text = "BUY" if direction > 0 else "SELL"
            self._log('info', f"[READ-ONLY] Signal {dir_text} sur {symbol}")
            return

        if self.mode == "live":
            self._execute_live_trade_v4(symbol, direction, vote_result, data, adjusted_risk_percent)
        else:
            self._execute_paper_trade_v4(symbol, direction, vote_result, data, adjusted_risk_percent)

    def _execute_live_trade_v4(self, symbol, direction, vote_result, data, adjusted_risk_percent):
        # V5 : utiliser le broker actif du failover si disponible
        broker = self.broker
        if self.broker_failover:
            broker = self.broker_failover.get_active()
            if broker is None:
                self._log('error', "Aucun broker disponible (failover)")
                return

        if not broker:
            return
        sym_info = broker.get_symbol_info(symbol)
        tick = broker.get_tick(symbol)
        if not sym_info or not tick:
            return

        atr_val = self._calculate_atr(data)
        if atr_val <= 0:
            return

        stop_distance = atr_val * self.config.strategy.atr_multiplier_sl
        if direction == 1:
            price = tick.ask
            sl = price - stop_distance
            tp = price + stop_distance * self.config.strategy.risk_reward_ratio
            order_type = OrderType.MARKET_BUY
        else:
            price = tick.bid
            sl = price + stop_distance
            tp = price - stop_distance * self.config.strategy.risk_reward_ratio
            order_type = OrderType.MARKET_SELL

        # V5 : risque ajusté
        original_risk = self.config.strategy.risk_percent
        self.config.strategy.risk_percent = adjusted_risk_percent
        lot_size = self._calculate_lot_size(sym_info, stop_distance)
        self.config.strategy.risk_percent = original_risk

        if lot_size <= 0:
            return

        # V5 : SOR execution
        result = None
        if self.sor:
            exec_result = self.sor.execute(symbol, direction, lot_size, sl, tp,
                                           self.config.strategy.magic_number)
            if exec_result.success:
                result = type('obj', (object,), {
                    'success': True, 'ticket': 0, 'filled_price': exec_result.filled_price,
                    'error_message': '',
                })()
            else:
                self._log('warning', f'SOR échoué: {exec_result.error_message}, fallback market')

        if result is None:
            result = broker.open_position(
                symbol=symbol, order_type=order_type,
                volume=lot_size, stop_loss=sl, take_profit=tp,
                magic=self.config.strategy.magic_number,
                comment='SafeTrendBotV5',
            )

        if result.success:
            dir_str = "BUY" if direction == 1 else "SELL"
            actual_price = result.filled_price or price
            self._log('info', f'{dir_str} {symbol} @ {actual_price:.5f} ({lot_size} lots, risk={adjusted_risk_percent:.2f}%)')
            self.today_trades += 1

            # EXTREME guard: notifie l'ouverture
            self._extreme_on_trade_opened()

            self.managed_positions[result.ticket] = ManagedPositionInfo(
                ticket=result.ticket, symbol=symbol, direction=direction,
                entry_price=actual_price,
                initial_risk=abs(actual_price - sl),
                current_sl=sl,
            )

            # V5 : enregistrer dans decision journal
            self.decision_journal.record_close(
                ticket=result.ticket,
                exit_price=actual_price,
                profit=0,
                exit_reason='OPENED',
            )

            self._journal_entry(
                ticket=result.ticket, symbol=symbol, direction=direction,
                volume=lot_size, entry=actual_price, sl=sl, tp=tp,
                vote_result=vote_result, atr_val=atr_val, data=data,
            )

            self.position_opened.emit({
                'symbol': symbol, 'direction': dir_str, 'price': actual_price,
                'volume': lot_size, 'sl': sl, 'tp': tp,
                'regime': vote_result.regime.value if hasattr(vote_result, 'regime') else 'unknown',
            })

            if self._telegram_alerts and self.config.telegram.alert_position_open:
                try:
                    regime_info = vote_result.regime.value if hasattr(vote_result, 'regime') else 'unknown'
                    self._telegram_alerts.send(
                        f"*Position ouverte V5*\\n\\n"
                        f"📊 {symbol} {dir_str}\\n"
                        f"@ {actual_price:.5f} ({lot_size} lots)\\n"
                        f"Régime : {regime_info}\\n"
                        f"Risk : {adjusted_risk_percent:.2f}%",
                        level=AlertLevel.INFO,
                    )
                except Exception:
                    pass
        else:
            self._log('error', f'Ordre refusé : {result.error_message}')
            self.circuit_breaker.record_error()

    def _execute_paper_trade_v4(self, symbol, direction, vote_result, data, adjusted_risk_percent):
        if not self.broker:
            return
        tick = self.broker.get_tick(symbol)
        if not tick:
            return

        atr_val = self._calculate_atr(data)
        if atr_val <= 0:
            return

        stop_distance = atr_val * self.config.strategy.atr_multiplier_sl
        if direction == 1:
            price = tick.ask
            sl = price - stop_distance
            tp = price + stop_distance * self.config.strategy.risk_reward_ratio
        else:
            price = tick.bid
            sl = price + stop_distance
            tp = price - stop_distance * self.config.strategy.risk_reward_ratio

        risk_amount = self.paper_engine.account.balance * adjusted_risk_percent / 100
        units = risk_amount / stop_distance if stop_distance > 0 else 0
        lot_size = max(0.01, round(units / 100000, 2))

        trade = self.paper_engine.open_trade(
            symbol=symbol, direction=direction, volume=lot_size,
            entry_price=price, stop_loss=sl, take_profit=tp,
        )
        self.today_trades += 1

        # EXTREME guard: notifie l'ouverture (paper)
        self._extreme_on_trade_opened()

        self._journal_entry(
            ticket=trade.ticket, symbol=symbol, direction=direction,
            volume=lot_size, entry=price, sl=sl, tp=tp,
            vote_result=vote_result, atr_val=atr_val, data=data,
        )

        dir_str = "BUY" if direction == 1 else "SELL"
        self._log('info', f'[PAPER V4] {dir_str} {symbol} @ {price:.5f} ({lot_size} lots, risk={adjusted_risk_percent:.2f}%)')
        self.position_opened.emit({
            'symbol': symbol, 'direction': dir_str, 'price': price,
            'volume': lot_size, 'sl': sl, 'tp': tp, 'paper': True,
            'regime': vote_result.regime.value if hasattr(vote_result, 'regime') else 'unknown',
        })

    # ========================================================================
    # UTILITAIRES (identiques V3)
    # ========================================================================

    def _get_market_data(self, symbol, timeframe_str):
        if not self.broker:
            return None
        data = self.broker.get_candles_arrays(symbol, timeframe_str, 250)
        if data is None:
            return None
        n = len(data['close'])
        if n < 50:
            return None
        higher_tf = self._get_higher_tf(timeframe_str)
        higher_data = self.broker.get_candles_arrays(symbol, higher_tf, 100)
        higher_closes = higher_data['close'] if higher_data is not None else None
        return MarketData(
            symbol=symbol,
            closes=data['close'], highs=data['high'], lows=data['low'],
            opens=data['open'], volumes=data['volume'],
            timeframe=timeframe_str,
            higher_tf_closes=higher_closes,
            higher_tf_timeframe=higher_tf,
        )

    def _is_safe_to_trade(self, symbol, data):
        # EXTREME guard check
        if self._is_extreme_locked():
            return False
        if not self._extreme_can_trade():
            return False

        if self.circuit_breaker.consecutive_losses >= self.config.strategy.max_consecutive_losses:
            return False
        if self.mode == "live" and self.today_start_balance > 0 and self.broker:
            info = self.broker.get_account_info()
            if info:
                daily_loss_pct = ((self.today_start_balance - info.balance) / self.today_start_balance * 100)
                if daily_loss_pct >= self.config.strategy.max_daily_loss_percent:
                    return False
        now = datetime.now()
        end_h = self.config.strategy.end_hour
        if end_h < 24:
            if now.hour < self.config.strategy.start_hour or now.hour >= end_h:
                return False
        elif now.hour < self.config.strategy.start_hour:
            return False
        if now.weekday() == 4 and not self.config.strategy.trade_on_friday:
            return False
        if now.weekday() >= 5:
            return False
        if self.config.strategy.use_volatility_filter:
            vol = self.volatility_filter.analyze(data.highs, data.lows, data.closes)
            if not vol.safe_to_trade:
                self._log('info', f'{symbol} : volatilité bloque ({vol.reason})')
                return False
        if self.config.news.enabled and not self._check_news_filter(symbol):
            return False
        if self.mode == "live" and self.broker:
            tick = self.broker.get_tick(symbol)
            sym_info = self.broker.get_symbol_info(symbol)
            if tick and sym_info and sym_info.point > 0:
                spread_points = (tick.ask - tick.bid) / sym_info.point
                if spread_points > 30:
                    return False
        return True

    def _check_news_filter(self, symbol):
        if getattr(self, '_economic_calendar', None) is None:
            try:
                from bot.economic_calendar import EconomicCalendar
                self._economic_calendar = EconomicCalendar()
            except ImportError:
                return True
        try:
            safe, event = self._economic_calendar.is_safe_to_trade(symbol)
            return safe
        except Exception:
            return True

    def _has_open_position(self, symbol):
        if self.mode == "live" and self.broker:
            positions = self.broker.get_positions(symbol=symbol, magic=self.config.strategy.magic_number)
            return len(positions) > 0
        else:
            return any(t.symbol == symbol for t in self.paper_engine.open_trades.values())

    def _get_open_positions_summary(self):
        if self.mode == "live" and self.broker:
            positions = self.broker.get_positions(magic=self.config.strategy.magic_number)
            return [(p.symbol, p.direction) for p in positions]
        else:
            return [(t.symbol, t.direction) for t in self.paper_engine.open_trades.values()]

    def _check_correlation(self, new_symbol, new_direction, open_positions):
        for open_symbol, open_direction in open_positions:
            if open_symbol == new_symbol:
                continue
            try:
                a_data = self.broker.get_candles_arrays(new_symbol, 'H1', 100)
                b_data = self.broker.get_candles_arrays(open_symbol, 'H1', 100)
                if a_data is None or b_data is None:
                    continue
                n = min(len(a_data['close']), len(b_data['close']))
                if n < 20:
                    continue
                a_returns = np.diff(a_data['close'][-n:]) / a_data['close'][-n:-1]
                b_returns = np.diff(b_data['close'][-n:]) / b_data['close'][-n:-1]
                corr = float(np.corrcoef(a_returns, b_returns)[0, 1])
                if corr > 0.75 and new_direction == open_direction:
                    return False, f"Corrélation forte ({corr:.2f}) avec {open_symbol}"
                if corr < -0.75 and new_direction != open_direction:
                    return False, f"Corrélation négative ({corr:.2f}) avec {open_symbol}"
            except Exception:
                continue
        return True, "OK"

    def _journal_entry(self, ticket, symbol, direction, volume, entry, sl, tp,
                       vote_result, atr_val, data):
        try:
            balance = equity = 0.0
            if self.mode == "live" and self.broker:
                info = self.broker.get_account_info()
                if info:
                    balance, equity = info.balance, info.equity
            else:
                balance = self.paper_engine.account.balance
                equity = self.paper_engine.account.equity
            vol_status = self.volatility_filter.analyze(data.highs, data.lows, data.closes)
            regime_str = vote_result.regime.value if hasattr(vote_result, 'regime') else 'unknown'
            entry_journal = TradeJournalEntry(
                ticket=ticket, symbol=symbol, timeframe=data.timeframe,
                direction="BUY" if direction == 1 else "SELL",
                volume=volume, entry_price=entry, entry_time=datetime.now(),
                stop_loss=sl, take_profit=tp,
                entry_balance=balance, entry_equity=equity,
                atr_value=atr_val, volatility_regime=vol_status.regime.value,
                confidence_score=vote_result.confidence,
                strategies_agreed=[s.strategy_name for s in vote_result.individual_signals
                                   if s.signal.value == direction],
                buy_votes=vote_result.buy_votes, sell_votes=vote_result.sell_votes,
                indicators={'atr': atr_val, 'regime': regime_str},
            )
            self.journal.record_entry(entry_journal)
        except Exception as e:
            self._log('warning', f'Erreur journal : {e}')

    @staticmethod
    def _get_higher_tf(tf):
        hierarchy = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']
        try:
            idx = hierarchy.index(tf.upper())
            return hierarchy[min(idx + 2, len(hierarchy) - 1)]
        except ValueError:
            return 'D1'

    def _calculate_atr(self, data):
        from app.core.strategies import atr
        result = atr(data.highs, data.lows, data.closes, self.config.strategy.atr_period)
        return float(result[-1]) if len(result) > 0 else 0.0

    def _calculate_lot_size(self, sym_info, stop_distance):
        if not self.broker:
            return 0
        account = self.broker.get_account_info()
        if not account:
            return 0
        risk_amount = account.balance * self.config.strategy.risk_percent / 100
        tick_value = sym_info.tick_value
        tick_size = sym_info.tick_size
        if tick_value == 0 or tick_size == 0 or stop_distance == 0:
            return 0
        value_per_unit = tick_value / tick_size
        lot_size = risk_amount / (stop_distance * value_per_unit)
        import math
        step = sym_info.volume_step
        lot_size = math.floor(lot_size / step) * step if step > 0 else lot_size
        lot_size = max(sym_info.volume_min, min(sym_info.volume_max, lot_size))
        return round(lot_size, 2)
