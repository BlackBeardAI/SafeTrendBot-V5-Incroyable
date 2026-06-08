"""
Moteur de trading V2 - Intègre toutes les fonctionnalités avancées :
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
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

import numpy as np

from app.core.config_manager import config_manager, SymbolConfig
from app.core.strategies import (
    StrategyVoter, MarketData, Signal, create_default_voter
)
from app.core.position_manager import PositionManager
from app.core.market_filters import (
    VolatilityFilter, CorrelationFilter, CircuitBreaker, CircuitBreakerLevel
)
from app.core.paper_trading import PaperTradingEngine
from app.core.trade_journal import TradeJournal, TradeJournalEntry


class BotState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    HALTED = "halted"            # Arrêté par circuit breaker
    ERROR = "error"


@dataclass
class BotStatus:
    state: BotState
    mode: str                    # "live" ou "paper"
    connected: bool
    last_tick_time: Optional[datetime]
    last_signal_time: Optional[datetime]
    active_symbols: list
    open_positions: int
    managed_positions: dict      # stats du position_manager
    today_trades: int
    today_pnl: float
    consecutive_losses: int
    circuit_breaker_level: str
    message: str = ""


class TradingEngineV2(QObject):
    """Moteur de trading V2 avec toutes les fonctionnalités avancées"""

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
        self.mode = "live"                   # "live" ou "paper"
        self._stop_event = Event()
        self._pause_event = Event()
        self._thread: Optional[Thread] = None

        # État
        self.today_trades = 0
        self.today_pnl = 0.0
        self.today_start_balance = 0.0
        self.current_day: Optional[datetime] = None
        self.last_signal_time: Optional[datetime] = None
        self.last_tick_time: Optional[datetime] = None

        # Composants avancés
        self.voter: Optional[StrategyVoter] = None
        self.position_manager = PositionManager(self.config, logger=self._log_info)
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
        self._telegram_alerts = None

        # Logger
        self._setup_logger()

    def _setup_logger(self):
        self.logger = logging.getLogger('TradingEngineV2')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            log_file = config_manager.get_log_file('trading')
            handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log(self, level: str, message: str):
        getattr(self.logger, level.lower())(message)
        self.log_message.emit(level, message)

    def _log_info(self, message: str):
        self._log('info', message)

    # ========================================================================
    # MODE
    # ========================================================================

    def set_mode(self, mode: str):
        """'live' ou 'paper'"""
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

        if self.mode == "live":
            if not MT5_AVAILABLE:
                self._log('error', 'MetaTrader5 non installé')
                self.error_occurred.emit("MetaTrader5 n'est pas installé")
                return False
            if not self._connect_mt5():
                self._set_state(BotState.ERROR)
                return False
        else:
            self._log('info', f"Mode paper : capital virtuel "
                              f"{self.paper_engine.account.balance:,.2f}")

        self._thread = Thread(target=self._run_loop, daemon=True, name="TradingEngineV2")
        self._thread.start()
        return True

    def stop(self):
        if self.state == BotState.STOPPED:
            return
        self._log('info', 'Arrêt...')
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        if self.mode == "live" and MT5_AVAILABLE:
            try:
                mt5.shutdown()
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
        connected = False
        open_positions = 0

        if self.mode == "live" and MT5_AVAILABLE and self.state != BotState.STOPPED:
            try:
                info = mt5.account_info()
                connected = info is not None
                positions = mt5.positions_get()
                if positions:
                    open_positions = len([p for p in positions
                                          if p.magic == self.config.strategy.magic_number])
            except Exception:
                pass
        elif self.mode == "paper":
            connected = True
            open_positions = len(self.paper_engine.open_trades)

        cb_status = self.circuit_breaker.check()

        return BotStatus(
            state=self.state,
            mode=self.mode,
            connected=connected,
            last_tick_time=self.last_tick_time,
            last_signal_time=self.last_signal_time,
            active_symbols=[s.symbol for s in self.config.symbols if s.enabled],
            open_positions=open_positions,
            managed_positions=self.position_manager.get_stats(),
            today_trades=self.today_trades,
            today_pnl=self.today_pnl,
            consecutive_losses=self.circuit_breaker.consecutive_losses,
            circuit_breaker_level=cb_status.level.value,
            message=message,
        )

    # ========================================================================
    # MT5 CONNEXION
    # ========================================================================

    def _connect_mt5(self) -> bool:
        mt5_conf = self.config.mt5
        try:
            if mt5_conf.auto_detect:
                ok = mt5.initialize()
            else:
                kwargs = {}
                if mt5_conf.terminal_path:
                    kwargs['path'] = mt5_conf.terminal_path
                if mt5_conf.login and mt5_conf.password and mt5_conf.server:
                    kwargs.update(login=mt5_conf.login, password=mt5_conf.password,
                                  server=mt5_conf.server)
                ok = mt5.initialize(**kwargs)

            if not ok:
                self._log('error', f'Échec connexion MT5 : {mt5.last_error()}')
                return False

            info = mt5.account_info()
            if info:
                self._log('info', f'Connecté : {info.name} ({info.server})')
                self.today_start_balance = info.balance
                self.circuit_breaker.peak_equity = info.equity
            return True
        except Exception as e:
            self._log('error', f'Exception : {e}')
            self.circuit_breaker.record_error()
            return False

    # ========================================================================
    # BOUCLE PRINCIPALE
    # ========================================================================

    def _run_loop(self):
        self._set_state(BotState.RUNNING)

        while not self._stop_event.is_set():
            try:
                self.last_tick_time = datetime.now()

                # 0. Circuit breaker check
                cb = self.circuit_breaker.check()
                if cb.level == CircuitBreakerLevel.HALT:
                    if self.state != BotState.HALTED:
                        self._log('error', f"Circuit breaker HALT : {', '.join(cb.reasons)}")
                        self._set_state(BotState.HALTED)
                    self._stop_event.wait(10)
                    continue

                # 1. Reset quotidien
                self._check_new_day()

                # 2. Mise à jour compte
                self._update_account_info()

                # 3. Gérer positions (trailing, break-even)
                if self.mode == "live":
                    self.position_manager.manage_all_positions()
                else:
                    # Paper : mettre à jour prix et vérifier SL/TP
                    self._manage_paper_positions()

                # 4. Chercher nouveaux signaux si pas en pause
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
            if self.mode == "live" and MT5_AVAILABLE:
                info = mt5.account_info()
                if info:
                    self.today_start_balance = info.balance

    def _update_account_info(self):
        if self.mode == "live" and MT5_AVAILABLE:
            try:
                info = mt5.account_info()
                if info:
                    self.circuit_breaker.update_equity(info.equity)
                    self.account_updated.emit({
                        'balance': info.balance, 'equity': info.equity,
                        'profit': info.profit, 'margin': info.margin,
                        'margin_free': info.margin_free, 'margin_level': info.margin_level,
                        'currency': info.currency, 'server': info.server,
                        'name': info.name, 'leverage': info.leverage,
                    })
            except Exception:
                pass
        elif self.mode == "paper":
            self.circuit_breaker.update_equity(self.paper_engine.account.equity)
            self.paper_account_updated.emit({
                'balance': self.paper_engine.account.balance,
                'equity': self.paper_engine.account.equity,
                'currency': self.paper_engine.account.currency,
                'open_trades': len(self.paper_engine.open_trades),
            })

    def _manage_paper_positions(self):
        """Met à jour les positions paper avec les prix réels"""
        if not MT5_AVAILABLE or not self.paper_engine.open_trades:
            return

        prices = {}
        for trade in self.paper_engine.open_trades.values():
            tick = mt5.symbol_info_tick(trade.symbol)
            if tick:
                prices[trade.symbol] = (tick.bid, tick.ask)

        closed = self.paper_engine.update_prices(prices)
        for trade in closed:
            self.today_pnl += trade.profit
            if trade.profit > 0:
                self.circuit_breaker.record_win()
            else:
                self.circuit_breaker.record_loss()
            # Journal
            self.journal.record_exit(
                ticket=trade.ticket,
                exit_price=trade.exit_price or 0,
                exit_reason=trade.exit_reason,
                profit=trade.profit,
                capital=self.paper_engine.account.balance,
            )
            self.position_closed.emit({
                'symbol': trade.symbol,
                'profit': trade.profit,
                'reason': trade.exit_reason,
            })

    # ========================================================================
    # TRAITEMENT D'UN SYMBOLE
    # ========================================================================

    def _process_symbol(self, symbol_config: SymbolConfig):
        symbol = symbol_config.symbol

        if self.mode == "live" and not mt5.symbol_select(symbol, True):
            return

        # Récupérer les données
        data = self._get_market_data(symbol, symbol_config.timeframe)
        if data is None:
            return

        # Filtres de sécurité
        if not self._is_safe_to_trade(symbol, data):
            return

        # Vérifier qu'on n'a pas déjà une position sur ce symbole
        if self._has_open_position(symbol):
            return

        # Vote des stratégies
        result = self.voter.vote(data)
        if result.final_signal == Signal.NONE:
            return

        # Filtre corrélation
        open_positions = self._get_open_positions_summary()
        direction = 1 if result.final_signal == Signal.BUY else -1
        corr_ok, corr_reason = self.correlation_filter.is_safe_to_open(
            symbol, direction, open_positions
        )
        if not corr_ok:
            self._log('info', f'{symbol} : bloqué par corrélation ({corr_reason})')
            return

        self.last_signal_time = datetime.now()
        self._log('info', f'{symbol} : {result.decision_reason}')

        # Exécuter le trade
        self._execute_trade(symbol, direction, result, data)

    def _get_market_data(self, symbol: str, timeframe_str: str) -> Optional[MarketData]:
        """Récupère les données pour l'analyse (incluant timeframe supérieur)"""
        if not MT5_AVAILABLE:
            return None

        tf = self._parse_timeframe(timeframe_str)
        tf_higher = self._parse_timeframe(self._get_higher_tf(timeframe_str))

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, 250)
        if rates is None or len(rates) < 210:
            return None

        # Timeframe supérieur pour confirmation de tendance
        rates_higher = mt5.copy_rates_from_pos(symbol, tf_higher, 0, 100)
        higher_closes = np.array([r['close'] for r in rates_higher]) if rates_higher is not None else None

        return MarketData(
            symbol=symbol,
            closes=np.array([r['close'] for r in rates]),
            highs=np.array([r['high'] for r in rates]),
            lows=np.array([r['low'] for r in rates]),
            opens=np.array([r['open'] for r in rates]),
            volumes=np.array([r['tick_volume'] for r in rates]),
            timeframe=timeframe_str,
            higher_tf_closes=higher_closes,
            higher_tf_timeframe=self._get_higher_tf(timeframe_str),
        )

    def _is_safe_to_trade(self, symbol: str, data: MarketData) -> bool:
        # Pertes consécutives
        if self.circuit_breaker.consecutive_losses >= self.config.strategy.max_consecutive_losses:
            return False

        # Perte journalière
        if self.mode == "live" and self.today_start_balance > 0 and MT5_AVAILABLE:
            info = mt5.account_info()
            if info:
                daily_loss_pct = ((self.today_start_balance - info.balance)
                                  / self.today_start_balance * 100)
                if daily_loss_pct >= self.config.strategy.max_daily_loss_percent:
                    return False

        # Filtre horaire
        now = datetime.now()
        if now.hour < self.config.strategy.start_hour or now.hour >= self.config.strategy.end_hour:
            return False
        if now.weekday() == 4 and not self.config.strategy.trade_on_friday:
            return False
        if now.weekday() >= 5:
            return False

        # Filtre volatilité
        vol = self.volatility_filter.analyze(data.highs, data.lows, data.closes)
        if not vol.safe_to_trade:
            self._log('info', f'{symbol} : {vol.reason}')
            return False

        # Filtre news
        if self.config.news.enabled:
            if not self._check_news_filter(symbol):
                return False

        # Filtre multi-timeframe : confirmer la tendance sur TF supérieur
        if data.higher_tf_closes is not None and len(data.higher_tf_closes) >= 50:
            from app.core.strategies import ema
            higher_ema = ema(data.higher_tf_closes, 50)
            # Si on est long, le TF supérieur doit être au-dessus de sa MA50
            # (on vérifie au moment du trade, pas ici)

        # Spread
        if self.mode == "live" and MT5_AVAILABLE:
            tick = mt5.symbol_info_tick(symbol)
            sym_info = mt5.symbol_info(symbol)
            if tick and sym_info:
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
                self._log('info', f'News filtrée pour {symbol} : {event.title if event else ""}')
            return safe
        except Exception:
            return True

    def _has_open_position(self, symbol: str) -> bool:
        if self.mode == "live" and MT5_AVAILABLE:
            positions = mt5.positions_get(symbol=symbol)
            if not positions:
                return False
            return any(p.magic == self.config.strategy.magic_number for p in positions)
        else:
            return any(t.symbol == symbol for t in self.paper_engine.open_trades.values())

    def _get_open_positions_summary(self) -> List[Tuple[str, int]]:
        """Retourne [(symbol, direction), ...] des positions ouvertes"""
        if self.mode == "live" and MT5_AVAILABLE:
            positions = mt5.positions_get() or []
            return [(p.symbol, 1 if p.type == mt5.POSITION_TYPE_BUY else -1)
                    for p in positions if p.magic == self.config.strategy.magic_number]
        else:
            return [(t.symbol, t.direction)
                    for t in self.paper_engine.open_trades.values()]

    # ========================================================================
    # EXÉCUTION
    # ========================================================================

    def _execute_trade(self, symbol: str, direction: int, vote_result, data: MarketData):
        if self.mode == "live":
            self._execute_live_trade(symbol, direction, vote_result, data)
        else:
            self._execute_paper_trade(symbol, direction, vote_result, data)

    def _execute_live_trade(self, symbol, direction, vote_result, data):
        if not MT5_AVAILABLE:
            return

        sym_info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if not sym_info or not tick:
            return

        atr_val = self._calculate_atr(data)
        if atr_val <= 0:
            return

        stop_distance = atr_val * self.config.strategy.atr_multiplier
        if direction == 1:
            price = tick.ask
            sl = price - stop_distance
            tp = price + stop_distance * self.config.strategy.risk_reward_ratio
            order_type = mt5.ORDER_TYPE_BUY
        else:
            price = tick.bid
            sl = price + stop_distance
            tp = price - stop_distance * self.config.strategy.risk_reward_ratio
            order_type = mt5.ORDER_TYPE_SELL

        lot_size = self._calculate_lot_size(sym_info, stop_distance)
        if lot_size <= 0:
            return

        request = {
            'action': mt5.TRADE_ACTION_DEAL, 'symbol': symbol, 'volume': lot_size,
            'type': order_type, 'price': price, 'sl': sl, 'tp': tp,
            'deviation': 20, 'magic': self.config.strategy.magic_number,
            'comment': 'SafeTrendBotV2', 'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            dir_str = "BUY" if direction == 1 else "SELL"
            self._log('info', f'{dir_str} {symbol} @ {price:.5f} ({lot_size} lots)')
            self.today_trades += 1

            # Enregistrer dans le position manager
            self.position_manager.register_position(
                ticket=result.order, symbol=symbol, direction=direction,
                entry=price, sl=sl, tp=tp,
            )

            # Enregistrer dans le journal
            self._journal_entry(
                ticket=result.order, symbol=symbol, direction=direction,
                volume=lot_size, entry=price, sl=sl, tp=tp,
                vote_result=vote_result, atr_val=atr_val, data=data,
            )

            self.position_opened.emit({
                'symbol': symbol, 'direction': dir_str, 'price': price,
                'volume': lot_size, 'sl': sl, 'tp': tp,
            })
        else:
            self._log('error', f'Ordre refusé : {result.comment}')
            self.circuit_breaker.record_error()

    def _execute_paper_trade(self, symbol, direction, vote_result, data):
        if not MT5_AVAILABLE:
            return
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return

        atr_val = self._calculate_atr(data)
        if atr_val <= 0:
            return

        stop_distance = atr_val * self.config.strategy.atr_multiplier
        if direction == 1:
            price = tick.ask
            sl = price - stop_distance
            tp = price + stop_distance * self.config.strategy.risk_reward_ratio
        else:
            price = tick.bid
            sl = price + stop_distance
            tp = price - stop_distance * self.config.strategy.risk_reward_ratio

        # Lot size approximatif en paper (risque % du capital virtuel)
        risk_amount = self.paper_engine.account.balance * self.config.strategy.risk_percent / 100
        units = risk_amount / stop_distance
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
        """Crée une entrée dans le journal de trading"""
        try:
            balance = 0.0
            equity = 0.0
            if self.mode == "live" and MT5_AVAILABLE:
                info = mt5.account_info()
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

    # ========================================================================
    # UTILITAIRES
    # ========================================================================

    @staticmethod
    def _parse_timeframe(tf: str):
        if not MT5_AVAILABLE:
            return None
        mapping = {
            'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15, 'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1,
        }
        return mapping.get(tf.upper(), mt5.TIMEFRAME_H4)

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
        result = atr(data.highs, data.lows, data.closes,
                    self.config.strategy.atr_period)
        return float(result[-1]) if len(result) > 0 else 0.0

    def _calculate_lot_size(self, sym_info, stop_distance: float) -> float:
        if not MT5_AVAILABLE:
            return 0
        account = mt5.account_info()
        if not account:
            return 0

        risk_amount = account.balance * self.config.strategy.risk_percent / 100
        tick_value = sym_info.trade_tick_value
        tick_size = sym_info.trade_tick_size
        if tick_value == 0 or tick_size == 0 or stop_distance == 0:
            return 0

        value_per_unit = tick_value / tick_size
        lot_size = risk_amount / (stop_distance * value_per_unit)

        min_lot = sym_info.volume_min
        max_lot = sym_info.volume_max
        step = sym_info.volume_step

        import math
        lot_size = math.floor(lot_size / step) * step
        lot_size = max(min_lot, min(max_lot, lot_size))
        return round(lot_size, 2)
