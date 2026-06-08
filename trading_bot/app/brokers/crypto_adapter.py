"""
Adapter crypto unifié pour les principaux exchanges via la lib ccxt.
Supporte Binance, Bybit, Kraken, Coinbase et 100+ autres exchanges
avec une API unique.

Statut : 🟡 EXPERIMENTAL - ccxt est mature mais chaque exchange a ses spécificités.

PRÉREQUIS : pip install ccxt
"""

from datetime import datetime
from typing import Optional, List, Dict
import time

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerCapabilities,
    AccountInfo, SymbolInfo, Tick, Candle, Position, OrderType, OrderResult,
    BrokerNotInstalledError, get_broker_capabilities
)


# Mapping timeframes vers format ccxt
CCXT_TIMEFRAMES = {
    'M1': '1m', 'M5': '5m', 'M15': '15m', 'M30': '30m',
    'H1': '1h', 'H4': '4h', 'D1': '1d', 'W1': '1w', 'MN1': '1M',
}


class CryptoAdapter(BrokerAdapter):
    """
    Adapter générique pour exchanges crypto via ccxt.
    Sous-classes : BinanceAdapter, BybitAdapter, KrakenAdapter, CoinbaseAdapter.
    """

    exchange_id: str = ""  # ccxt exchange id, ex: 'binance'

    def __init__(self):
        if not CCXT_AVAILABLE:
            raise BrokerNotInstalledError(
                "ccxt non installé. Installez avec : pip install ccxt"
            )
        self.capabilities = get_broker_capabilities(self.broker_type)
        self.exchange = None
        self._last_error = ""

    def connect(self, api_key: str = "", api_secret: str = "",
                passphrase: str = "", sandbox: bool = False,
                **kwargs) -> bool:
        """
        Connecte à l'exchange crypto.

        Args:
            api_key: Clé API obtenue sur l'exchange
            api_secret: Secret API
            passphrase: Passphrase (seulement Coinbase Pro)
            sandbox: Utiliser le mode testnet si disponible
        """
        if not api_key or not api_secret:
            self._last_error = "api_key et api_secret requis"
            return False

        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            config = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            }
            if passphrase:
                config['password'] = passphrase
            if sandbox:
                config['options'] = {'defaultType': 'spot'}

            self.exchange = exchange_class(config)

            if sandbox:
                try:
                    self.exchange.set_sandbox_mode(True)
                except Exception:
                    pass

            # Test la connexion en chargeant les marchés
            self.exchange.load_markets()
            # Test le compte
            self.exchange.fetch_balance()
            return True
        except Exception as e:
            self._last_error = str(e)
            self.exchange = None
            return False

    def disconnect(self):
        self.exchange = None

    def is_connected(self) -> bool:
        if self.exchange is None:
            return False
        try:
            self.exchange.fetch_time()
            return True
        except Exception:
            return False

    def get_last_error(self) -> str:
        return self._last_error

    # ========================================================================
    # COMPTE
    # ========================================================================

    def get_account_info(self) -> Optional[AccountInfo]:
        if self.exchange is None:
            return None
        try:
            balance = self.exchange.fetch_balance()
            # Pour les exchanges crypto, on cherche la devise principale (USDT, USD, EUR)
            # et on agrège la valeur totale
            total_usdt = 0.0
            for currency in ('USDT', 'USD', 'USDC', 'EUR'):
                if currency in balance['total']:
                    total_usdt = balance['total'][currency]
                    if total_usdt > 0:
                        break

            # Fallback : prendre la première devise avec un solde
            if total_usdt == 0:
                for curr, amount in balance['total'].items():
                    if amount and amount > 0:
                        total_usdt = amount
                        break

            return AccountInfo(
                name=f"{self.capabilities.name} Account",
                server=self.capabilities.name,
                currency="USDT",
                balance=total_usdt,
                equity=total_usdt,
                profit=0,
                margin=0,
                margin_free=total_usdt,
                margin_level=100.0,
                leverage=1,
                broker_type=self.broker_type,
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    # ========================================================================
    # SYMBOLES
    # ========================================================================

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Convertit EURUSD ou BTCUSDT en BTC/USDT pour ccxt"""
        if '/' in symbol:
            return symbol.upper()
        # Essayer de deviner : BTCUSDT -> BTC/USDT
        common_quotes = ['USDT', 'USDC', 'USD', 'EUR', 'BTC', 'ETH', 'BUSD']
        symbol = symbol.upper()
        for quote in common_quotes:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                if base:
                    return f"{base}/{quote}"
        return symbol

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        if self.exchange is None:
            return None
        sym = self._normalize_symbol(symbol)
        try:
            markets = self.exchange.markets
            if sym not in markets:
                self._last_error = f"Symbole introuvable : {sym}"
                return None
            m = markets[sym]
            precision_price = m.get('precision', {}).get('price', 2)
            precision_amount = m.get('precision', {}).get('amount', 6)
            # ccxt précision peut être int (nombre décimales) ou float (tick size)
            if isinstance(precision_price, float):
                digits = max(0, int(-1 * (precision_price).as_integer_ratio()[1].bit_length() * 0.301))
                tick_size = precision_price
            else:
                digits = int(precision_price)
                tick_size = 10 ** -digits

            limits = m.get('limits', {})
            vol_limits = limits.get('amount', {})

            return SymbolInfo(
                symbol=sym,
                description=m.get('id', sym),
                digits=digits,
                point=tick_size,
                tick_size=tick_size,
                tick_value=1.0,
                contract_size=1,
                volume_min=vol_limits.get('min', 0.0001) or 0.0001,
                volume_max=vol_limits.get('max', 1000000) or 1000000,
                volume_step=10 ** -precision_amount if isinstance(precision_amount, int) else precision_amount,
                spread=0,
                currency_base=m.get('base', ''),
                currency_profit=m.get('quote', ''),
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_tick(self, symbol: str) -> Optional[Tick]:
        if self.exchange is None:
            return None
        sym = self._normalize_symbol(symbol)
        try:
            ticker = self.exchange.fetch_ticker(sym)
            return Tick(
                symbol=symbol,
                bid=ticker.get('bid', 0) or ticker.get('last', 0),
                ask=ticker.get('ask', 0) or ticker.get('last', 0),
                time=datetime.fromtimestamp((ticker.get('timestamp') or time.time() * 1000) / 1000),
                volume=int(ticker.get('quoteVolume', 0) or 0),
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_candles(self, symbol: str, timeframe: str,
                    count: int) -> Optional[List[Candle]]:
        if self.exchange is None:
            return None
        sym = self._normalize_symbol(symbol)
        tf = CCXT_TIMEFRAMES.get(timeframe.upper())
        if tf is None:
            self._last_error = f"Timeframe invalide : {timeframe}"
            return None
        try:
            ohlcv = self.exchange.fetch_ohlcv(sym, timeframe=tf, limit=count)
            return [
                Candle(
                    time=datetime.fromtimestamp(c[0] / 1000),
                    open=c[1], high=c[2], low=c[3], close=c[4],
                    volume=int(c[5]),
                )
                for c in ohlcv
            ]
        except Exception as e:
            self._last_error = str(e)
            return None

    def select_symbol(self, symbol: str) -> bool:
        sym = self._normalize_symbol(symbol)
        return self.exchange is not None and sym in self.exchange.markets

    def list_available_symbols(self) -> List[str]:
        if self.exchange is None:
            return []
        return list(self.exchange.markets.keys())[:100]  # Limiter

    # ========================================================================
    # POSITIONS
    # ========================================================================

    def get_positions(self, symbol: Optional[str] = None,
                      magic: Optional[int] = None) -> List[Position]:
        """
        Pour le spot crypto, il n'y a pas de "positions" comme en forex.
        On retourne les soldes non-stable comme positions virtuelles.
        Pour les futures, utiliser l'API futures spécifique.
        """
        if self.exchange is None:
            return []
        try:
            # Tenter d'abord les positions de futures si supporté
            if self.exchange.has.get('fetchPositions'):
                try:
                    positions = self.exchange.fetch_positions()
                    result = []
                    for p in positions:
                        if p.get('contracts', 0) == 0:
                            continue
                        direction = 1 if p.get('side') == 'long' else -1
                        result.append(Position(
                            ticket=hash(f"{p.get('symbol')}{p.get('timestamp', 0)}"),
                            symbol=p.get('symbol', ''),
                            direction=direction,
                            volume=abs(p.get('contracts', 0)),
                            entry_price=p.get('entryPrice', 0) or 0,
                            current_price=p.get('markPrice', 0) or 0,
                            stop_loss=0, take_profit=0,
                            profit=p.get('unrealizedPnl', 0) or 0,
                            swap=0, commission=0,
                            opened_at=datetime.fromtimestamp(
                                (p.get('timestamp') or time.time() * 1000) / 1000
                            ),
                            magic=0, comment='',
                        ))
                    return result
                except Exception:
                    pass

            # Fallback : soldes non-stables comme positions implicites
            balance = self.exchange.fetch_balance()
            result = []
            stable_coins = {'USDT', 'USDC', 'BUSD', 'USD', 'EUR', 'DAI'}
            for curr, amount in balance['total'].items():
                if curr in stable_coins or not amount or amount <= 0:
                    continue
                # Essayer de trouver le prix en USDT
                pair = f"{curr}/USDT"
                try:
                    ticker = self.exchange.fetch_ticker(pair)
                    result.append(Position(
                        ticket=hash(curr),
                        symbol=pair,
                        direction=1,
                        volume=amount,
                        entry_price=0,
                        current_price=ticker.get('last', 0),
                        stop_loss=0, take_profit=0,
                        profit=0, swap=0, commission=0,
                        opened_at=datetime.now(),
                        magic=0, comment='Spot balance',
                    ))
                except Exception:
                    continue
            return result
        except Exception as e:
            self._last_error = str(e)
            return []

    def open_position(self, symbol: str, order_type: OrderType,
                      volume: float, stop_loss: float, take_profit: float,
                      magic: int = 0, comment: str = "") -> OrderResult:
        if self.exchange is None:
            return OrderResult(success=False, error_message="Non connecté")

        sym = self._normalize_symbol(symbol)
        try:
            side = 'buy' if order_type == OrderType.MARKET_BUY else 'sell'
            order = self.exchange.create_market_order(
                symbol=sym,
                side=side,
                amount=volume,
            )
            # Ajout SL/TP si supporté (pas tous les exchanges le font via create_order)
            # Certains nécessitent des appels séparés create_stop_loss_order, etc.
            return OrderResult(
                success=True,
                ticket=int(order.get('id', 0)) if order.get('id', '').isdigit() else hash(order.get('id', '')),
                filled_price=order.get('price', 0) or order.get('average', 0),
            )
        except Exception as e:
            return OrderResult(success=False, error_message=str(e))

    def close_position(self, ticket: int) -> OrderResult:
        # Fermeture = ordre inverse
        # Comme on n'a pas de "ticket" stable en crypto, c'est à gérer côté moteur
        return OrderResult(
            success=False,
            error_message="close_position non supporté en crypto via cet adapter. "
                         "Placez un ordre inverse manuellement."
        )

    def modify_position(self, ticket: int, stop_loss: Optional[float] = None,
                        take_profit: Optional[float] = None) -> OrderResult:
        return OrderResult(
            success=False,
            error_message="modify_position non implémenté pour crypto"
        )


# ============================================================================
# IMPLÉMENTATIONS SPÉCIFIQUES
# ============================================================================

class BinanceAdapter(CryptoAdapter):
    broker_type = BrokerType.BINANCE
    exchange_id = 'binance'


class BybitAdapter(CryptoAdapter):
    broker_type = BrokerType.BYBIT
    exchange_id = 'bybit'


class KrakenAdapter(CryptoAdapter):
    broker_type = BrokerType.KRAKEN
    exchange_id = 'kraken'


class CoinbaseAdapter(CryptoAdapter):
    broker_type = BrokerType.COINBASE
    exchange_id = 'coinbase'
