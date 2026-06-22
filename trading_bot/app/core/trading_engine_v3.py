"""
Moteur de trading V3 - Utilise l'abstraction BrokerAdapter.
Fonctionne avec MT5, XTB, et Interactive Brokers via la même interface.

Toutes les fonctionnalités V2 sont conservées :
- Multi-stratégies avec vote
- Multi-timeframes
- Filtres de volatilité et corrélation
- Trailing stop + break-even
- Paper trading mode
- Journal automatique
- Circuit breaker intelligent
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

from app.core.config_manager import config_manager, SymbolConfig
from app.core.strategies import (
    StrategyVoter, MarketData, Signal, create_default_voter
)
from app.core.market_filters import (
    VolatilityFilter, CorrelationFilter, CircuitBreaker, CircuitBreakerLevel
)
from app.core.paper_trading import PaperTradingEngine
from app.core.trade_journal import TradeJournal, TradeJournalEntry
from app.brokers import (
    BrokerAdapter, BrokerType, create_broker_adapter,
    OrderType, Position as BrokerPosition, BrokerNotInstalledError,
)

# Import optionnel des alertes Telegram
try:
    from bot.telegram_alerts import AlertSystem, AlertLevel
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    AlertSystem = None
    AlertLevel = None


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
    message: str = ""


@dataclass
class ManagedPositionInfo:
    """État de gestion d'une position (simplifié)"""
    ticket: int
    symbol: str
    direction: int
    entry_price: float
    initial_risk: float
    current_sl: float
    phase: str = "opened"           # "opened", "at_breakeven", "trailing"
    peak_profit: float = 0.0


class TradingEngineV3(QObject):
    """Moteur de trading V3 avec abstraction broker"""

    # Signaux Qt
    status_changed = pyqtSignal(object)
    log_message = pyqtSignal(str, str)
    position_opened = pyqtSignal(dict)
    position_closed = pyqtSignal(dict)
    account_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    paper_account_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.config = config_manager.config
        self.state = BotState.STOPPED
        # Respect du mode par défaut défini dans la config (paper par défaut).
        self.mode = self.config.default_mode if self.config.default_mode in ("live", "paper") else "paper"
        self._stop_event = Event()
        self._pause_event = Event()
        self._thread: Optional[Thread] = None

        # Broker adapter
        self.broker: Optional[BrokerAdapter] = None

        # État
        self.today_trades = 0
        self.today_pnl = 0.0
        self.today_start_balance = 0.0
        self.current_day: Optional[datetime] = None
        self.last_signal_time: Optional[datetime] = None
        self.last_tick_time: Optional[datetime] = None

        # Composants avancés
        self.voter: Optional[StrategyVoter] = None
        self.managed_positions: dict = {}  # ticket -> ManagedPositionInfo
        self.volatility_filter = VolatilityFilter()
        self.correlation_filter = CorrelationFilter()
        self.circuit_breaker = CircuitBreaker(
            max_drawdown_percent=15.0,
            max_consecutive_losses=self.config.strategy.max_consecutive_losses + 2,
        )

        # Paper trading
        data_dir = Path(config_manager.app_data_dir) / 'paper'
        self.paper_engine = PaperTradingEngine(
            initial_balance=self.config.initial_capital,
            data_dir=data_dir,
        )

        # Journal
        self.journal = TradeJournal(Path(config_manager.app_data_dir) / 'journal')

        # Dépendances externes
        self._economic_calendar = None
        self._telegram_alerts: Optional[AlertSystem] = None
        self._last_daily_report_date = None
        self._reload_telegram()

        # Logger
        self._setup_logger()

    def _reload_telegram(self):
        """Recharge la config Telegram (appelé au démarrage et après save)"""
        if not TELEGRAM_AVAILABLE:
            return
        cfg = self.config.telegram
        if cfg.enabled and cfg.token and cfg.chat_id:
            try:
                self._telegram_alerts = AlertSystem(token=cfg.token, chat_id=cfg.chat_id)
            except Exception:
                self._telegram_alerts = None
        else:
            self._telegram_alerts = None

    def reload_telegram(self):
        """API publique pour rafraîchir depuis la UI"""
        self._reload_telegram()
        if self._telegram_alerts:
            self._log('info', 'Notifications Telegram activées')
        else:
            self._log('info', 'Notifications Telegram désactivées')

    def _setup_logger(self):
        self.logger = logging.getLogger('TradingEngineV3')
        self.logger.setLevel(logging.DEBUG)  # DEBUG pour voir chaque analyse
        if not self.logger.handlers:
            log_file = config_manager.get_log_file('trading')
            handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level: str, message: str):
        getattr(self.logger, level.lower(), self.logger.info)(message)
        # Émettre vers l'UI (info et au-dessus seulement pour ne pas saturer)
        if level.lower() in ('info', 'warning', 'error', 'critical', 'debug'):
            self.log_message.emit(level, message)

    # ========================================================================
    # BROKER MANAGEMENT
    # ========================================================================

    def _create_broker(self) -> bool:
        """Crée l'adapter broker selon la config"""
        broker_name = self.config.broker.selected.lower()
        type_map = {
            "mt5": BrokerType.MT5,
            "xtb": BrokerType.XTB,
            "ib": BrokerType.INTERACTIVE_BROKERS,
            "ctrader": BrokerType.CTRADER,
            "binance": BrokerType.BINANCE,
            "bybit": BrokerType.BYBIT,
            "kraken": BrokerType.KRAKEN,
            "coinbase": BrokerType.COINBASE,
        }
        broker_type = type_map.get(broker_name)
        if broker_type is None:
            self._log('error', f"Broker inconnu : {broker_name}")
            return False

        try:
            self.broker = create_broker_adapter(broker_type)
            if self.broker is None:
                return False

            # Avertir si expérimental
            from app.brokers import BrokerSupportLevel
            if self.broker.capabilities.support_level == BrokerSupportLevel.EXPERIMENTAL:
                self._log('warning',
                         f"Broker {self.broker.capabilities.name} : support expérimental")
                for warning in self.broker.capabilities.warnings:
                    self._log('warning', f"  • {warning}")

            return True
        except BrokerNotInstalledError as e:
            self._log('error', str(e))
            return False
        except Exception as e:
            self._log('error', f"Erreur création broker : {e}")
            return False

    def _connect_broker(self) -> bool:
        """Connecte le broker selon sa config"""
        if self.broker is None:
            return False

        broker_name = self.config.broker.selected.lower()
        try:
            if broker_name == "mt5":
                cfg = self.config.broker.mt5
                ok = self.broker.connect(
                    auto_detect=cfg.auto_detect,
                    terminal_path=cfg.terminal_path,
                    login=cfg.login, password=cfg.password, server=cfg.server,
                )
            elif broker_name == "xtb":
                cfg = self.config.broker.xtb
                if not cfg.user_id or not cfg.password:
                    self._log('error',
                             "XTB : user_id et password requis. "
                             "Configurez dans Paramètres > Broker.")
                    return False
                ok = self.broker.connect(
                    user_id=cfg.user_id, password=cfg.password, demo=cfg.demo,
                )
            elif broker_name == "ib":
                cfg = self.config.broker.ib
                ok = self.broker.connect(
                    host=cfg.host, port=cfg.port, client_id=cfg.client_id,
                )
            elif broker_name == "ctrader":
                cfg = self.config.broker.ctrader
                ok = self.broker.connect(
                    client_id=cfg.client_id, client_secret=cfg.client_secret,
                    access_token=cfg.access_token, account_id=cfg.account_id,
                    demo=cfg.demo,
                )
            elif broker_name in ("binance", "bybit", "kraken", "coinbase"):
                cfg = getattr(self.config.broker, broker_name)
                ok = self.broker.connect(
                    api_key=cfg.api_key, api_secret=cfg.api_secret,
                    passphrase=cfg.passphrase, sandbox=cfg.sandbox,
                )
            else:
                return False

            if ok:
                info = self.broker.get_account_info()
                if info:
                    self._log('info',
                             f"Connecté : {info.name} ({info.server}) — "
                             f"{info.balance:.2f} {info.currency}")
                    self.today_start_balance = info.balance
                    self.circuit_breaker.peak_equity = info.equity
                return True
            else:
                self._log('error', f"Échec connexion : {self.broker.get_last_error()}")
                return False
        except Exception as e:
            self._log('error', f"Exception connexion : {e}")
            self.circuit_breaker.record_error()
            return False

    # ========================================================================
    # MODE
    # ========================================================================

    def set_mode(self, mode: str):
        if self.state != BotState.STOPPED:
            self._log('warning', "Impossible de changer de mode pendant que le bot tourne")
            return False
        if mode not in ('live', 'paper'):
            return False
        self.mode = mode
        self._log('info', f"Mode : {mode}")
        return True

    # ========================================================================
    # CONTRÔLE
    # ========================================================================

    def start(self) -> bool:
        if self.state == BotState.RUNNING:
            return False

        self.voter = create_default_voter(self.config)
        self._log('info', f"Démarrage ({self.mode}) — "
                          f"{len(self.voter.strategies)} stratégies chargées")
        self._stop_event.clear()
        self._pause_event.clear()
        self._set_state(BotState.STARTING)

        # Connexion broker (requis dans les deux modes pour les données de marché)
        broker_ok = False
        if self._create_broker():
            broker_ok = self._connect_broker()
            if not broker_ok:
                err = self.broker.get_last_error() if self.broker else "Raison inconnue"
                self._log('error',
                         f"Connexion MT5 échouée : {err}\n"
                         f"Vérifiez que MetaTrader 5 est ouvert et connecté à un compte.")

        if self.mode == "live":
            if not broker_ok:
                self._set_state(BotState.ERROR)
                return False
            self._log('info', "Mode LIVE — les ordres seront envoyés au broker")
        else:
            if broker_ok:
                self._log('info',
                         f"Mode PAPER — les ordres sont simulés, "
                         f"les données viennent de MT5")
            else:
                self._log('warning',
                         "Mode PAPER sans broker — données de marché non disponibles. "
                         "Lancez MetaTrader 5 et redémarrez le bot pour recevoir les signaux.")
            self._log('info', f"Capital virtuel : "
                              f"{self.paper_engine.account.balance:,.2f} "
                              f"{self.paper_engine.account.currency}")

        self._thread = Thread(target=self._run_loop, daemon=True, name="TradingEngineV3")
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
                # Pour MT5 : appeler shutdown() complet (pas juste disconnect)
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
            self._log('warning', "Circuit breaker activé - reset requis avant reprise")
            return
        self._pause_event.clear()
        self._set_state(BotState.RUNNING)

    def reset_circuit_breaker(self):
        self.circuit_breaker.reset()
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
            'at_breakeven': sum(1 for p in self.managed_positions.values()
                                if p.phase == 'at_breakeven'),
            'trailing': sum(1 for p in self.managed_positions.values()
                           if p.phase == 'trailing'),
            'new': sum(1 for p in self.managed_positions.values()
                      if p.phase == 'opened'),
        }

        return BotStatus(
            state=self.state,
            mode=self.mode,
            broker=broker_name,
            connected=connected,
            last_tick_time=self.last_tick_time,
            last_signal_time=self.last_signal_time,
            active_symbols=[s.symbol for s in self.config.symbols if s.enabled],
            open_positions=open_positions,
            managed_positions=managed_stats,
            today_trades=self.today_trades,
            today_pnl=self.today_pnl,
            consecutive_losses=self.circuit_breaker.consecutive_losses,
            circuit_breaker_level=cb_status.level.value,
            message=message,
        )

    # ========================================================================
    # BOUCLE PRINCIPALE
    # ========================================================================

    def _run_loop(self):
        self._set_state(BotState.RUNNING)

        while not self._stop_event.is_set():
            try:
                self.last_tick_time = datetime.now()

                # Circuit breaker check
                cb = self.circuit_breaker.check()
                if cb.level == CircuitBreakerLevel.HALT:
                    if self.state != BotState.HALTED:
                        self._log('error', f"Circuit breaker HALT : {', '.join(cb.reasons)}")
                        self._set_state(BotState.HALTED)
                        # Alerte Telegram
                        if self._telegram_alerts:
                            try:
                                self._telegram_alerts.send(
                                    f"*CIRCUIT BREAKER ACTIVÉ*\n\n"
                                    f"Le bot a été arrêté automatiquement.\n\n"
                                    f"Raisons :\n" + "\n".join(f"• {r}" for r in cb.reasons) +
                                    f"\n\n*Action requise :* reset manuel dans l'application.",
                                    level=AlertLevel.CRITICAL if AlertLevel else None,
                                )
                            except Exception:
                                pass
                    self._stop_event.wait(10)
                    continue

                # Reset quotidien
                self._check_new_day()

                # Rapport journalier Telegram
                self._check_daily_report()

                # Mise à jour compte
                self._update_account_info()

                # Gérer positions
                if self.mode == "live":
                    self._manage_positions()
                else:
                    self._manage_paper_positions()

                # Chercher nouveaux signaux
                if not self._pause_event.is_set() and self.state == BotState.RUNNING:
                    for symbol_config in self.config.symbols:
                        if not symbol_config.enabled:
                            continue
                        if self._stop_event.is_set():
                            break
                        self._process_symbol(symbol_config)

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

    def _check_daily_report(self):
        """Envoie le rapport journalier à l'heure configurée"""
        if not self._telegram_alerts:
            return
        if not self.config.telegram.alert_daily_report:
            return

        now = datetime.now()
        target_hour = self.config.telegram.daily_report_hour
        today = now.date()

        # Une seule fois par jour, à l'heure cible
        if (now.hour == target_hour and
                self._last_daily_report_date != today and
                self.today_trades > 0):
            try:
                balance = 0.0
                if self.mode == "live" and self.broker:
                    info = self.broker.get_account_info()
                    if info:
                        balance = info.balance
                else:
                    balance = self.paper_engine.account.balance

                # Calcul win rate du jour depuis le journal
                today_trades = [
                    e for e in self.journal.get_all(only_closed=True)
                    if e.exit_time and e.exit_time.date() == today
                ]
                wins = sum(1 for t in today_trades if t.profit > 0)
                win_rate = (wins / len(today_trades) * 100) if today_trades else 0

                self._telegram_alerts.alert_daily_report(
                    trades=self.today_trades,
                    pnl=self.today_pnl,
                    win_rate=win_rate,
                    balance=balance,
                )
                self._last_daily_report_date = today
            except Exception as e:
                self._log('warning', f"Erreur rapport journalier : {e}")

    def _update_account_info(self):
        if self.mode == "live" and self.broker:
            info = self.broker.get_account_info()
            if info:
                self.circuit_breaker.update_equity(info.equity)
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
            self.paper_account_updated.emit({
                'balance': self.paper_engine.account.balance,
                'equity': self.paper_engine.account.equity,
                'currency': self.paper_engine.account.currency,
                'open_trades': len(self.paper_engine.open_trades),
            })

    def _manage_positions(self):
        """Gère les positions ouvertes (break-even, trailing)"""
        if not self.broker or not self.broker.capabilities.supports_trailing_stop:
            return

        try:
            positions = self.broker.get_positions(magic=self.config.strategy.magic_number)
            open_tickets = {p.ticket for p in positions}

            # Détecter les positions fermées (présentes avant, absentes maintenant)
            closed_tickets = [t for t in self.managed_positions if t not in open_tickets]
            for ticket in closed_tickets:
                managed = self.managed_positions[ticket]
                # Récupérer le résultat depuis le journal pour avoir le P&L
                self._handle_live_position_closed(ticket, managed)
                del self.managed_positions[ticket]

            # Découvrir les nouvelles
            for p in positions:
                if p.ticket not in self.managed_positions:
                    self.managed_positions[p.ticket] = ManagedPositionInfo(
                        ticket=p.ticket, symbol=p.symbol, direction=p.direction,
                        entry_price=p.entry_price,
                        initial_risk=abs(p.entry_price - p.stop_loss),
                        current_sl=p.stop_loss,
                    )

            # Gérer chacune
            for p in positions:
                self._manage_single_position(p)
        except Exception as e:
            self._log('warning', f"Erreur gestion positions : {e}")

    def _handle_live_position_closed(self, ticket: int, managed: ManagedPositionInfo):
        """Appelé quand une position disparaît des positions ouvertes (live)"""
        # Tenter de récupérer le P&L depuis l'historique du broker
        try:
            # Note : idéalement on récupèrerait depuis broker.get_history_deal()
            # mais pour simplicité, on émet juste l'événement
            self._log('info', f"Position {ticket} fermée ({managed.symbol})")

            self.position_closed.emit({
                'symbol': managed.symbol,
                'profit': 0,  # P&L non récupérable ici sans history
                'reason': 'Closed',
            })

            # Alerte Telegram (générique - on n'a pas le P&L exact ici)
            if self._telegram_alerts and self.config.telegram.alert_position_close:
                try:
                    self._telegram_alerts.send(
                        f"*Position fermée*\n\n"
                        f"📊 {managed.symbol}\n"
                        f"Ticket : {ticket}\n"
                        f"Consultez l'historique de votre broker pour le P&L.",
                        level=AlertLevel.INFO if AlertLevel else None,
                    )
                except Exception:
                    pass
        except Exception as e:
            self._log('warning', f"Erreur handle close : {e}")

    def _manage_single_position(self, position: BrokerPosition):
        """Applique break-even et trailing stop à une position"""
        managed = self.managed_positions.get(position.ticket)
        if managed is None or managed.initial_risk <= 0:
            return

        # Récupérer le prix actuel
        tick = self.broker.get_tick(position.symbol)
        if tick is None:
            return

        current_price = tick.bid if position.direction == 1 else tick.ask

        # Profit en unités de prix
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
                    self._log('info',
                             f"✓ Position {position.ticket} : break-even @ {new_sl:.5f}")

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
                        self._log('info',
                                 f"↗ Position {position.ticket} : trailing → {new_sl:.5f}")
            else:
                new_sl = current_price + trail_distance
                if new_sl < managed.current_sl:
                    result = self.broker.modify_position(position.ticket, stop_loss=new_sl)
                    if result.success:
                        managed.current_sl = new_sl
                        self._log('info',
                                 f"↘ Position {position.ticket} : trailing → {new_sl:.5f}")

    def _manage_paper_positions(self):
        """Met à jour les positions paper avec les prix réels"""
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
            if trade.profit > 0:
                self.circuit_breaker.record_win()
            else:
                self.circuit_breaker.record_loss()
            self.journal.record_exit(
                ticket=trade.ticket, exit_price=trade.exit_price or 0,
                exit_reason=trade.exit_reason, profit=trade.profit,
                capital=self.paper_engine.account.balance,
            )
            self.position_closed.emit({
                'symbol': trade.symbol, 'profit': trade.profit,
                'reason': trade.exit_reason,
            })

            # Alerte Telegram à la clôture
            if self._telegram_alerts and self.config.telegram.alert_position_close:
                try:
                    self._telegram_alerts.alert_position_closed(
                        symbol=trade.symbol, profit=trade.profit,
                        reason=trade.exit_reason,
                    )
                except Exception:
                    pass

    # ========================================================================
    # TRAITEMENT D'UN SYMBOLE
    # ========================================================================

    def _process_symbol(self, symbol_config: SymbolConfig):
        symbol = symbol_config.symbol

        # Activer le symbole dans MT5 (ne bloque pas si échec)
        if self.broker:
            self.broker.select_symbol(symbol)

        data = self._get_market_data(symbol, symbol_config.timeframe)
        if data is None:
            self._log('debug', f'{symbol}: données non disponibles')
            return

        if not self._is_safe_to_trade(symbol, data):
            return  # _is_safe_to_trade loggue déjà la raison

        if self._has_open_position(symbol):
            self._log('debug', f'{symbol}: position déjà ouverte, skip')
            return

        result = self.voter.vote(data)

        # Toujours loguer le résultat du vote pour debug
        buy_s = result.buy_votes
        sell_s = result.sell_votes
        self._log('debug',
                  f'{symbol}: vote → {result.final_signal.name} '
                  f'(buy={buy_s}, sell={sell_s}, conf={result.confidence:.2f})')

        if result.final_signal == Signal.NONE:
            return

        open_positions = self._get_open_positions_summary()
        direction = 1 if result.final_signal == Signal.BUY else -1

        # Filtre corrélation
        if self.config.strategy.use_correlation_filter:
            corr_ok, corr_reason = self._check_correlation(
                symbol, direction, open_positions
            )
            if not corr_ok:
                self._log('info', f'{symbol}: bloqué corrélation ({corr_reason})')
                return

        self.last_signal_time = datetime.now()
        self._log('info',
                  f'📈 SIGNAL {result.final_signal.name} sur {symbol} — '
                  f'{result.decision_reason} (conf={result.confidence:.2f})')

        self._execute_trade(symbol, direction, result, data)

    def _check_correlation(self, new_symbol: str, new_direction: int,
                            open_positions: List[Tuple[str, int]]) -> Tuple[bool, str]:
        """Vérifie la corrélation via les données du broker"""
        for open_symbol, open_direction in open_positions:
            if open_symbol == new_symbol:
                continue
            # Récupérer les closes pour corrélation
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

    def _get_market_data(self, symbol: str, timeframe_str: str) -> Optional[MarketData]:
        if not self.broker:
            return None

        # Demander 250 bougies mais accepter dès 50 (minimum pour les indicateurs)
        data = self.broker.get_candles_arrays(symbol, timeframe_str, 250)
        if data is None:
            self._log('warning', f'{symbol}: impossible de récupérer les données ({self.broker.get_last_error()})')
            return None

        n = len(data['close'])
        if n < 50:
            self._log('warning', f'{symbol}: seulement {n} bougies disponibles (minimum 50 requis)')
            return None

        if n < 210:
            # Pas assez pour EMA200, on avertit mais on continue
            self._log('info', f'{symbol}: {n} bougies (EMA200 imprécise, mais on continue)')

        # Timeframe supérieur pour confirmation multi-TF
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

    def _is_safe_to_trade(self, symbol: str, data: MarketData) -> bool:
        if self.circuit_breaker.consecutive_losses >= self.config.strategy.max_consecutive_losses:
            return False

        if self.mode == "live" and self.today_start_balance > 0 and self.broker:
            info = self.broker.get_account_info()
            if info:
                daily_loss_pct = ((self.today_start_balance - info.balance)
                                  / self.today_start_balance * 100)
                if daily_loss_pct >= self.config.strategy.max_daily_loss_percent:
                    return False

        now = datetime.now()
        end_h = self.config.strategy.end_hour
        # end_hour=24 signifie "toujours ouvert" (forex 24h/5)
        if end_h < 24:
            if now.hour < self.config.strategy.start_hour or now.hour >= end_h:
                return False
        elif now.hour < self.config.strategy.start_hour:
            return False
        if now.weekday() == 4 and not self.config.strategy.trade_on_friday:
            return False
        if now.weekday() >= 5:
            return False

        # Volatilité — respecte le flag de config
        if self.config.strategy.use_volatility_filter:
            vol = self.volatility_filter.analyze(data.highs, data.lows, data.closes)
            if not vol.safe_to_trade:
                self._log('info', f'{symbol} : volatilité bloque ({vol.reason})')
                return False

        # News
        if self.config.news.enabled and not self._check_news_filter(symbol):
            return False

        # Spread
        if self.mode == "live" and self.broker:
            tick = self.broker.get_tick(symbol)
            sym_info = self.broker.get_symbol_info(symbol)
            if tick and sym_info and sym_info.point > 0:
                spread_points = (tick.ask - tick.bid) / sym_info.point
                if spread_points > 30:
                    return False

        return True

    def _check_news_filter(self, symbol: str) -> bool:
        if self._economic_calendar is None:
            try:
                from bot.economic_calendar import EconomicCalendar
                self._economic_calendar = EconomicCalendar()
            except ImportError:
                return True
        try:
            safe, event = self._economic_calendar.is_safe_to_trade(symbol)
            if not safe:
                self._log('info', f'News filtrée pour {symbol}')
            return safe
        except Exception:
            return True

    def _has_open_position(self, symbol: str) -> bool:
        if self.mode == "live" and self.broker:
            positions = self.broker.get_positions(
                symbol=symbol, magic=self.config.strategy.magic_number
            )
            return len(positions) > 0
        else:
            return any(t.symbol == symbol for t in self.paper_engine.open_trades.values())

    def _get_open_positions_summary(self) -> List[Tuple[str, int]]:
        if self.mode == "live" and self.broker:
            positions = self.broker.get_positions(magic=self.config.strategy.magic_number)
            return [(p.symbol, p.direction) for p in positions]
        else:
            return [(t.symbol, t.direction) for t in self.paper_engine.open_trades.values()]

    # ========================================================================
    # EXÉCUTION
    # ========================================================================

    def _execute_trade(self, symbol: str, direction: int, vote_result, data: MarketData):
        # Mode lecture seule : on log le signal mais on ne trade pas
        if getattr(self.config.strategy, 'read_only_mode', False):
            dir_text = "BUY" if direction > 0 else "SELL"
            self._log('info',
                     f"[READ-ONLY] Signal {dir_text} sur {symbol} ignoré "
                     f"(mode lecture seule activé)")
            return

        if self.mode == "live":
            self._execute_live_trade(symbol, direction, vote_result, data)
        else:
            self._execute_paper_trade(symbol, direction, vote_result, data)

    def _execute_live_trade(self, symbol, direction, vote_result, data):
        if not self.broker:
            return
        sym_info = self.broker.get_symbol_info(symbol)
        tick = self.broker.get_tick(symbol)
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

        lot_size = self._calculate_lot_size(sym_info, stop_distance)
        if lot_size <= 0:
            return

        result = self.broker.open_position(
            symbol=symbol, order_type=order_type,
            volume=lot_size, stop_loss=sl, take_profit=tp,
            magic=self.config.strategy.magic_number,
            comment='SafeTrendBotV3',
        )

        if result.success:
            dir_str = "BUY" if direction == 1 else "SELL"
            actual_price = result.filled_price or price
            self._log('info', f'{dir_str} {symbol} @ {actual_price:.5f} ({lot_size} lots)')
            self.today_trades += 1

            self.managed_positions[result.ticket] = ManagedPositionInfo(
                ticket=result.ticket, symbol=symbol, direction=direction,
                entry_price=actual_price,
                initial_risk=abs(actual_price - sl),
                current_sl=sl,
            )

            self._journal_entry(
                ticket=result.ticket, symbol=symbol, direction=direction,
                volume=lot_size, entry=actual_price, sl=sl, tp=tp,
                vote_result=vote_result, atr_val=atr_val, data=data,
            )

            self.position_opened.emit({
                'symbol': symbol, 'direction': dir_str, 'price': actual_price,
                'volume': lot_size, 'sl': sl, 'tp': tp,
            })

            # Alerte Telegram
            if self._telegram_alerts and self.config.telegram.alert_position_open:
                try:
                    self._telegram_alerts.alert_position_opened(
                        symbol=symbol, direction=dir_str, volume=lot_size,
                        entry=actual_price, sl=sl, tp=tp,
                    )
                except Exception:
                    pass
        else:
            self._log('error', f'Ordre refusé : {result.error_message}')
            self.circuit_breaker.record_error()

    def _execute_paper_trade(self, symbol, direction, vote_result, data):
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

        risk_amount = self.paper_engine.account.balance * self.config.strategy.risk_percent / 100
        units = risk_amount / stop_distance if stop_distance > 0 else 0
        lot_size = max(0.01, round(units / 100000, 2))

        trade = self.paper_engine.open_trade(
            symbol=symbol, direction=direction, volume=lot_size,
            entry_price=price, stop_loss=sl, take_profit=tp,
        )
        self.today_trades += 1

        self._journal_entry(
            ticket=trade.ticket, symbol=symbol, direction=direction,
            volume=lot_size, entry=price, sl=sl, tp=tp,
            vote_result=vote_result, atr_val=atr_val, data=data,
        )

        dir_str = "BUY" if direction == 1 else "SELL"
        self._log('info', f'[PAPER] {dir_str} {symbol} @ {price:.5f} ({lot_size} lots)')
        self.position_opened.emit({
            'symbol': symbol, 'direction': dir_str, 'price': price,
            'volume': lot_size, 'sl': sl, 'tp': tp, 'paper': True,
        })

    def _journal_entry(self, ticket, symbol, direction, volume, entry, sl, tp,
                       vote_result, atr_val, data):
        try:
            balance = 0.0
            equity = 0.0
            if self.mode == "live" and self.broker:
                info = self.broker.get_account_info()
                if info:
                    balance = info.balance
                    equity = info.equity
            else:
                balance = self.paper_engine.account.balance
                equity = self.paper_engine.account.equity

            vol_status = self.volatility_filter.analyze(data.highs, data.lows, data.closes)

            entry_journal = TradeJournalEntry(
                ticket=ticket, symbol=symbol,
                timeframe=data.timeframe,
                direction="BUY" if direction == 1 else "SELL",
                volume=volume, entry_price=entry, entry_time=datetime.now(),
                stop_loss=sl, take_profit=tp,
                entry_balance=balance, entry_equity=equity,
                atr_value=atr_val, volatility_regime=vol_status.regime.value,
                confidence_score=vote_result.confidence,
                strategies_agreed=[s.strategy_name for s in vote_result.individual_signals
                                   if s.signal.value == direction],
                buy_votes=vote_result.buy_votes, sell_votes=vote_result.sell_votes,
                indicators={'atr': atr_val},
            )
            self.journal.record_entry(entry_journal)
        except Exception as e:
            self._log('warning', f'Erreur journal : {e}')

    @staticmethod
    def _get_higher_tf(tf: str) -> str:
        hierarchy = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']
        try:
            idx = hierarchy.index(tf.upper())
            return hierarchy[min(idx + 2, len(hierarchy) - 1)]
        except ValueError:
            return 'D1'

    def _calculate_atr(self, data: MarketData) -> float:
        from app.core.strategies import atr
        result = atr(data.highs, data.lows, data.closes, self.config.strategy.atr_period)
        return float(result[-1]) if len(result) > 0 else 0.0

    def _calculate_lot_size(self, sym_info, stop_distance: float) -> float:
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
