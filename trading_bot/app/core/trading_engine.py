"""
Moteur de trading - s'exécute dans un thread séparé
Surveille les marchés, exécute les trades selon la stratégie, gère le risque.
"""

import time
import logging
from threading import Thread, Event
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from app.core.config_manager import config_manager, SymbolConfig


class BotState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class BotStatus:
    state: BotState
    connected: bool
    last_tick_time: Optional[datetime]
    last_signal_time: Optional[datetime]
    active_symbols: list
    open_positions: int
    today_trades: int
    today_pnl: float
    consecutive_losses: int
    message: str = ""


class TradingEngine(QObject):
    """
    Moteur de trading principal.
    Émet des signaux Qt pour mettre à jour l'UI.
    """

    # Signaux Qt pour communication avec l'UI
    status_changed = pyqtSignal(object)          # BotStatus
    log_message = pyqtSignal(str, str)           # level, message
    position_opened = pyqtSignal(dict)
    position_closed = pyqtSignal(dict)
    account_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.config = config_manager.config
        self.state = BotState.STOPPED
        self._stop_event = Event()
        self._pause_event = Event()
        self._thread: Optional[Thread] = None

        # État interne
        self.consecutive_losses = 0
        self.today_trades = 0
        self.today_pnl = 0.0
        self.today_start_balance = 0.0
        self.current_day: Optional[datetime] = None
        self.last_signal_time: Optional[datetime] = None
        self.last_tick_time: Optional[datetime] = None

        # Logger
        self._setup_logger()

        # Dépendances (chargées à la demande)
        self._economic_calendar = None
        self._telegram_alerts = None

    def _setup_logger(self):
        self.logger = logging.getLogger('TradingEngine')
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

    # ========================================================================
    # CONTRÔLE DU BOT
    # ========================================================================

    def start(self) -> bool:
        """Démarre le moteur de trading"""
        if self.state == BotState.RUNNING:
            self._log('warning', 'Le bot est déjà en marche')
            return False

        if not MT5_AVAILABLE:
            self._log('error', 'Package MetaTrader5 non installé')
            self.error_occurred.emit("Le package MetaTrader5 n'est pas installé")
            return False

        self._log('info', 'Démarrage du moteur de trading...')
        self._stop_event.clear()
        self._pause_event.clear()
        self._set_state(BotState.STARTING)

        # Connexion MT5
        if not self._connect_mt5():
            self._set_state(BotState.ERROR)
            return False

        # Démarrage du thread
        self._thread = Thread(target=self._run_loop, daemon=True, name="TradingEngine")
        self._thread.start()
        return True

    def stop(self):
        """Arrête le moteur de trading"""
        if self.state == BotState.STOPPED:
            return
        self._log('info', 'Arrêt du moteur...')
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        if MT5_AVAILABLE:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self._set_state(BotState.STOPPED)
        self._log('info', 'Moteur arrêté')

    def pause(self):
        """Met en pause le trading (ne ferme pas les positions)"""
        self._pause_event.set()
        self._set_state(BotState.PAUSED)
        self._log('info', 'Trading en pause (positions maintenues)')

    def resume(self):
        """Reprend le trading"""
        self._pause_event.clear()
        self._set_state(BotState.RUNNING)
        self._log('info', 'Trading repris')

    def _set_state(self, state: BotState, message: str = ""):
        self.state = state
        status = self.get_status(message)
        self.status_changed.emit(status)

    def get_status(self, message: str = "") -> BotStatus:
        """Retourne l'état actuel du bot"""
        connected = False
        open_positions = 0
        if MT5_AVAILABLE and self.state != BotState.STOPPED:
            try:
                info = mt5.account_info()
                connected = info is not None
                positions = mt5.positions_get()
                if positions:
                    open_positions = len([p for p in positions
                                          if p.magic == self.config.strategy.magic_number])
            except Exception:
                pass

        return BotStatus(
            state=self.state,
            connected=connected,
            last_tick_time=self.last_tick_time,
            last_signal_time=self.last_signal_time,
            active_symbols=[s.symbol for s in self.config.symbols if s.enabled],
            open_positions=open_positions,
            today_trades=self.today_trades,
            today_pnl=self.today_pnl,
            consecutive_losses=self.consecutive_losses,
            message=message,
        )

    # ========================================================================
    # CONNEXION MT5
    # ========================================================================

    def _connect_mt5(self) -> bool:
        """Établit la connexion avec MetaTrader 5"""
        mt5_conf = self.config.mt5
        try:
            if mt5_conf.auto_detect:
                initialized = mt5.initialize()
            else:
                kwargs = {}
                if mt5_conf.terminal_path:
                    kwargs['path'] = mt5_conf.terminal_path
                if mt5_conf.login and mt5_conf.password and mt5_conf.server:
                    kwargs['login'] = mt5_conf.login
                    kwargs['password'] = mt5_conf.password
                    kwargs['server'] = mt5_conf.server
                initialized = mt5.initialize(**kwargs)

            if not initialized:
                error = mt5.last_error()
                self._log('error', f'Échec connexion MT5 : {error}')
                self.error_occurred.emit(f"Connexion MT5 échouée : {error}")
                return False

            account_info = mt5.account_info()
            if account_info:
                self._log('info', f'Connecté : {account_info.name} ({account_info.server})')
                self.today_start_balance = account_info.balance
                self.account_updated.emit({
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'currency': account_info.currency,
                    'server': account_info.server,
                    'name': account_info.name,
                    'leverage': account_info.leverage,
                })
            return True
        except Exception as e:
            self._log('error', f'Exception connexion MT5 : {e}')
            self.error_occurred.emit(str(e))
            return False

    # ========================================================================
    # BOUCLE PRINCIPALE
    # ========================================================================

    def _run_loop(self):
        """Boucle principale du moteur (tourne dans un thread)"""
        self._set_state(BotState.RUNNING)
        self._log('info', 'Moteur de trading actif')

        # Intervalles selon le timeframe (en secondes)
        tick_interval = 5  # vérification toutes les 5s

        while not self._stop_event.is_set():
            try:
                self.last_tick_time = datetime.now()

                # Vérifications quotidiennes
                self._check_new_day()

                # Mise à jour du compte
                self._update_account_info()

                # Si en pause, ne pas trader mais continuer la surveillance
                if not self._pause_event.is_set():
                    # Pour chaque symbole actif
                    for symbol_config in self.config.symbols:
                        if not symbol_config.enabled:
                            continue
                        if self._stop_event.is_set():
                            break
                        self._process_symbol(symbol_config)

                # Mise à jour de l'état
                self.status_changed.emit(self.get_status())

                # Attente avant prochaine itération
                self._stop_event.wait(tick_interval)

            except Exception as e:
                self._log('error', f'Erreur dans la boucle principale : {e}')
                self.error_occurred.emit(str(e))
                self._stop_event.wait(30)  # pause 30s en cas d'erreur

        self._set_state(BotState.STOPPED)

    def _check_new_day(self):
        """Reset des compteurs journaliers"""
        today = datetime.now().date()
        if self.current_day != today:
            if self.current_day is not None:
                # Fin de journée : rapport
                self._log('info', f"Rapport jour : {self.today_trades} trades, "
                                  f"P&L {self.today_pnl:+.2f}")
            self.current_day = today
            self.today_trades = 0
            self.today_pnl = 0.0
            if MT5_AVAILABLE:
                info = mt5.account_info()
                if info:
                    self.today_start_balance = info.balance

    def _update_account_info(self):
        """Met à jour les infos du compte"""
        if not MT5_AVAILABLE:
            return
        try:
            info = mt5.account_info()
            if info:
                self.account_updated.emit({
                    'balance': info.balance,
                    'equity': info.equity,
                    'profit': info.profit,
                    'margin': info.margin,
                    'margin_free': info.margin_free,
                    'margin_level': info.margin_level,
                    'currency': info.currency,
                })
        except Exception:
            pass

    # ========================================================================
    # TRAITEMENT PAR SYMBOLE
    # ========================================================================

    def _process_symbol(self, symbol_config: SymbolConfig):
        """Analyse et trade sur un symbole"""
        symbol = symbol_config.symbol

        # Vérifier que le symbole est disponible
        if not mt5.symbol_select(symbol, True):
            return

        # Safety checks
        if not self._is_safe_to_trade(symbol):
            return

        # Position déjà ouverte sur ce symbole ?
        if self._has_open_position(symbol):
            return

        # Analyser les signaux
        signal = self._analyze_signal(symbol, symbol_config.timeframe)
        if signal == 0:
            return

        # Exécuter le trade
        self._execute_trade(symbol, signal)

    def _is_safe_to_trade(self, symbol: str) -> bool:
        """Vérifications de sécurité avant de trader"""
        # Pertes consécutives
        if self.consecutive_losses >= self.config.strategy.max_consecutive_losses:
            return False

        # Perte journalière max
        if self.today_start_balance > 0:
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
        if now.weekday() >= 5:  # Weekend
            return False

        # Filtre news
        if self.config.news.enabled:
            if not self._check_news_filter(symbol):
                return False

        # Spread raisonnable
        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if tick and sym_info:
            spread_points = (tick.ask - tick.bid) / sym_info.point
            if spread_points > 30:
                return False

        return True

    def _check_news_filter(self, symbol: str) -> bool:
        """Retourne False s'il y a une news à haut impact proche"""
        if self._economic_calendar is None:
            try:
                from bot.economic_calendar import EconomicCalendar
                self._economic_calendar = EconomicCalendar()
            except ImportError:
                return True

        try:
            safe, event = self._economic_calendar.is_safe_to_trade(symbol)
            if not safe and event:
                self._log('info', f'News filtrée pour {symbol} : {event.title}')
            return safe
        except Exception:
            return True

    def _has_open_position(self, symbol: str) -> bool:
        """Vérifie s'il y a une position ouverte par ce bot sur ce symbole"""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return False
        return any(p.magic == self.config.strategy.magic_number for p in positions)

    # ========================================================================
    # ANALYSE DES SIGNAUX
    # ========================================================================

    def _analyze_signal(self, symbol: str, timeframe_str: str) -> int:
        """Retourne 1 pour achat, -1 pour vente, 0 sinon"""
        timeframe = self._parse_timeframe(timeframe_str)

        # Récupérer les données
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 250)
        if rates is None or len(rates) < 210:
            return 0

        # Calculer les indicateurs (simpliste mais fonctionnel)
        import numpy as np
        closes = np.array([r['close'] for r in rates])
        highs = np.array([r['high'] for r in rates])
        lows = np.array([r['low'] for r in rates])

        fast_ema = self._ema(closes, self.config.strategy.fast_ema)
        slow_ema = self._ema(closes, self.config.strategy.slow_ema)
        rsi = self._rsi(closes, self.config.strategy.rsi_period)

        # Dernière valeur et précédente
        fast_now, fast_prev = fast_ema[-1], fast_ema[-2]
        slow_now, slow_prev = slow_ema[-1], slow_ema[-2]
        current_price = closes[-1]
        rsi_now = rsi[-1]

        # Signal d'achat
        bullish_cross = fast_prev <= slow_prev and fast_now > slow_now
        bullish_trend = current_price > slow_now
        rsi_ok_buy = 40 < rsi_now < self.config.strategy.rsi_overbought

        if bullish_cross and bullish_trend and rsi_ok_buy:
            self.last_signal_time = datetime.now()
            self._log('info', f'{symbol} : Signal ACHAT (RSI={rsi_now:.1f})')
            return 1

        # Signal de vente
        bearish_cross = fast_prev >= slow_prev and fast_now < slow_now
        bearish_trend = current_price < slow_now
        rsi_ok_sell = self.config.strategy.rsi_oversold < rsi_now < 60

        if bearish_cross and bearish_trend and rsi_ok_sell:
            self.last_signal_time = datetime.now()
            self._log('info', f'{symbol} : Signal VENTE (RSI={rsi_now:.1f})')
            return -1

        return 0

    @staticmethod
    def _parse_timeframe(tf: str):
        mapping = {
            'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15, 'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1,
        }
        return mapping.get(tf.upper(), mt5.TIMEFRAME_H4)

    @staticmethod
    def _ema(data, period: int):
        import numpy as np
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema

    @staticmethod
    def _rsi(data, period: int = 14):
        import numpy as np
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros_like(data)
        avg_loss = np.zeros_like(data)
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])

        for i in range(period + 1, len(data)):
            avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i-1]) / period

        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    # ========================================================================
    # EXÉCUTION DES TRADES
    # ========================================================================

    def _execute_trade(self, symbol: str, direction: int):
        """Place un ordre de marché"""
        sym_info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if not sym_info or not tick:
            return

        # Calcul ATR pour les stops
        atr = self._calculate_atr(symbol, self.config.strategy.atr_period)
        if atr <= 0:
            return

        stop_distance = atr * self.config.strategy.atr_multiplier
        if direction == 1:  # BUY
            price = tick.ask
            sl = price - stop_distance
            tp = price + stop_distance * self.config.strategy.risk_reward_ratio
            order_type = mt5.ORDER_TYPE_BUY
        else:  # SELL
            price = tick.bid
            sl = price + stop_distance
            tp = price - stop_distance * self.config.strategy.risk_reward_ratio
            order_type = mt5.ORDER_TYPE_SELL

        # Taille de position
        lot_size = self._calculate_lot_size(symbol, stop_distance)
        if lot_size <= 0:
            return

        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': lot_size,
            'type': order_type,
            'price': price,
            'sl': sl,
            'tp': tp,
            'deviation': 20,
            'magic': self.config.strategy.magic_number,
            'comment': 'SafeTrendBot',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            direction_str = "BUY" if direction == 1 else "SELL"
            self._log('info', f'{direction_str} {symbol} @ {price:.5f} '
                              f'lots={lot_size} SL={sl:.5f} TP={tp:.5f}')
            self.today_trades += 1
            self.position_opened.emit({
                'symbol': symbol,
                'direction': direction_str,
                'price': price,
                'volume': lot_size,
                'sl': sl,
                'tp': tp,
            })
        else:
            self._log('error', f'Ordre refusé {symbol} : {result.comment} (code {result.retcode})')

    def _calculate_atr(self, symbol: str, period: int) -> float:
        """Calcule l'ATR"""
        timeframe = self._parse_timeframe(
            next((s.timeframe for s in self.config.symbols if s.symbol == symbol), 'H4')
        )
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period + 1)
        if rates is None or len(rates) < period + 1:
            return 0

        import numpy as np
        trs = []
        for i in range(1, len(rates)):
            high_low = rates[i]['high'] - rates[i]['low']
            high_close = abs(rates[i]['high'] - rates[i-1]['close'])
            low_close = abs(rates[i]['low'] - rates[i-1]['close'])
            trs.append(max(high_low, high_close, low_close))
        return float(np.mean(trs[-period:]))

    def _calculate_lot_size(self, symbol: str, stop_distance: float) -> float:
        """Calcule la taille de position selon le risque"""
        account = mt5.account_info()
        sym_info = mt5.symbol_info(symbol)
        if not account or not sym_info:
            return 0

        risk_amount = account.balance * self.config.strategy.risk_percent / 100
        tick_value = sym_info.trade_tick_value
        tick_size = sym_info.trade_tick_size
        if tick_value == 0 or tick_size == 0 or stop_distance == 0:
            return 0

        # Valeur par unité de prix
        value_per_unit = tick_value / tick_size
        lot_size = risk_amount / (stop_distance * value_per_unit)

        # Contraintes du broker
        min_lot = sym_info.volume_min
        max_lot = sym_info.volume_max
        step = sym_info.volume_step

        import math
        lot_size = math.floor(lot_size / step) * step
        lot_size = max(min_lot, min(max_lot, lot_size))
        return round(lot_size, 2)
