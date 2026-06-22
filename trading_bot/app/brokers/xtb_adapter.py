"""
SafeTrendBot — XTB (XTB.com) Adapter
====================================
Adapter pour le broker XTB via xAPI WebSocket.

Documentation: https://developers.xstore.com/
"""

import sys
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import struct

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerCapabilities, BrokerSupportLevel,
    AccountInfo, SymbolInfo, Tick, Candle, Position, OrderType, OrderResult,
    BrokerNotInstalledError, get_broker_capabilities,
)
from app.core.trading_engine import TradeDirection, TradeResult

logger = logging.getLogger("XTB")


# ═══════════════════════════════════════════════════════════════════════════════
# XTB PROTOCOL
# ═══════════════════════════════════════════════════════════════════════════════

class XTBCommand(Enum):
    """Commandes API XTB."""
    LOGIN = "login"
    LOGOUT = "logout"
    GET_ACCOUNT = "getAccount"
    GET_ALL_SYMBOLS = "getAllSymbols"
    GET_SYMBOL = "getSymbol"
    GET_CANDLES = "getCandles"
    TRADE_TRANSACTION = "tradeTransaction"
    TRADE_TRANSACTION_STATUS = "tradeTransactionStatus"
    GET_POSITIONS = "getPositions"
    GET_OPEN_POSITIONS = "getOpenPositions"
    GET_PENDING = "getPendingOrders"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class XTBConfig:
    """Configuration XTB."""
    # Serveurs
    host: str = "xapi.xtb.com"  # Demo: xapi.xtb.com ou xapi-demo.xtb.com
    port: int = 5112
    
    # Authentification
    account_id: str = ""
    password: str = ""
    
    # Mode
    demo: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# XTB STREAM CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class XTBWebSocket:
    """Client WebSocket pour XTB."""
    
    def __init__(self, config: XTBConfig):
        self.config = config
        self.ws = None
        self.stream_ws = None
        self.running = False
        self._lock = threading.Lock()
        self._callbacks: Dict[str, callable] = {}
        self._stream_id: Optional[int] = None
        
        try:
            import websocket
            self._ws_module = websocket
        except ImportError:
            logger.warning("websocket-client requis: pip install websocket-client")
            self._ws_module = None
    
    def connect(self) -> bool:
        """Connecte au broker XTB."""
        if not self._ws_module:
            return False
        
        try:
            # Endpoint selon mode
            if self.config.demo:
                url = f"wss://xapi-demo.xtb.com:5112/demoStream"
                stream_url = f"wss://xapi-demo.xtb.com:5112/demoStream"
            else:
                url = f"wss://xapi.xtb.com:{self.config.port}/live"
                stream_url = f"wss://xapi.xtb.com:{self.config.port}/liveStream"
            
            # Connexion principale
            self.ws = self._ws_module.WebSocketApp(
                url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )
            
            self.running = True
            thread = threading.Thread(target=self._run, daemon=True)
            thread.start()
            
            time.sleep(2)
            
            # Login
            self._send_login()
            time.sleep(1)
            
            return self.ws.sock and self.ws.sock.connected
            
        except Exception as e:
            logger.error(f"Erreur connexion XTB: {e}")
            return False
    
    def _run(self):
        """Boucle de réception."""
        try:
            self.ws.run_forever(ping_interval=30)
        except Exception as e:
            logger.error(f"XTB WebSocket error: {e}")
        finally:
            self.running = False
    
    def _on_open(self, ws):
        logger.info("XTB WebSocket ouvert")
    
    def _on_message(self, ws, message):
        """Traite les messages."""
        try:
            data = json.loads(message)
            
            # Commande répondu
            if "command" in data:
                cmd = data["command"]
                with self._lock:
                    self._callbacks[cmd] = data
            
            # Stream update
            if "streamSessionId" in data:
                self._stream_id = data.get("streamSessionId")
                
        except json.JSONDecodeError:
            pass
    
    def _on_error(self, ws, error):
        logger.error(f"XTB error: {error}")
    
    def _on_close(self, ws, code, msg):
        logger.info(f"XTB fermé: {code}")
        self.running = False
    
    def _send_login(self):
        """Envoie login."""
        payload = {
            "command": XTBCommand.LOGIN,
            "arguments": {
                "accountId": self.config.account_id,
                "password": self.config.password
            }
        }
        self.send(payload)
    
    def send(self, payload: dict, timeout: float = 5.0) -> Optional[dict]:
        """Envoie une commande et attend la réponse."""
        if not self.ws or not self.running:
            return None
        
        try:
            cmd = payload.get("command", "")
            self._ws_module.WebSocket.send(self.ws, json.dumps(payload))
            
            # Attendre réponse
            start = time.time()
            while time.time() - start < timeout:
                with self._lock:
                    if cmd in self._callbacks:
                        return self._callbacks.pop(cmd)
                time.sleep(0.1)
            
            return None
        except Exception as e:
            logger.error(f"Erreur envoi XTB: {e}")
            return None
    
    def disconnect(self):
        """Déconnecte."""
        self.running = False
        if self.ws:
            self.ws.close()


# ═══════════════════════════════════════════════════════════════════════════════
# XTB ADAPTER
# ═══════════════════════════════════════════════════════════════════════════════

class XTBAdapter(BrokerAdapter):
    """
    Adapter pour XTB (xStation).
    
    Nécessite:
    - Compte XTB (demo ou live)
    - pip install websocket-client
    
    Note: XTB propose aussi une API REST limitée.
    Pour le trading complet, utilisez leur WebSocket API.
    """
    
    def __init__(self, config: dict = None):
        # === CONFIGURATION ===
        self.config = XTBConfig(
            host=config.get("host", "xapi-demo.xtb.com") if config else "xapi-demo.xtb.com",
            port=config.get("port", 5112) if config else 5112,
            account_id=config.get("account_id", "") if config else "",
            password=config.get("password", "") if config else "",
            demo=config.get("demo", True) if config else True,
        )
        
        self.ws: Optional[XTBWebSocket] = None
        self.connected = False
        self._account_info: Dict = {}
        self._positions: List[Position] = []
        self._symbols: Dict[str, dict] = {}
    
    def connect(self) -> bool:
        """Connecte à XTB."""
        self.ws = XTBWebSocket(self.config)
        
        if self.ws.connect():
            # Vérifier login
            response = self.ws.send({"command": XTBCommand.GET_ACCOUNT})
            if response and response.get("status"):
                self.connected = True
                self._account_info = response.get("returnData", {})
                logger.info(f"XTB connecté: {self.config.account_id}")
                return True
        
        return False
    
    def disconnect(self):
        """Déconnecte."""
        if self.ws:
            self.ws.disconnect()
        self.connected = False
    
    def get_account_info(self) -> dict:
        """Retourne les infos du compte."""
        if not self.connected:
            return {}
        
        response = self.ws.send({"command": XTBCommand.GET_ACCOUNT})
        if response and response.get("status"):
            data = response.get("returnData", {})
            return {
                "balance": data.get("balance", 0),
                "equity": data.get("equity", 0),
                "margin": data.get("margin", 0),
                "margin_level": data.get("marginLevel", 0),
                "currency": data.get("currency", "USD"),
                "broker": "XTB"
            }
        
        return {}
    
    def get_positions(self) -> List[Position]:
        """Retourne les positions ouvertes."""
        if not self.connected:
            return []
        
        response = self.ws.send({"command": XTBCommand.GET_POSITIONS})
        if not response or not response.get("status"):
            return []
        
        positions = []
        for p in response.get("returnData", []):
            pos = Position(
                ticket=p.get("position", 0),
                symbol=p.get("symbol", ""),
                direction=TradeDirection.LONG if p.get("type", 0) == 0 else TradeDirection.SHORT,
                volume=p.get("volume", 0) / 100.0,  # XTB: volume en 0.01 lots
                entry_price=p.get("open_price", 0),
                current_price=p.get("current_price", 0),
                stop_loss=p.get("sl", 0),
                take_profit=p.get("tp", 0),
                unrealized_pnl=p.get("profit", 0),
                opened_at=datetime.fromtimestamp(p.get("open_time", 0))
            )
            positions.append(pos)
        
        return positions
    
    def get_candles(self, symbol: str, timeframe: str = "H1", count: int = 100) -> List[dict]:
        """Récupère les chandeliers."""
        if not self.connected:
            return []
        
        # Map timeframe XTB
        tf_map = {
            "M1": 1, "M5": 5, "M15": 15, "M30": 30,
            "H1": 60, "H4": 240, "D1": 1440, "W1": 10080
        }
        period = tf_map.get(timeframe, 60)
        
        response = self.ws.send({
            "command": XTBCommand.GET_CANDLES,
            "arguments": {
                "symbol": symbol,
                "period": period,
                "count": count
            }
        })
        
        if not response or not response.get("status"):
            return []
        
        candles = []
        for c in response.get("returnData", []):
            candles.append({
                "time": datetime.fromtimestamp(c.get("ctm", 0) / 1000),
                "open": c.get("open", 0),
                "high": c.get("high", 0),
                "low": c.get("low", 0),
                "close": c.get("close", 0),
                "volume": c.get("vol", 0)
            })
        
        return candles
    
    def send_order(self, symbol: str, direction: TradeDirection, volume: float,
                  stop_loss: float, take_profit: float) -> TradeResult:
        """Envoie un ordre."""
        if not self.connected:
            return TradeResult(
                False, None, symbol, direction, 0, volume, stop_loss, take_profit,
                "Non connecté"
            )
        
        start = time.time()
        
        # Type XTB: 0=BUY, 1=SELL
        order_type = 0 if direction == TradeDirection.LONG else 1
        
        # Volume en 0.01 lots
        vol_x100 = int(volume * 100)
        
        payload = {
            "command": XTBCommand.TRADE_TRANSACTION,
            "arguments": {
                "tradeTransInfo": {
                    "cmd": order_type,
                    "symbol": symbol,
                    "volume": vol_x100,
                    "sl": stop_loss,
                    "tp": take_profit,
                    "type": 0,  # Ordre marché
                    "comment": "SafeTrendBot"
                }
            }
        }
        
        response = self.ws.send(payload, timeout=10)
        elapsed = (time.time() - start) * 1000
        
        if response and response.get("status"):
            data = response.get("returnData", {})
            ticket = data.get("order", 0)
            
            logger.info(f"XTB ORDER: {direction.name} {volume} {symbol}")
            
            return TradeResult(
                True, ticket, symbol, direction,
                data.get("price", 0), volume, stop_loss, take_profit,
                execution_time_ms=elapsed
            )
        
        return TradeResult(
            False, None, symbol, direction, 0, volume, stop_loss, take_profit,
            response.get("errorCode", "Unknown error") if response else "No response",
            elapsed
        )
    
    def close_position(self, ticket: int) -> bool:
        """Ferme une position."""
        if not self.connected:
            return False
        
        payload = {
            "command": XTBCommand.TRADE_TRANSACTION,
            "arguments": {
                "tradeTransInfo": {
                    "type": 2,  # Close
                    "order": ticket
                }
            }
        }
        
        response = self.ws.send(payload, timeout=10)
        
        if response and response.get("status"):
            logger.info(f"XTB CLOSE: {ticket}")
            return True
        
        return False
    
    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Retourne les infos d'un symbole."""
        if symbol in self._symbols:
            return self._symbols[symbol]
        
        response = self.ws.send({
            "command": XTBCommand.GET_SYMBOL,
            "arguments": {"symbol": symbol}
        })
        
        if response and response.get("status"):
            data = response.get("returnData", {})
            info = {
                "symbol": symbol,
                "bid": data.get("bid", 0),
                "ask": data.get("ask", 0),
                "spread": data.get("spread", 0),
                "digits": data.get("digits", 5),
                "lot_min": data.get("min_lot", 0.01),
                "lot_max": data.get("max_lot", 100),
                "lot_step": data.get("lot_step", 0.01),
                "contract_size": data.get("contract_size", 100000),
            }
            self._symbols[symbol] = info
            return info
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_xtb_adapter(config: dict = None) -> XTBAdapter:
    """Factory pour créer un adapter XTB."""
    return XTBAdapter(config)


if __name__ == "__main__":
    # Test
    adapter = XTBAdapter({"account_id": "TEST123", "demo": True})
    print(f"XTB Adapter créé: {adapter.__class__.__name__}")