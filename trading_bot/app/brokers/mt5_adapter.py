"""
Adapter MetaTrader 5.
Statut : 🟢 SUPPORTED - Testé et stable.
"""

from datetime import datetime
from typing import Optional, List, Dict
import numpy as np

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerCapabilities, BrokerSupportLevel,
    AccountInfo, SymbolInfo, Tick, Candle, Position, OrderType, OrderResult,
    BrokerNotInstalledError, get_broker_capabilities
)


class MT5Adapter(BrokerAdapter):
    """Adapter pour MetaTrader 5"""

    broker_type = BrokerType.MT5

    TIMEFRAME_MAP = {}  # Rempli dynamiquement

    def __init__(self):
        if not MT5_AVAILABLE:
            raise BrokerNotInstalledError(
                "MetaTrader5 non installé. Installez avec : pip install MetaTrader5\n"
                "Note: la bibliothèque MetaTrader5 ne fonctionne que sous Windows."
            )
        self.capabilities = get_broker_capabilities(BrokerType.MT5)
        self._connected = False
        self._last_error = ""

        # Timeframe mapping
        MT5Adapter.TIMEFRAME_MAP = {
            'M1': mt5.TIMEFRAME_M1, 'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15, 'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1, 'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1, 'W1': mt5.TIMEFRAME_W1, 'MN1': mt5.TIMEFRAME_MN1,
        }

    # ========================================================================
    # CONNEXION
    # ========================================================================

    def connect(self, auto_detect: bool = True, terminal_path: str = "",
                login: int = 0, password: str = "", server: str = "",
                **kwargs) -> bool:
        try:
            if auto_detect:
                ok = mt5.initialize()
            else:
                init_args = {}
                if terminal_path:
                    init_args['path'] = terminal_path
                if login and password and server:
                    init_args.update(login=login, password=password, server=server)
                ok = mt5.initialize(**init_args)

            if not ok:
                err = mt5.last_error()
                self._last_error = f"Échec init MT5: {err}"
                return False

            info = mt5.account_info()
            if info is None:
                self._last_error = "Connecté au terminal mais pas de compte actif"
                return False

            self._connected = True
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def disconnect(self):
        """
        Déconnecte MT5.
        ⚠️ mt5.shutdown() est GLOBAL — ne l'appeler que si c'est nous qui avons
        lancé la session. Si le moteur de trading est actif, ne pas appeler ici.
        """
        self._connected = False
        # On ne fait PAS mt5.shutdown() ici car il tuerait la connexion
        # du moteur de trading si celui-ci tourne.
        # Le vrai shutdown n'est fait que par TradingEngine.stop()

    def shutdown(self):
        """Shutdown complet — uniquement appelé par TradingEngine.stop()"""
        try:
            mt5.shutdown()
        except Exception:
            pass
        self._connected = False
        if not self._connected:
            return False
        try:
            return mt5.account_info() is not None
        except Exception:
            return False

    def get_last_error(self) -> str:
        return self._last_error

    # ========================================================================
    # COMPTE
    # ========================================================================

    def get_account_info(self) -> Optional[AccountInfo]:
        try:
            info = mt5.account_info()
            if info is None:
                return None
            return AccountInfo(
                name=info.name, server=info.server, currency=info.currency,
                balance=info.balance, equity=info.equity, profit=info.profit,
                margin=info.margin, margin_free=info.margin_free,
                margin_level=info.margin_level, leverage=info.leverage,
                broker_type=BrokerType.MT5,
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    # ========================================================================
    # SYMBOLES
    # ========================================================================

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None
            return SymbolInfo(
                symbol=info.name, description=info.description,
                digits=info.digits, point=info.point,
                tick_size=info.trade_tick_size, tick_value=info.trade_tick_value,
                contract_size=info.trade_contract_size,
                volume_min=info.volume_min, volume_max=info.volume_max,
                volume_step=info.volume_step,
                spread=info.spread, currency_base=info.currency_base,
                currency_profit=info.currency_profit,
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_tick(self, symbol: str) -> Optional[Tick]:
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            return Tick(
                symbol=symbol, bid=tick.bid, ask=tick.ask,
                time=datetime.fromtimestamp(tick.time),
                volume=tick.volume,
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_candles(self, symbol: str, timeframe: str,
                    count: int) -> Optional[List[Candle]]:
        try:
            tf = self.TIMEFRAME_MAP.get(timeframe.upper())
            if tf is None:
                self._last_error = f"Timeframe invalide : {timeframe}"
                return None
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is None:
                return None
            return [
                Candle(
                    time=datetime.fromtimestamp(r['time']),
                    open=r['open'], high=r['high'], low=r['low'],
                    close=r['close'], volume=int(r['tick_volume']),
                )
                for r in rates
            ]
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_candles_arrays(self, symbol: str, timeframe: str,
                           count: int) -> Optional[Dict[str, np.ndarray]]:
        """Version optimisée pour MT5 (évite la conversion Candle)"""
        try:
            tf = self.TIMEFRAME_MAP.get(timeframe.upper())
            if tf is None:
                return None
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is None or len(rates) == 0:
                return None
            return {
                'time': np.array([datetime.fromtimestamp(r['time']) for r in rates]),
                'open': np.array([r['open'] for r in rates]),
                'high': np.array([r['high'] for r in rates]),
                'low': np.array([r['low'] for r in rates]),
                'close': np.array([r['close'] for r in rates]),
                'volume': np.array([r['tick_volume'] for r in rates]),
            }
        except Exception as e:
            self._last_error = str(e)
            return None

    def select_symbol(self, symbol: str) -> bool:
        try:
            return mt5.symbol_select(symbol, True)
        except Exception:
            return False

    def list_available_symbols(self) -> List[str]:
        try:
            symbols = mt5.symbols_get()
            return [s.name for s in symbols] if symbols else []
        except Exception:
            return []

    # ========================================================================
    # POSITIONS
    # ========================================================================

    def get_positions(self, symbol: Optional[str] = None,
                      magic: Optional[int] = None) -> List[Position]:
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            if positions is None:
                return []

            result = []
            for p in positions:
                if magic is not None and p.magic != magic:
                    continue
                direction = 1 if p.type == mt5.POSITION_TYPE_BUY else -1
                result.append(Position(
                    ticket=p.ticket, symbol=p.symbol, direction=direction,
                    volume=p.volume, entry_price=p.price_open,
                    current_price=p.price_current,
                    stop_loss=p.sl, take_profit=p.tp,
                    profit=p.profit, swap=p.swap, commission=p.commission,
                    opened_at=datetime.fromtimestamp(p.time),
                    magic=p.magic, comment=p.comment,
                ))
            return result
        except Exception as e:
            self._last_error = str(e)
            return []

    def open_position(self, symbol: str, order_type: OrderType,
                      volume: float, stop_loss: float, take_profit: float,
                      magic: int = 0, comment: str = "") -> OrderResult:
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return OrderResult(success=False, error_message="Pas de tick")

            if order_type == OrderType.MARKET_BUY:
                mt5_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            elif order_type == OrderType.MARKET_SELL:
                mt5_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                return OrderResult(success=False, error_message="Type d'ordre non supporté")

            request = {
                'action': mt5.TRADE_ACTION_DEAL, 'symbol': symbol, 'volume': volume,
                'type': mt5_type, 'price': price, 'sl': stop_loss, 'tp': take_profit,
                'deviation': 20, 'magic': magic, 'comment': comment or "SafeTrendBot",
                'type_time': mt5.ORDER_TIME_GTC, 'type_filling': mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return OrderResult(
                    success=True, ticket=result.order,
                    filled_price=result.price,
                )
            return OrderResult(
                success=False, error_code=result.retcode,
                error_message=result.comment,
            )
        except Exception as e:
            return OrderResult(success=False, error_message=str(e))

    def close_position(self, ticket: int) -> OrderResult:
        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return OrderResult(success=False, error_message="Position introuvable")
            p = positions[0]
            tick = mt5.symbol_info_tick(p.symbol)
            if tick is None:
                return OrderResult(success=False, error_message="Pas de tick")

            if p.type == mt5.POSITION_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                close_type = mt5.ORDER_TYPE_BUY
                price = tick.ask

            request = {
                'action': mt5.TRADE_ACTION_DEAL, 'symbol': p.symbol,
                'volume': p.volume, 'type': close_type, 'price': price,
                'position': ticket, 'deviation': 20, 'magic': p.magic,
                'type_time': mt5.ORDER_TIME_GTC, 'type_filling': mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return OrderResult(success=True, ticket=ticket, filled_price=result.price)
            return OrderResult(success=False, error_code=result.retcode,
                             error_message=result.comment)
        except Exception as e:
            return OrderResult(success=False, error_message=str(e))

    def modify_position(self, ticket: int, stop_loss: Optional[float] = None,
                        take_profit: Optional[float] = None) -> OrderResult:
        try:
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                return OrderResult(success=False, error_message="Position introuvable")
            p = positions[0]

            request = {
                'action': mt5.TRADE_ACTION_SLTP, 'position': ticket,
                'symbol': p.symbol,
                'sl': stop_loss if stop_loss is not None else p.sl,
                'tp': take_profit if take_profit is not None else p.tp,
                'magic': p.magic,
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return OrderResult(success=True, ticket=ticket)
            return OrderResult(success=False, error_code=result.retcode,
                             error_message=result.comment)
        except Exception as e:
            return OrderResult(success=False, error_message=str(e))
