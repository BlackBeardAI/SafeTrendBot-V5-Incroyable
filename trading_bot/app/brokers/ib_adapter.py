"""
Adapter Interactive Brokers via ib_insync.
Statut : 🟡 EXPERIMENTAL

PRÉREQUIS :
- Installer ib_insync : pip install ib_insync
- Lancer TWS ou IB Gateway
- Activer l'API dans TWS : Config > API > Enable ActiveX and Socket Clients
- Ports par défaut : 7497 (démo TWS), 7496 (live TWS), 4002 (gateway démo), 4001 (gateway live)
- Avoir les permissions de trading sur les instruments visés

NOTES :
- IB utilise un modèle "contract" différent de MT5/XTB
- Pour le forex : Forex('EURUSD') (sans slash)
- Pour les CFDs/actions, il faut spécifier l'exchange
- Pas de concept de "lot" - IB raisonne en quantité d'unités
  (1 lot forex MT5 = 100 000 unités IB)
- IB ne supporte PAS le hedging (comptes US)
"""

import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import numpy as np

try:
    from ib_insync import IB, Forex, Stock, CFD, Contract, MarketOrder, StopOrder
    from ib_insync import util as ib_util
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerCapabilities,
    AccountInfo, SymbolInfo, Tick, Candle, Position, OrderType, OrderResult,
    BrokerNotInstalledError, get_broker_capabilities
)


# Mapping timeframes MT5 -> IB (barSize)
IB_TIMEFRAME_MAP = {
    'M1': '1 min', 'M5': '5 mins', 'M15': '15 mins', 'M30': '30 mins',
    'H1': '1 hour', 'H4': '4 hours', 'D1': '1 day', 'W1': '1 week', 'MN1': '1 month',
}

# Durée de récupération selon le timeframe
IB_DURATION_MAP = {
    'M1': '2 D', 'M5': '5 D', 'M15': '10 D', 'M30': '15 D',
    'H1': '30 D', 'H4': '60 D', 'D1': '1 Y', 'W1': '2 Y', 'MN1': '5 Y',
}


class IBAdapter(BrokerAdapter):
    """Adapter pour Interactive Brokers"""

    broker_type = BrokerType.INTERACTIVE_BROKERS

    def __init__(self):
        if not IB_AVAILABLE:
            raise BrokerNotInstalledError(
                "ib_insync non installé. Installez avec : pip install ib_insync"
            )
        self.capabilities = get_broker_capabilities(BrokerType.INTERACTIVE_BROKERS)
        self.ib: Optional[IB] = None
        self._last_error = ""
        self._contract_cache: Dict[str, Contract] = {}

    # ========================================================================
    # CONNEXION
    # ========================================================================

    def connect(self, host: str = "127.0.0.1", port: int = 7497,
                client_id: int = 1, **kwargs) -> bool:
        """
        Se connecte à TWS ou Gateway.

        Ports par défaut :
        - TWS démo : 7497
        - TWS live : 7496
        - Gateway démo : 4002
        - Gateway live : 4001
        """
        try:
            self.ib = IB()
            self.ib.connect(host=host, port=port, clientId=client_id, timeout=10)
            if not self.ib.isConnected():
                self._last_error = "Impossible de se connecter à TWS/Gateway"
                return False
            return True
        except ConnectionRefusedError:
            self._last_error = (f"Connexion refusée sur {host}:{port}. "
                                "Vérifiez que TWS/Gateway est lancé et l'API activée.")
            return False
        except Exception as e:
            self._last_error = f"Erreur connexion : {e}"
            return False

    def disconnect(self):
        try:
            if self.ib and self.ib.isConnected():
                self.ib.disconnect()
        except Exception:
            pass
        self.ib = None

    def is_connected(self) -> bool:
        return self.ib is not None and self.ib.isConnected()

    def get_last_error(self) -> str:
        return self._last_error

    # ========================================================================
    # CONTRACTS
    # ========================================================================

    def _get_contract(self, symbol: str) -> Optional[Contract]:
        """
        Devine le type de contrat selon le symbole.
        - XXXYYY (6 lettres, devises connues) → Forex
        - 1-5 lettres majuscules → Stock (NYSE/NASDAQ)
        - Autres → on essaie CFD puis Stock
        """
        if symbol in self._contract_cache:
            return self._contract_cache[symbol]

        contract = self._detect_contract(symbol)
        if contract is None:
            return None

        try:
            # Qualifier le contrat (récupérer les infos IB)
            qualified = self.ib.qualifyContracts(contract)
            if qualified:
                self._contract_cache[symbol] = qualified[0]
                return qualified[0]
        except Exception as e:
            self._last_error = f"Contract invalide {symbol} : {e}"
        return None

    @staticmethod
    def _detect_contract(symbol: str) -> Optional[Contract]:
        """Détecte le type de contrat selon le symbole"""
        # Forex : 6 lettres, pairs connues
        forex_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD'}
        if len(symbol) == 6:
            base = symbol[:3].upper()
            quote = symbol[3:].upper()
            if base in forex_currencies and quote in forex_currencies:
                return Forex(symbol.upper())

        # Actions US : 1-5 lettres majuscules
        if symbol.isalpha() and 1 <= len(symbol) <= 5 and symbol.isupper():
            return Stock(symbol, 'SMART', 'USD')

        # Sinon, on essaie action par défaut (l'utilisateur devra
        # potentiellement utiliser un préfixe comme CFD:DE40)
        if symbol.startswith('CFD:'):
            return CFD(symbol[4:], 'SMART', 'USD')

        # Tentative CFD puis Stock
        return CFD(symbol, 'SMART', 'USD')

    # ========================================================================
    # COMPTE
    # ========================================================================

    def get_account_info(self) -> Optional[AccountInfo]:
        if not self.is_connected():
            return None
        try:
            accounts = self.ib.managedAccounts()
            if not accounts:
                return None
            account = accounts[0]
            summary = self.ib.accountSummary(account)

            values = {item.tag: float(item.value) if self._is_number(item.value) else item.value
                      for item in summary if item.currency in ('', 'USD', 'EUR')}

            return AccountInfo(
                name=account,
                server="Interactive Brokers",
                currency=self._find_str(summary, 'AccountType', 'USD') or 'USD',
                balance=float(self._find_value(summary, 'TotalCashValue') or 0),
                equity=float(self._find_value(summary, 'NetLiquidation') or 0),
                profit=float(self._find_value(summary, 'UnrealizedPnL') or 0),
                margin=float(self._find_value(summary, 'InitMarginReq') or 0),
                margin_free=float(self._find_value(summary, 'AvailableFunds') or 0),
                margin_level=0.0,
                leverage=1,  # IB n'expose pas un leverage simple
                broker_type=BrokerType.INTERACTIVE_BROKERS,
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    @staticmethod
    def _find_value(summary, tag: str) -> Optional[str]:
        for item in summary:
            if item.tag == tag:
                return item.value
        return None

    @staticmethod
    def _find_str(summary, tag: str, default: str) -> str:
        v = IBAdapter._find_value(summary, tag)
        return v if v else default

    @staticmethod
    def _is_number(s: str) -> bool:
        try:
            float(s)
            return True
        except (ValueError, TypeError):
            return False

    # ========================================================================
    # SYMBOLES
    # ========================================================================

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        if not self.is_connected():
            return None
        contract = self._get_contract(symbol)
        if contract is None:
            return None

        try:
            details_list = self.ib.reqContractDetails(contract)
            if not details_list:
                return None
            d = details_list[0]

            # Contract size : pour forex = 100000, actions = 1
            contract_size = 100000 if isinstance(contract, Forex) else 1
            digits = 5 if isinstance(contract, Forex) else 2
            point = 10 ** -digits

            return SymbolInfo(
                symbol=symbol,
                description=d.longName or symbol,
                digits=digits, point=point,
                tick_size=float(d.minTick or point),
                tick_value=1.0,  # À calculer précisément
                contract_size=contract_size,
                volume_min=0.01 if isinstance(contract, Forex) else 1,
                volume_max=100 if isinstance(contract, Forex) else 1000000,
                volume_step=0.01 if isinstance(contract, Forex) else 1,
                spread=0,
                currency_base=contract.symbol if isinstance(contract, Forex) else '',
                currency_profit=d.contract.currency or 'USD',
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_tick(self, symbol: str) -> Optional[Tick]:
        if not self.is_connected():
            return None
        contract = self._get_contract(symbol)
        if contract is None:
            return None

        try:
            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(1)  # Attendre la première mise à jour

            bid = ticker.bid if ticker.bid and ticker.bid > 0 else (ticker.last or 0)
            ask = ticker.ask if ticker.ask and ticker.ask > 0 else (ticker.last or 0)

            self.ib.cancelMktData(contract)

            return Tick(
                symbol=symbol, bid=bid, ask=ask, time=datetime.now(),
            )
        except Exception as e:
            self._last_error = str(e)
            return None

    def get_candles(self, symbol: str, timeframe: str,
                    count: int) -> Optional[List[Candle]]:
        if not self.is_connected():
            return None
        contract = self._get_contract(symbol)
        if contract is None:
            return None

        bar_size = IB_TIMEFRAME_MAP.get(timeframe.upper())
        if bar_size is None:
            self._last_error = f"Timeframe invalide : {timeframe}"
            return None

        # Calculer la durée pour récupérer au moins `count` bougies
        duration = IB_DURATION_MAP.get(timeframe.upper(), '30 D')

        try:
            bars = self.ib.reqHistoricalData(
                contract, endDateTime='', durationStr=duration,
                barSizeSetting=bar_size, whatToShow='MIDPOINT',
                useRTH=False, formatDate=1, keepUpToDate=False,
            )
            if not bars:
                return None

            # Ne garder que les `count` dernières bougies
            bars = bars[-count:]

            return [
                Candle(
                    time=b.date if isinstance(b.date, datetime) else datetime.combine(b.date, datetime.min.time()),
                    open=b.open, high=b.high, low=b.low, close=b.close,
                    volume=int(b.volume or 0),
                )
                for b in bars
            ]
        except Exception as e:
            self._last_error = str(e)
            return None

    def select_symbol(self, symbol: str) -> bool:
        return self._get_contract(symbol) is not None

    def list_available_symbols(self) -> List[str]:
        # IB a des millions de symboles - impossible de tous les lister
        # On retourne les principales paires forex
        return [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD',
            'USDCAD', 'NZDUSD', 'EURGBP', 'EURJPY', 'GBPJPY',
        ]

    # ========================================================================
    # POSITIONS
    # ========================================================================

    def get_positions(self, symbol: Optional[str] = None,
                      magic: Optional[int] = None) -> List[Position]:
        if not self.is_connected():
            return []
        try:
            ib_positions = self.ib.positions()
            result = []
            for p in ib_positions:
                if symbol and p.contract.symbol != symbol:
                    continue

                direction = 1 if p.position > 0 else -1
                abs_volume = abs(p.position)

                # Pour forex, convertir en lots
                if isinstance(p.contract, Forex):
                    volume = abs_volume / 100000
                else:
                    volume = abs_volume

                # IB ne fournit pas directement SL/TP/open_time dans positions()
                # Il faudrait croiser avec trades() pour ces infos
                result.append(Position(
                    ticket=int(time.time() * 1000),  # Pas de vrai ticket stable
                    symbol=p.contract.symbol,
                    direction=direction, volume=volume,
                    entry_price=p.avgCost / (100000 if isinstance(p.contract, Forex) else 1),
                    current_price=0, stop_loss=0, take_profit=0,
                    profit=0, swap=0, commission=0,
                    opened_at=datetime.now(),
                    magic=0, comment='IB',
                ))
            return result
        except Exception as e:
            self._last_error = str(e)
            return []

    def open_position(self, symbol: str, order_type: OrderType,
                      volume: float, stop_loss: float, take_profit: float,
                      magic: int = 0, comment: str = "") -> OrderResult:
        if not self.is_connected():
            return OrderResult(success=False, error_message="Non connecté")

        contract = self._get_contract(symbol)
        if contract is None:
            return OrderResult(success=False, error_message="Contract invalide")

        # Convertir volume (lots) en quantité IB
        if isinstance(contract, Forex):
            quantity = int(volume * 100000)
        else:
            quantity = int(volume)

        if quantity <= 0:
            return OrderResult(success=False, error_message="Volume invalide")

        action = 'BUY' if order_type == OrderType.MARKET_BUY else 'SELL'

        try:
            # Bracket order : entrée + SL + TP
            parent_order = MarketOrder(action, quantity)
            parent_order.orderRef = comment or "SafeTrendBot"
            parent_order.transmit = False

            # TP order (limite)
            from ib_insync import LimitOrder
            tp_action = 'SELL' if action == 'BUY' else 'BUY'
            tp_order = LimitOrder(tp_action, quantity, take_profit)
            tp_order.parentId = 0  # Rempli après placement parent
            tp_order.transmit = False

            # SL order (stop)
            sl_order = StopOrder(tp_action, quantity, stop_loss)
            sl_order.parentId = 0
            sl_order.transmit = True

            # Placer parent d'abord
            parent_trade = self.ib.placeOrder(contract, parent_order)
            self.ib.sleep(0.5)

            # Attacher SL/TP
            tp_order.parentId = parent_trade.order.orderId
            sl_order.parentId = parent_trade.order.orderId
            parent_order.transmit = True

            tp_trade = self.ib.placeOrder(contract, tp_order)
            sl_trade = self.ib.placeOrder(contract, sl_order)

            # Attendre la confirmation (max 10s)
            for _ in range(20):
                self.ib.sleep(0.5)
                if parent_trade.orderStatus.status in ('Filled', 'Submitted'):
                    return OrderResult(
                        success=True,
                        ticket=parent_trade.order.orderId,
                        filled_price=parent_trade.orderStatus.avgFillPrice or 0,
                    )
                if parent_trade.orderStatus.status in ('Cancelled', 'Inactive'):
                    return OrderResult(
                        success=False,
                        error_message=f"Ordre {parent_trade.orderStatus.status}"
                    )

            return OrderResult(success=False, error_message="Timeout")
        except Exception as e:
            return OrderResult(success=False, error_message=str(e))

    def close_position(self, ticket: int) -> OrderResult:
        if not self.is_connected():
            return OrderResult(success=False, error_message="Non connecté")

        try:
            # Trouver la position
            positions = self.ib.positions()
            # On ne peut pas vraiment matcher par ticket dans IB
            # Cette implémentation est simplifiée - en prod il faudrait un mapping
            if not positions:
                return OrderResult(success=False, error_message="Aucune position")

            # Fermer la première (limitation de cette API simple)
            pos = positions[0]
            action = 'SELL' if pos.position > 0 else 'BUY'
            quantity = abs(pos.position)

            order = MarketOrder(action, quantity)
            trade = self.ib.placeOrder(pos.contract, order)

            for _ in range(20):
                self.ib.sleep(0.5)
                if trade.orderStatus.status == 'Filled':
                    return OrderResult(success=True, ticket=ticket,
                                     filled_price=trade.orderStatus.avgFillPrice)
            return OrderResult(success=False, error_message="Timeout")
        except Exception as e:
            return OrderResult(success=False, error_message=str(e))

    def modify_position(self, ticket: int, stop_loss: Optional[float] = None,
                        take_profit: Optional[float] = None) -> OrderResult:
        # IB nécessite d'annuler et replacer les ordres SL/TP
        # Implémentation simplifiée pour l'instant
        if not self.is_connected():
            return OrderResult(success=False, error_message="Non connecté")

        try:
            # Trouver les ordres enfants (SL/TP) liés au ticket
            open_orders = self.ib.openOrders()
            modified = False
            for order in open_orders:
                if order.parentId == ticket:
                    if stop_loss is not None and order.orderType == 'STP':
                        order.auxPrice = stop_loss
                        self.ib.placeOrder(order.contract, order)
                        modified = True
                    elif take_profit is not None and order.orderType == 'LMT':
                        order.lmtPrice = take_profit
                        self.ib.placeOrder(order.contract, order)
                        modified = True

            if modified:
                return OrderResult(success=True, ticket=ticket)
            return OrderResult(success=False, error_message="Aucun ordre enfant trouvé")
        except Exception as e:
            return OrderResult(success=False, error_message=str(e))
