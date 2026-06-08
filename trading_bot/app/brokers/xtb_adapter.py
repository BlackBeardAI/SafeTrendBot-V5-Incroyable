"""
Adapter XTB xStation via xAPI (JSON sur WebSocket).
Statut : 🟡 EXPERIMENTAL

AVERTISSEMENTS :
- API non-officielle, peut changer sans préavis
- XTB peut bloquer les comptes utilisant du trading automatisé
- Vérifier avec le support XTB que votre compte autorise l'API
- Pas de support hedging (une seule position par symbole)
- Trailing stop géré côté client (pas serveur)

Documentation xAPI : http://developers.xstore.pro/documentation/
"""

import json
import socket
import ssl
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from queue import Queue, Empty
import numpy as np

from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerCapabilities,
    AccountInfo, SymbolInfo, Tick, Candle, Position, OrderType, OrderResult,
    get_broker_capabilities
)


# XTB timeframes (en minutes)
XTB_TIMEFRAMES = {
    'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
    'H1': 60, 'H4': 240, 'D1': 1440, 'W1': 10080, 'MN1': 43200,
}

# XTB command codes pour les opérations
XTB_CMD_BUY = 0
XTB_CMD_SELL = 1
XTB_CMD_BUY_LIMIT = 2
XTB_CMD_SELL_LIMIT = 3
XTB_CMD_BUY_STOP = 4
XTB_CMD_SELL_STOP = 5

XTB_TRANS_OPEN = 0
XTB_TRANS_CLOSE = 2
XTB_TRANS_MODIFY = 3


class XTBClient:
    """Client bas-niveau pour l'API xAPI de XTB"""

    def __init__(self, demo: bool = True):
        self.demo = demo
        if demo:
            self.host = "xapi.xtb.com"
            self.port = 5124
        else:
            self.host = "xapi.xtb.com"
            self.port = 5112
        self.sock: Optional[ssl.SSLSocket] = None
        self.lock = threading.Lock()
        self.connected = False
        self.session_id: Optional[str] = None
        self.last_error = ""
        self._buffer = b""

    def connect(self) -> bool:
        try:
            raw_sock = socket.create_connection((self.host, self.port), timeout=10)
            context = ssl.create_default_context()
            # XTB a parfois des problèmes de cert - on laisse les vérifs par défaut
            self.sock = context.wrap_socket(raw_sock, server_hostname=self.host)
            self.sock.settimeout(30)
            self.connected = True
            return True
        except Exception as e:
            self.last_error = f"Connexion échec : {e}"
            return False

    def disconnect(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.connected = False

    def _send(self, command: Dict) -> Optional[Dict]:
        """Envoie une commande et attend la réponse (thread-safe)"""
        if not self.connected or self.sock is None:
            self.last_error = "Non connecté"
            return None

        message = json.dumps(command).encode('utf-8') + b'\n\n'

        with self.lock:
            try:
                self.sock.sendall(message)
                return self._receive()
            except Exception as e:
                self.last_error = f"Send échec : {e}"
                return None

    def _receive(self) -> Optional[Dict]:
        """Reçoit une réponse complète (délimiteur \\n\\n)"""
        try:
            while b'\n\n' not in self._buffer:
                chunk = self.sock.recv(8192)
                if not chunk:
                    self.last_error = "Connexion fermée"
                    self.connected = False
                    return None
                self._buffer += chunk

            message, self._buffer = self._buffer.split(b'\n\n', 1)
            return json.loads(message.decode('utf-8'))
        except Exception as e:
            self.last_error = f"Receive échec : {e}"
            return None

    def login(self, user_id: str, password: str, app_name: str = "SafeTrendBot") -> bool:
        response = self._send({
            'command': 'login',
            'arguments': {
                'userId': user_id,
                'password': password,
                'appName': app_name,
            }
        })
        if response and response.get('status'):
            self.session_id = response.get('streamSessionId')
            return True
        self.last_error = response.get('errorDescr', 'Login échec') if response else 'Pas de réponse'
        return False

    def logout(self):
        self._send({'command': 'logout'})

    def get_all_symbols(self) -> Optional[List[Dict]]:
        response = self._send({'command': 'getAllSymbols'})
        if response and response.get('status'):
            return response.get('returnData', [])
        return None

    def get_symbol(self, symbol: str) -> Optional[Dict]:
        response = self._send({
            'command': 'getSymbol',
            'arguments': {'symbol': symbol},
        })
        if response and response.get('status'):
            return response.get('returnData')
        return None

    def get_margin_level(self) -> Optional[Dict]:
        response = self._send({'command': 'getMarginLevel'})
        if response and response.get('status'):
            return response.get('returnData')
        return None

    def get_chart_last_request(self, symbol: str, period: int,
                                start_ms: int) -> Optional[Dict]:
        response = self._send({
            'command': 'getChartLastRequest',
            'arguments': {
                'info': {
                    'symbol': symbol, 'period': period, 'start': start_ms,
                }
            }
        })
        if response and response.get('status'):
            return response.get('returnData')
        return None

    def get_trades(self, opened_only: bool = True) -> Optional[List[Dict]]:
        response = self._send({
            'command': 'getTrades',
            'arguments': {'openedOnly': opened_only},
        })
        if response and response.get('status'):
            return response.get('returnData', [])
        return None

    def trade_transaction(self, cmd: int, trans_type: int, symbol: str,
                          volume: float, price: float, sl: float = 0,
                          tp: float = 0, order_id: int = 0,
                          comment: str = "") -> Optional[Dict]:
        response = self._send({
            'command': 'tradeTransaction',
            'arguments': {
                'tradeTransInfo': {
                    'cmd': cmd, 'type': trans_type, 'symbol': symbol,
                    'volume': volume, 'price': price, 'sl': sl, 'tp': tp,
                    'order': order_id, 'customComment': comment,
                    'expiration': 0, 'offset': 0,
                }
            }
        })
        if response and response.get('status'):
            return response.get('returnData')
        self.last_error = response.get('errorDescr', 'Transaction échec') if response else 'Pas de réponse'
        return None

    def trade_transaction_status(self, order: int) -> Optional[Dict]:
        response = self._send({
            'command': 'tradeTransactionStatus',
            'arguments': {'order': order},
        })
        if response and response.get('status'):
            return response.get('returnData')
        return None


class XTBAdapter(BrokerAdapter):
    """Adapter BrokerAdapter pour XTB"""

    broker_type = BrokerType.XTB

    def __init__(self):
        self.capabilities = get_broker_capabilities(BrokerType.XTB)
        self.client: Optional[XTBClient] = None
        self._last_error = ""
        self._symbol_cache: Dict[str, Dict] = {}
        self._cache_time: Dict[str, float] = {}
        self._cache_ttl = 60  # secondes

    # ========================================================================
    # CONNEXION
    # ========================================================================

    def connect(self, user_id: str = "", password: str = "",
                demo: bool = True, **kwargs) -> bool:
        if not user_id or not password:
            self._last_error = "user_id et password requis"
            return False

        self.client = XTBClient(demo=demo)
        if not self.client.connect():
            self._last_error = self.client.last_error
            return False

        if not self.client.login(user_id, password):
            self._last_error = self.client.last_error
            self.client.disconnect()
            self.client = None
            return False

        return True

    def disconnect(self):
        if self.client:
            try:
                self.client.logout()
            except Exception:
                pass
            self.client.disconnect()
            self.client = None

    def is_connected(self) -> bool:
        return self.client is not None and self.client.connected

    def get_last_error(self) -> str:
        if self.client and self.client.last_error:
            return self.client.last_error
        return self._last_error

    # ========================================================================
    # COMPTE
    # ========================================================================

    def get_account_info(self) -> Optional[AccountInfo]:
        if not self.is_connected():
            return None
        data = self.client.get_margin_level()
        if data is None:
            return None
        # XTB ne fournit pas directement le nom de compte via cette méthode
        equity = data.get('equity', 0)
        balance = data.get('balance', 0)
        margin = data.get('margin', 0)
        return AccountInfo(
            name="XTB Account",
            server="XTB Demo" if self.client.demo else "XTB Live",
            currency=data.get('currency', 'EUR'),
            balance=balance, equity=equity,
            profit=equity - balance,
            margin=margin,
            margin_free=data.get('margin_free', 0),
            margin_level=data.get('margin_level', 0),
            leverage=100,  # XTB ne renvoie pas directement
            broker_type=BrokerType.XTB,
        )

    # ========================================================================
    # SYMBOLES
    # ========================================================================

    def _get_symbol_cached(self, symbol: str) -> Optional[Dict]:
        now = time.time()
        if (symbol in self._symbol_cache and
                now - self._cache_time.get(symbol, 0) < self._cache_ttl):
            return self._symbol_cache[symbol]
        data = self.client.get_symbol(symbol) if self.client else None
        if data:
            self._symbol_cache[symbol] = data
            self._cache_time[symbol] = now
        return data

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        if not self.is_connected():
            return None
        data = self._get_symbol_cached(symbol)
        if data is None:
            return None

        digits = data.get('precision', 5)
        point = 10 ** -digits

        return SymbolInfo(
            symbol=data.get('symbol', symbol),
            description=data.get('description', ''),
            digits=digits, point=point,
            tick_size=data.get('tickSize', point),
            tick_value=data.get('tickValue', 1.0),
            contract_size=data.get('contractSize', 100000),
            volume_min=data.get('lotMin', 0.01),
            volume_max=data.get('lotMax', 100),
            volume_step=data.get('lotStep', 0.01),
            spread=data.get('spreadRaw', 0) / point if point > 0 else 0,
            currency_base=data.get('currency', ''),
            currency_profit=data.get('currencyProfit', ''),
        )

    def get_tick(self, symbol: str) -> Optional[Tick]:
        if not self.is_connected():
            return None
        data = self._get_symbol_cached(symbol)
        if data is None:
            return None
        # Note : getSymbol renvoie les derniers prix connus mais pas en temps réel
        # Pour du temps réel, il faudrait utiliser le streaming xAPI
        return Tick(
            symbol=symbol,
            bid=data.get('bid', 0),
            ask=data.get('ask', 0),
            time=datetime.now(),
        )

    def get_candles(self, symbol: str, timeframe: str,
                    count: int) -> Optional[List[Candle]]:
        if not self.is_connected():
            return None
        period = XTB_TIMEFRAMES.get(timeframe.upper())
        if period is None:
            self._last_error = f"Timeframe invalide : {timeframe}"
            return None

        # XTB attend un timestamp en ms pour le début
        # On calcule : count * period minutes dans le passé
        start_ms = int((time.time() - (count * period * 60)) * 1000)
        data = self.client.get_chart_last_request(symbol, period, start_ms)
        if data is None:
            return None

        rate_infos = data.get('rateInfos', [])
        digits = data.get('digits', 5)
        factor = 10 ** digits

        candles = []
        for r in rate_infos[-count:]:
            # XTB : open est absolu, high/low/close sont relatifs à open (en "pips internes")
            open_price = r['open'] / factor
            high = (r['open'] + r['high']) / factor
            low = (r['open'] + r['low']) / factor
            close = (r['open'] + r['close']) / factor
            candles.append(Candle(
                time=datetime.fromtimestamp(r['ctm'] / 1000),
                open=open_price, high=high, low=low, close=close,
                volume=int(r.get('vol', 0)),
            ))
        return candles

    def select_symbol(self, symbol: str) -> bool:
        # XTB n'a pas de notion de "sélection"
        data = self._get_symbol_cached(symbol)
        return data is not None

    def list_available_symbols(self) -> List[str]:
        if not self.is_connected():
            return []
        symbols = self.client.get_all_symbols()
        return [s.get('symbol', '') for s in symbols] if symbols else []

    # ========================================================================
    # POSITIONS
    # ========================================================================

    def get_positions(self, symbol: Optional[str] = None,
                      magic: Optional[int] = None) -> List[Position]:
        if not self.is_connected():
            return []
        trades = self.client.get_trades(opened_only=True)
        if trades is None:
            return []

        result = []
        for t in trades:
            if symbol and t.get('symbol') != symbol:
                continue
            # XTB : cmd 0=buy, 1=sell
            direction = 1 if t.get('cmd') == 0 else -1
            result.append(Position(
                ticket=t.get('order', 0),
                symbol=t.get('symbol', ''),
                direction=direction,
                volume=t.get('volume', 0),
                entry_price=t.get('open_price', 0),
                current_price=t.get('close_price', 0),  # Prix actuel selon XTB
                stop_loss=t.get('sl', 0),
                take_profit=t.get('tp', 0),
                profit=t.get('profit', 0),
                swap=t.get('storage', 0),
                commission=t.get('commission', 0),
                opened_at=datetime.fromtimestamp(t.get('open_time', 0) / 1000),
                magic=0,  # XTB n'a pas de magic number
                comment=t.get('customComment', ''),
            ))
        return result

    def open_position(self, symbol: str, order_type: OrderType,
                      volume: float, stop_loss: float, take_profit: float,
                      magic: int = 0, comment: str = "") -> OrderResult:
        if not self.is_connected():
            return OrderResult(success=False, error_message="Non connecté")

        # Vérifier qu'on n'a pas déjà une position (XTB no hedging)
        existing = self.get_positions(symbol=symbol)
        if existing:
            return OrderResult(
                success=False,
                error_message=f"Position déjà ouverte sur {symbol} (XTB ne supporte pas le hedging)"
            )

        # Récupérer le prix actuel
        sym_data = self._get_symbol_cached(symbol)
        if sym_data is None:
            return OrderResult(success=False, error_message="Symbole introuvable")

        if order_type == OrderType.MARKET_BUY:
            cmd = XTB_CMD_BUY
            price = sym_data.get('ask', 0)
        elif order_type == OrderType.MARKET_SELL:
            cmd = XTB_CMD_SELL
            price = sym_data.get('bid', 0)
        else:
            return OrderResult(success=False, error_message="Type d'ordre non supporté")

        if price <= 0:
            return OrderResult(success=False, error_message="Prix invalide")

        result = self.client.trade_transaction(
            cmd=cmd, trans_type=XTB_TRANS_OPEN, symbol=symbol,
            volume=volume, price=price, sl=stop_loss, tp=take_profit,
            comment=comment or "SafeTrendBot",
        )
        if result is None:
            return OrderResult(success=False,
                             error_message=self.client.last_error)

        order_id = result.get('order', 0)
        # Attendre la confirmation
        for _ in range(10):
            time.sleep(0.5)
            status = self.client.trade_transaction_status(order_id)
            if status and status.get('requestStatus') == 3:  # ACCEPTED
                return OrderResult(success=True, ticket=order_id,
                                 filled_price=price)
            if status and status.get('requestStatus') in (1, 2, 4):  # ERROR, REJECTED
                return OrderResult(success=False, error_code=status.get('requestStatus'),
                                 error_message=status.get('message', ''))
        return OrderResult(success=False, error_message="Timeout confirmation")

    def close_position(self, ticket: int) -> OrderResult:
        if not self.is_connected():
            return OrderResult(success=False, error_message="Non connecté")

        # Récupérer la position
        trades = self.client.get_trades(opened_only=True)
        if not trades:
            return OrderResult(success=False, error_message="Position introuvable")

        position = next((t for t in trades if t.get('order') == ticket), None)
        if position is None:
            return OrderResult(success=False, error_message="Position introuvable")

        sym_data = self._get_symbol_cached(position['symbol'])
        if sym_data is None:
            return OrderResult(success=False, error_message="Symbole introuvable")

        # Fermer = ordre inverse
        if position.get('cmd') == XTB_CMD_BUY:
            close_price = sym_data.get('bid', 0)
        else:
            close_price = sym_data.get('ask', 0)

        result = self.client.trade_transaction(
            cmd=position['cmd'], trans_type=XTB_TRANS_CLOSE,
            symbol=position['symbol'], volume=position['volume'],
            price=close_price, order_id=ticket,
        )
        if result:
            return OrderResult(success=True, ticket=ticket, filled_price=close_price)
        return OrderResult(success=False, error_message=self.client.last_error)

    def modify_position(self, ticket: int, stop_loss: Optional[float] = None,
                        take_profit: Optional[float] = None) -> OrderResult:
        if not self.is_connected():
            return OrderResult(success=False, error_message="Non connecté")

        trades = self.client.get_trades(opened_only=True)
        if not trades:
            return OrderResult(success=False, error_message="Position introuvable")
        position = next((t for t in trades if t.get('order') == ticket), None)
        if position is None:
            return OrderResult(success=False, error_message="Position introuvable")

        sl = stop_loss if stop_loss is not None else position.get('sl', 0)
        tp = take_profit if take_profit is not None else position.get('tp', 0)

        result = self.client.trade_transaction(
            cmd=position['cmd'], trans_type=XTB_TRANS_MODIFY,
            symbol=position['symbol'], volume=position['volume'],
            price=position['open_price'], sl=sl, tp=tp, order_id=ticket,
        )
        if result:
            return OrderResult(success=True, ticket=ticket)
        return OrderResult(success=False, error_message=self.client.last_error)
