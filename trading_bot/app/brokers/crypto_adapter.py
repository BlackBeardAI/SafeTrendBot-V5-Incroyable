"""
SafeTrendBot — Binance Adapter
===============================
Adapter pour Binance (Spot et Futures).
Utilise l'API REST + WebSocket streams.

Documentation: https://developers.binance.com/
"""

import sys
import time
import hmac
import hashlib
import logging
import threading
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.bot_types import (
    TradeDirection, Position, TradeResult
)
from app.brokers.broker_adapter import BrokerAdapter

logger = logging.getLogger("Binance")


# ═══════════════════════════════════════════════════════════════════════════════
# BINANCE TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class BinanceEnv(Enum):
    """Environnement Binance."""
    SPOT = "https://api.binance.com"
    FUTURES_USDM = "https://fapi.binance.com"
    FUTURES_COIN = "https://dapi.binance.com"


class BinanceMode(Enum):
    """Mode de trading."""
    SPOT = "spot"
    USD_M_FUTURES = "futures_usdm"
    COIN_M_FUTURES = "futures_coin"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BinanceConfig:
    """Configuration Binance."""
    # Clés API
    api_key: str = ""
    api_secret: str = ""
    
    # Environnement
    mode: BinanceMode = BinanceMode.SPOT
    
    # Proxy (optionnel)
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    
    # Testnet
    testnet: bool = True
    
    # Endpoints
    @property
    def base_url(self) -> str:
        if self.testnet:
            if self.mode == BinanceMode.SPOT:
                return "https://testnet.binance.vision/api"
            elif self.mode == BinanceMode.USD_M_FUTURES:
                return "https://testnet.binancefuture.com/fapi"
            else:
                return "https://testnet.binancefuture.com/dapi"
        else:
            return self.mode.value


# ═══════════════════════════════════════════════════════════════════════════════
# BINANCE HTTP CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class BinanceHTTP:
    """Client HTTP pour l'API Binance REST."""
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.session = None
        
        try:
            import requests
            self._requests = requests
        except ImportError:
            logger.warning("requests non installé")
            self._requests = None
    
    def _sign(self, params: dict) -> dict:
        """Signe les paramètres avec la clé secrète."""
        if not self.config.api_secret:
            return params
        
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        signature = hmac.new(
            self.config.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        
        params["signature"] = signature
        return params
    
    def _headers(self) -> dict:
        """Headers par défaut."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-MBX-APIKEY"] = self.config.api_key
        return headers
    
    def get(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """GET request."""
        if not self._requests:
            return None
        
        try:
            url = f"{self.config.base_url}{endpoint}"
            response = self._requests.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Binance GET error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Binance GET exception: {e}")
            return None
    
    def post(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """POST request (signé)."""
        if not self._requests:
            return None
        
        try:
            url = f"{self.config.base_url}{endpoint}"
            params = params or {}
            params = self._sign(params)
            
            response = self._requests.post(
                url,
                params=params,
                headers=self._headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Binance POST error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Binance POST exception: {e}")
            return None
    
    def delete(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """DELETE request (signé)."""
        if not self._requests:
            return None
        
        try:
            url = f"{self.config.base_url}{endpoint}"
            params = params or {}
            params = self._sign(params)
            
            response = self._requests.delete(
                url,
                params=params,
                headers=self._headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Binance DELETE error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Binance DELETE exception: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# BINANCE WEBSOCKET STREAM
# ═══════════════════════════════════════════════════════════════════════════════

class BinanceWebSocket:
    """Client WebSocket pour les streams Binance."""
    
    STREAM_URL = "wss://stream.binance.com:9443/ws"
    TESTNET_STREAM_URL = "wss://testnet.binance.vision/ws"
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.ws = None
        self.running = False
        self._callbacks: Dict[str, callable] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        
        try:
            import websocket
            self._ws_module = websocket
        except ImportError:
            self._ws_module = None
    
    def _get_stream_url(self) -> str:
        """URL du stream selon config."""
        if self.config.testnet:
            return self.TESTNET_STREAM_URL
        return self.STREAM_URL
    
    def subscribe(self, streams: List[str], callback: callable):
        """S'abonne à des streams."""
        if not self._ws_module:
            return
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                
                # Appeler le callback
                for stream, cb in self._callbacks.items():
                    if any(s in data for s in [stream, stream.replace("@kline_", "")]):
                        cb(data)
                        
            except json.JSONDecodeError:
                pass
        
        def on_error(ws, error):
            logger.error(f"Binance WS error: {error}")
        
        def on_close(ws, code, msg):
            self.running = False
        
        def on_open(ws):
            # Subscribe
            sub_msg = {
                "method": "SUBSCRIBE",
                "params": streams,
                "id": 1
            }
            ws.send(json.dumps(sub_msg))
        
        self._callbacks.update({s: callback for s in streams})
        
        url = self._get_stream_url()
        self.ws = self._ws_module.WebSocketApp(
            url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        try:
            self.ws.run_forever(ping_interval=30)
        except Exception:
            pass
        finally:
            self.running = False
    
    def unsubscribe(self, streams: List[str]):
        """Se désabonne."""
        if not self.ws or not self.running:
            return
        
        unsub_msg = {
            "method": "UNSUBSCRIBE",
            "params": streams,
            "id": 2
        }
        self.ws.send(json.dumps(unsub_msg))
    
    def close(self):
        """Ferme la connexion."""
        self.running = False
        if self.ws:
            self.ws.close()


# ═══════════════════════════════════════════════════════════════════════════════
# BINANCE ADAPTER
# ═══════════════════════════════════════════════════════════════════════════════

class BinanceAdapter(BrokerAdapter):
    """
    Adapter pour Binance (Spot et Futures).
    
    Nécessite:
    - Clés API Binance (pour trading)
    - pip install requests websocket-client
    
    Exemple config:
    {
        "api_key": "votre_cle",
        "api_secret": "votre_secret",
        "mode": "spot",  # ou "futures_usdm"
        "testnet": True   # ou False pour production
    }
    """
    
    def __init__(self, config: dict = None):
        # === CONFIGURATION ===
        self.config = BinanceConfig(
            api_key=config.get("api_key", "") if config else "",
            api_secret=config.get("api_secret", "") if config else "",
            mode=BinanceMode(config.get("mode", "spot")) if config else BinanceMode.SPOT,
            testnet=config.get("testnet", True) if config else True,
        )
        
        self.http: Optional[BinanceHTTP] = None
        self.ws: Optional[BinanceWebSocket] = None
        self.connected = False
        
        # Cache
        self._account_info: Dict = {}
        self._positions: Dict[str, Position] = {}
        self._symbols: Dict[str, dict] = {}
    
    def connect(self) -> bool:
        """Connecte à Binance."""
        self.http = BinanceHTTP(self.config)
        
        if self.config.api_key:
            # Test connexion avec les clés
            account = self.http.get("/api/v3/account")
            if account:
                self._account_info = account
                self.connected = True
                
                # Charger les positions
                self._load_positions()
                
                logger.info(f"Binance connecté: {self.config.mode.value}")
                return True
        
        # Mode sans auth (lecture seule)
        self.connected = True
        logger.info(f"Binance connecté (lecture seule)")
        return True
    
    def disconnect(self):
        """Déconnecte."""
        if self.ws:
            self.ws.close()
        self.connected = False
    
    def _load_positions(self):
        """Charge les positions depuis l'API."""
        if self.config.mode == BinanceMode.SPOT:
            return  # Spot n'a pas de "positions" au même sens
        
        # Futures
        positions = self.http.get("/fapi/v2/positionRisk")
        if positions:
            self._positions = {}
            for p in positions:
                if float(p.get("positionAmt", 0)) != 0:
                    symbol = p.get("symbol", "")
                    pos = Position(
                        ticket=int(p.get("updateTime", 0)),
                        symbol=symbol,
                        direction=TradeDirection.LONG if float(p.get("positionAmt", 0)) > 0 else TradeDirection.SHORT,
                        volume=abs(float(p.get("positionAmt", 0))),
                        entry_price=float(p.get("entryPrice", 0)),
                        current_price=float(p.get("markPrice", 0)),
                        stop_loss=float(p.get("stopLoss", 0) or 0),
                        take_profit=float(p.get("takeProfit", 0) or 0),
                        unrealized_pnl=float(p.get("unrealizedProfit", 0)),
                        opened_at=datetime.fromtimestamp(p.get("updateTime", 0) / 1000)
                    )
                    self._positions[symbol] = pos
    
    def get_account_info(self) -> dict:
        """Retourne les infos du compte."""
        if not self.connected:
            return {}
        
        if self.config.mode == BinanceMode.SPOT:
            data = self.http.get("/api/v3/account")
            if data:
                return {
                    "balance": float(data.get("balances", [{}])[0].get("free", 0)),
                    "equity": float(data.get("balances", [{}])[0].get("free", 0)),
                    "currency": "USDT",
                    "broker": "Binance Spot"
                }
        else:
            data = self.http.get("/fapi/v2/account")
            if data:
                return {
                    "balance": float(data.get("availableBalance", 0)),
                    "equity": float(data.get("totalEquity", 0)),
                    "margin": float(data.get("totalMarginBalance", 0)),
                    "margin_level": float(data.get("marginLevel", 0)),
                    "currency": "USDT",
                    "broker": "Binance Futures"
                }
        
        return {}
    
    def get_positions(self) -> List[Position]:
        """Retourne les positions ouvertes."""
        return list(self._positions.values())
    
    def get_candles(self, symbol: str, timeframe: str = "1h", count: int = 100) -> List[dict]:
        """Récupère les chandeliers."""
        if not self.connected:
            return []
        
        # Map timeframe Binance
        tf_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h",
            "8h": "8h", "12h": "12h", "1d": "1d", "3d": "3d",
            "1w": "1w", "1M": "1M"
        }
        interval = tf_map.get(timeframe, "1h")
        
        # Symbol format: BTCUSDT
        endpoint = "/api/v3/klines"
        if self.config.mode == BinanceMode.USD_M_FUTURES:
            endpoint = "/fapi/v1/klines"
        
        params = {"symbol": symbol, "interval": interval, "limit": count}
        data = self.http.get(endpoint, params)
        
        if not data:
            return []
        
        candles = []
        for k in data:
            # Format Binance: [openTime, open, high, low, close, volume, ...]
            candles.append({
                "time": datetime.fromtimestamp(k[0] / 1000),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })
        
        return candles
    
    def send_order(self, symbol: str, direction: TradeDirection, volume: float,
                  stop_loss: float = 0, take_profit: float = 0) -> TradeResult:
        """Envoie un ordre."""
        if not self.connected:
            return TradeResult(
                False, None, symbol, direction, 0, volume, stop_loss, take_profit,
                "Non connecté"
            )
        
        if not self.config.api_key:
            return TradeResult(
                False, None, symbol, direction, 0, volume, stop_loss, take_profit,
                "Clés API non configurées"
            )
        
        start = time.time()
        
        # Type: BUY ou SELL
        side = "BUY" if direction in [TradeDirection.LONG, TradeDirection.CLOSE_SHORT] else "SELL"
        
        # Type d'ordre
        order_type = "MARKET"
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": volume,
        }
        
        # Stop loss / Take profit pour Futures
        if self.config.mode != BinanceMode.SPOT:
            if stop_loss:
                params["stopPrice"] = stop_loss
                params["stopLossPrice"] = stop_loss
            if take_profit:
                params["takeProfitPrice"] = take_profit
        
        endpoint = "/api/v3/order"
        if self.config.mode == BinanceMode.USD_M_FUTURES:
            endpoint = "/fapi/v1/order"
        
        result = self.http.post(endpoint, params)
        elapsed = (time.time() - start) * 1000
        
        if result:
            ticket = result.get("orderId", 0)
            fill_price = float(result.get("fills", [{}])[0].get("price", 0)) or float(result.get("price", 0))
            
            logger.info(f"Binance ORDER: {side} {volume} {symbol}")
            
            return TradeResult(
                True, ticket, symbol, direction,
                fill_price, volume, stop_loss, take_profit,
                execution_time_ms=elapsed
            )
        
        return TradeResult(
            False, None, symbol, direction, 0, volume, stop_loss, take_profit,
            "Ordre échoué",
            elapsed
        )
    
    def close_position(self, ticket: int) -> bool:
        """Ferme une position par ticket."""
        if not self.connected:
            return False
        
        # Trouver la position
        position = None
        for pos in self._positions.values():
            if pos.ticket == ticket:
                position = pos
                break
        
        if not position:
            return False
        
        # Envoyer ordre inverse
        reverse_dir = TradeDirection.SHORT if position.direction == TradeDirection.LONG else TradeDirection.LONG
        
        result = self.send_order(
            position.symbol,
            reverse_dir,
            position.volume
        )
        
        if result.success:
            del self._positions[position.symbol]
            return True
        
        return False
    
    def close_position_by_symbol(self, symbol: str) -> bool:
        """Ferme la position sur un symbole."""
        if symbol not in self._positions:
            return False
        
        position = self._positions[symbol]
        return self.close_position(position.ticket)
    
    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Retourne les infos d'un symbole."""
        if symbol in self._symbols:
            return self._symbols[symbol]
        
        # Prix actuel
        endpoint = "/api/v3/ticker/bookTicker"
        if self.config.mode == BinanceMode.USD_M_FUTURES:
            endpoint = "/fapi/v1/ticker/bookTicker"
        
        data = self.http.get(endpoint, {"symbol": symbol})
        
        if data:
            info = {
                "symbol": symbol,
                "bid": float(data.get("bidPrice", 0)),
                "ask": float(data.get("askPrice", 0)),
                "spread": float(data.get("askPrice", 0)) - float(data.get("bidPrice", 0)),
            }
            self._symbols[symbol] = info
            return info
        
        return None
    
    def get_balance(self, asset: str = "USDT") -> float:
        """Retourne le solde d'un asset."""
        if self.config.mode == BinanceMode.SPOT:
            data = self.http.get("/api/v3/account")
            if data:
                for b in data.get("balances", []):
                    if b.get("asset", "").upper() == asset.upper():
                        return float(b.get("free", 0))
        else:
            info = self.get_account_info()
            return info.get("balance", 0)
        
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def create_binance_adapter(config: dict = None) -> BinanceAdapter:
    """Factory pour créer un adapter Binance."""
    return BinanceAdapter(config)


if __name__ == "__main__":
    # Test
    adapter = BinanceAdapter({"testnet": True})
    print(f"Binance Adapter créé: {adapter.__class__.__name__}")
    print(f"URL: {adapter.config.base_url}")