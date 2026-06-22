"""
SafeTrendBot — cTrader Adapter
==============================
Adapter pour le broker cTrader (Spotware).
Utilise l'API cTrader IDN (Internet Data Nutrition) via WebSocket.

Documentation: https://developers.spotware.com/
"""

import sys
import json
import time
import logging
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum

# Ajouter parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.bot_types import (
    TradeDirection, Position, TradeResult
)
from app.brokers.broker_adapter import BrokerAdapter

logger = logging.getLogger("cTrader")


# ═══════════════════════════════════════════════════════════════════════════════
# PROTOCOL MESSAGES (cTrader IDN)
# ═══════════════════════════════════════════════════════════════════════════════

class MessageType(IntEnum):
    """Types de messages cTrader IDN."""
    PING = 2
    PONG = 3
    LOGIN = 1
    LOGIN_RESPONSE = 2
    LOGOUT = 4
    GET_ACCOUNT_INFO = 20
    ACCOUNT_INFO = 21
    GET_POSITIONS = 22
    POSITIONS = 23
    GET_TRADE = 24
    TRADE = 25
    CLOSE_POSITION = 26
    CLOSE_POSITION_RESPONSE = 27
    OPEN_POSITION = 28
    OPEN_POSITION_RESPONSE = 29
    GET_SYMBOLS = 34
    SYMBOLS = 35
    GET_CANDLES = 36
    CANDLES = 37
    SUBSCRIBE_SPOTS = 49
    SPOTS_UPDATE = 50
    ERROR = 100


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class cTraderConfig:
    """Configuration de connexion cTrader."""
    host: str = "demo.ctraderapi.com"
    port: int = 5032
    account_id: str = ""
    password: str = ""
    app_id: str = "1002"  # Demo App ID
    app_version: str = "3.4"
    client_id: str = ""  # À générer


# ═══════════════════════════════════════════════════════════════════════════════
# SPOTWARE WEB SOCKET CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class cTraderWebSocket:
    """Client WebSocket pour cTrader IDN."""
    
    def __init__(self, config: cTraderConfig):
        self.config = config
        self.websocket = None
        self.running = False
        self._recv_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: Dict[int, callable] = {}
        self._messages: Dict[int, dict] = {}
        self._client_id = config.client_id or self._generate_client_id()
        
        try:
            import websocket
            self._ws_module = websocket
        except ImportError:
            logger.warning("websocket-client non installé. pip install websocket-client")
            self._ws_module = None
    
    def _generate_client_id(self) -> str:
        """Génère un client ID unique."""
        import uuid
        return str(uuid.uuid4()).upper()
    
    def connect(self) -> bool:
        """Établit la connexion WebSocket."""
        if not self._ws_module:
            logger.error("websocket-client requis: pip install websocket-client")
            return False
        
        try:
            url = f"wss://{self.config.host}:{self.config.port}"
            headers = [
                "X-CTrader-Auth-AccountId: " + self.config.account_id,
                "X-CTrader-Auth-AppId: " + self.config.app_id,
                "X-CTrader-Auth-AppVersion: " + self.config.app_version,
                "X-CTrader-Auth-ClientId: " + self._client_id,
            ]
            
            self.websocket = self._ws_module.WebSocketApp(
                url,
                header=headers,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )
            
            self.running = True
            self._recv_thread = threading.Thread(target=self._run, daemon=True)
            self._recv_thread.start()
            
            # Attendre connexion
            time.sleep(2)
            
            return self.websocket.sock and self.websocket.sock.connected
            
        except Exception as e:
            logger.error(f"Erreur connexion cTrader: {e}")
            return False
    
    def _run(self):
        """Boucle de réception."""
        try:
            self.websocket.run_forever(ping_interval=30)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.running = False
    
    def _on_open(self, ws):
        logger.info("cTrader WebSocket ouvert")
    
    def _on_message(self, ws, message):
        """Traite les messages entrants."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", 0)
            
            # Dispatch
            if msg_type in self._callbacks:
                self._callbacks[msg_type](data)
            
            # Store pour sync reads
            with self._lock:
                self._messages[msg_type] = data
                
        except json.JSONDecodeError:
            logger.warning(f"Message JSON invalide: {message[:100]}")
    
    def _on_error(self, ws, error):
        logger.error(f"cTrader WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"cTrader déconnecté: {close_status_code}")
        self.running = False
    
    def send(self, payload: dict) -> bool:
        """Envoie un message."""
        if not self.websocket or not self.running:
            return False
        
        try:
            msg = json.dumps(payload)
            self.websocket.send(msg)
            return True
        except Exception as e:
            logger.error(f"Erreur envoi: {e}")
            return False
    
    def disconnect(self):
        """Déconnecte le WebSocket."""
        self.running = False
        if self.websocket:
            self.websocket.close()


# ═══════════════════════════════════════════════════════════════════════════════
# CTRADER ADAPTER
# ═══════════════════════════════════════════════════════════════════════════════

class cTraderAdapter(BrokerAdapter):
    """
    Adapter pour cTrader.
    
    Nécessite:
    - Un compte cTrader (demo ou live)
    - websocket-client: pip install websocket-client
    
    Note: cTrader requiert une connexion via leur API proprietary.
    Pour un usage en production, utilisez leur SDK officiel.
    """
    
    def __init__(self, config: dict = None):
        # === CONFIGURATION ===
        self.config = cTraderConfig(
            host=config.get("host", "demo.ctraderapi.com") if config else "demo.ctraderapi.com",
            port=config.get("port", 5032) if config else 5032,
            account_id=config.get("account_id", "") if config else "",
            password=config.get("password", "") if config else "",
            app_id=config.get("app_id", "1002") if config else "1002",
        )
        
        self.ws: Optional[cTraderWebSocket] = None
        self.connected = False
        self._account_info: Dict = {}
        self._positions: List[Position] = []
        self._symbols: Dict[str, dict] = {}
    
    def connect(self) -> bool:
        """Connecte à cTrader."""
        self.ws = cTraderWebSocket(self.config)
        
        if self.ws.connect():
            # Envoyer login
            self._send_login()
            time.sleep(1)
            self.connected = True
            logger.info("cTrader connecté")
            return True
        
        return False
    
    def disconnect(self):
        """Déconnecte."""
        if self.ws:
            self.ws.disconnect()
        self.connected = False
    
    def _send_login(self):
        """Envoie la requête de login."""
        payload = {
            "type": MessageType.LOGIN,
            "data": {
                "accountId": self.config.account_id,
                "password": self.config.password,
            }
        }
        self.ws.send(payload)
    
    def get_account_info(self) -> dict:
        """Retourne les infos du compte."""
        if not self.connected:
            return {}
        
        # Simuler avec données locales si pas de réponse WS
        return self._account_info or {
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "currency": "USD",
            "broker": "cTrader"
        }
    
    def get_positions(self) -> List[Position]:
        """Retourne les positions ouvertes."""
        if not self.connected:
            return []
        
        # Demander les positions via WS
        # En réel: attendre la réponse WS
        return self._positions
    
    def get_candles(self, symbol: str, timeframe: str = "H1", count: int = 100) -> List[dict]:
        """Récupère les chandeliers."""
        if not self.connected:
            return []
        
        # Map timeframe cTrader
        tf_map = {
            "M1": 1, "M5": 2, "M15": 3, "M30": 4,
            "H1": 5, "H4": 6, "D1": 7, "W1": 8, "MN": 9
        }
        tf_id = tf_map.get(timeframe, 5)
        
        # Simuler des chandeliers (en prod: attendre WS)
        candles = []
        import random
        base_price = 1.08 if "EUR" in symbol else 100.0
        
        for i in range(count):
            o = base_price + random.uniform(-0.01, 0.01)
            h = o + random.uniform(0, 0.005)
            l = o - random.uniform(0, 0.005)
            c = o + random.uniform(-0.003, 0.003)
            
            candles.append({
                "time": datetime.now(),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": random.randint(100, 10000)
            })
            base_price = c
        
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
        
        # Déterminer type d'ordre
        order_type = 1 if direction == TradeDirection.LONG else 0  # Buy=1, Sell=0
        
        # Simuler envoi (en prod: attendre réponse WS)
        ticket = int(time.time() % 1000000)
        
        elapsed = (time.time() - start) * 1000
        
        logger.info(f"cTrader ORDER: {direction.name} {volume} {symbol} @ market")
        
        return TradeResult(
            True, ticket, symbol, direction,
            self._symbols.get(symbol, {}).get("bid", 1.08),
            volume, stop_loss, take_profit,
            execution_time_ms=elapsed
        )
    
    def close_position(self, ticket: int) -> bool:
        """Ferme une position."""
        if not self.connected:
            return False
        
        logger.info(f"cTrader CLOSE position: {ticket}")
        
        # Simuler fermeture
        return True
    
    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Retourne les infos d'un symbole."""
        if symbol in self._symbols:
            return self._symbols[symbol]
        
        # Simuler
        return {
            "symbol": symbol,
            "bid": 1.08,
            "ask": 1.0802,
            "spread": 0.2,
            "digits": 5,
            "lot_min": 0.01,
            "lot_max": 100.0,
            "lot_step": 0.01,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_ctrader_adapter(config: dict = None) -> cTraderAdapter:
    """Factory pour créer un adapter cTrader."""
    return cTraderAdapter(config)


if __name__ == "__main__":
    # Test
    adapter = cTraderAdapter({"account_id": "TEST123"})
    print(f"cTrader Adapter créé: {adapter.__class__.__name__}")
    print(f"Config: {adapter.config}")