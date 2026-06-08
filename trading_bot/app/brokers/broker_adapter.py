"""
Interface abstraite pour les adapters de broker.
Tous les brokers (MT5, XTB, IB, etc.) implémentent cette interface.

Cette abstraction permet au moteur de trading de fonctionner
indépendamment du broker sous-jacent.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Tuple
import numpy as np


class BrokerType(Enum):
    MT5 = "mt5"
    XTB = "xtb"
    INTERACTIVE_BROKERS = "ib"
    CTRADER = "ctrader"
    BINANCE = "binance"
    BYBIT = "bybit"
    KRAKEN = "kraken"
    COINBASE = "coinbase"


class BrokerSupportLevel(Enum):
    """Niveau de support du broker"""
    SUPPORTED = "supported"         # 🟢 Testé et stable
    EXPERIMENTAL = "experimental"   # 🟡 Fonctionne mais avec risques
    UNSUPPORTED = "unsupported"     # 🔴 Pas d'API disponible


class OrderType(Enum):
    MARKET_BUY = "market_buy"
    MARKET_SELL = "market_sell"
    LIMIT_BUY = "limit_buy"
    LIMIT_SELL = "limit_sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class AccountInfo:
    """Informations du compte (normalisées)"""
    name: str
    server: str
    currency: str
    balance: float
    equity: float
    profit: float           # P&L non réalisé
    margin: float
    margin_free: float
    margin_level: float     # En %
    leverage: int
    broker_type: BrokerType


@dataclass
class SymbolInfo:
    """Infos d'un symbole (normalisées)"""
    symbol: str
    description: str
    digits: int             # Nombre de décimales
    point: float            # Taille d'un point
    tick_size: float
    tick_value: float       # Valeur d'un tick dans la devise du compte
    contract_size: float    # Taille d'un lot
    volume_min: float
    volume_max: float
    volume_step: float
    spread: float           # Spread actuel en points
    currency_base: str
    currency_profit: str


@dataclass
class Tick:
    """Cotation courante"""
    symbol: str
    bid: float
    ask: float
    time: datetime
    volume: int = 0


@dataclass
class Candle:
    """Bougie OHLCV"""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class Position:
    """Position ouverte (normalisée)"""
    ticket: int
    symbol: str
    direction: int          # 1 = long, -1 = short
    volume: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    profit: float
    swap: float
    commission: float
    opened_at: datetime
    magic: int = 0
    comment: str = ""


@dataclass
class OrderResult:
    """Résultat d'un passage d'ordre"""
    success: bool
    ticket: Optional[int] = None
    filled_price: Optional[float] = None
    error_code: Optional[int] = None
    error_message: str = ""


@dataclass
class BrokerCapabilities:
    """Ce que le broker peut faire"""
    name: str
    support_level: BrokerSupportLevel
    supports_forex: bool = True
    supports_cfd: bool = True
    supports_stocks: bool = False
    supports_crypto: bool = False
    supports_trailing_stop: bool = True
    supports_partial_close: bool = True
    supports_hedging: bool = True
    max_symbols_per_account: Optional[int] = None
    warnings: List[str] = field(default_factory=list)


class BrokerConnectionError(Exception):
    """Erreur de connexion au broker"""
    pass


class BrokerNotInstalledError(Exception):
    """Bibliothèque broker non installée"""
    pass


# ============================================================================
# INTERFACE PRINCIPALE
# ============================================================================

class BrokerAdapter(ABC):
    """
    Interface que tous les adapters broker doivent implémenter.
    Le TradingEngine utilise UNIQUEMENT cette interface.
    """

    broker_type: BrokerType = None
    capabilities: BrokerCapabilities = None

    # ------------------------------------------------------------------------
    # CONNEXION
    # ------------------------------------------------------------------------

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """Se connecte au broker. Retourne True si succès."""
        pass

    @abstractmethod
    def disconnect(self):
        """Ferme la connexion"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Vérifie si on est connecté"""
        pass

    @abstractmethod
    def get_last_error(self) -> str:
        """Récupère le dernier message d'erreur"""
        pass

    # ------------------------------------------------------------------------
    # COMPTE
    # ------------------------------------------------------------------------

    @abstractmethod
    def get_account_info(self) -> Optional[AccountInfo]:
        """Récupère les infos du compte"""
        pass

    # ------------------------------------------------------------------------
    # SYMBOLES
    # ------------------------------------------------------------------------

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Récupère les infos d'un symbole"""
        pass

    @abstractmethod
    def get_tick(self, symbol: str) -> Optional[Tick]:
        """Récupère la cotation actuelle"""
        pass

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str,
                    count: int) -> Optional[List[Candle]]:
        """Récupère les N dernières bougies"""
        pass

    @abstractmethod
    def select_symbol(self, symbol: str) -> bool:
        """Active un symbole (si nécessaire)"""
        pass

    @abstractmethod
    def list_available_symbols(self) -> List[str]:
        """Liste les symboles disponibles"""
        pass

    # ------------------------------------------------------------------------
    # POSITIONS
    # ------------------------------------------------------------------------

    @abstractmethod
    def get_positions(self, symbol: Optional[str] = None,
                      magic: Optional[int] = None) -> List[Position]:
        """Liste les positions ouvertes (filtrable)"""
        pass

    @abstractmethod
    def open_position(self, symbol: str, order_type: OrderType,
                      volume: float, stop_loss: float, take_profit: float,
                      magic: int = 0, comment: str = "") -> OrderResult:
        """Ouvre une position"""
        pass

    @abstractmethod
    def close_position(self, ticket: int) -> OrderResult:
        """Ferme une position"""
        pass

    @abstractmethod
    def modify_position(self, ticket: int, stop_loss: Optional[float] = None,
                        take_profit: Optional[float] = None) -> OrderResult:
        """Modifie SL/TP d'une position"""
        pass

    # ------------------------------------------------------------------------
    # HELPERS pour numpy (pour éviter conversions répétées)
    # ------------------------------------------------------------------------

    def get_candles_arrays(self, symbol: str, timeframe: str,
                           count: int) -> Optional[Dict[str, np.ndarray]]:
        """
        Retourne les bougies sous forme de dict de numpy arrays.
        Par défaut utilise get_candles(), surcharger pour optimiser.
        """
        candles = self.get_candles(symbol, timeframe, count)
        if candles is None or len(candles) == 0:
            return None
        return {
            'time': np.array([c.time for c in candles]),
            'open': np.array([c.open for c in candles]),
            'high': np.array([c.high for c in candles]),
            'low': np.array([c.low for c in candles]),
            'close': np.array([c.close for c in candles]),
            'volume': np.array([c.volume for c in candles]),
        }


# ============================================================================
# REGISTRY
# ============================================================================

def get_broker_capabilities(broker_type: BrokerType) -> BrokerCapabilities:
    """Retourne les capacités déclarées d'un broker sans l'instancier"""
    if broker_type == BrokerType.MT5:
        return BrokerCapabilities(
            name="MetaTrader 5",
            support_level=BrokerSupportLevel.SUPPORTED,
            supports_forex=True,
            supports_cfd=True,
            supports_stocks=True,
            supports_crypto=True,
            supports_trailing_stop=True,
            supports_partial_close=True,
            supports_hedging=True,
            warnings=[],
        )
    elif broker_type == BrokerType.XTB:
        return BrokerCapabilities(
            name="XTB xStation",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=True,
            supports_cfd=True,
            supports_stocks=True,
            supports_crypto=False,
            supports_trailing_stop=False,
            supports_partial_close=False,
            supports_hedging=False,
            warnings=[
                "API xAPI non-officielle - risque de changements sans préavis",
                "XTB peut bloquer les comptes utilisant du trading automatisé non autorisé",
                "Vérifiez avec le support XTB que votre compte accepte l'API avant usage",
                "Pas de support hedging - une seule position par symbole",
                "Pas de trailing stop côté serveur - géré côté client uniquement",
            ],
        )
    elif broker_type == BrokerType.INTERACTIVE_BROKERS:
        return BrokerCapabilities(
            name="Interactive Brokers",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=True,
            supports_cfd=True,
            supports_stocks=True,
            supports_crypto=True,
            supports_trailing_stop=True,
            supports_partial_close=True,
            supports_hedging=False,
            warnings=[
                "Nécessite TWS ou IB Gateway lancé localement",
                "Nécessite un compte IB (min. 10 000 USD pour certains marchés)",
                "Permissions API à activer dans TWS: Config > API > Enable ActiveX and Socket Clients",
                "Frais de market data peuvent s'appliquer pour le live",
                "Par défaut compte démo sur port 7497, live sur 7496",
            ],
        )
    elif broker_type == BrokerType.CTRADER:
        return BrokerCapabilities(
            name="cTrader (Spotware)",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=True,
            supports_cfd=True,
            supports_stocks=False,
            supports_crypto=False,
            supports_trailing_stop=True,
            supports_partial_close=True,
            supports_hedging=True,
            warnings=[
                "Nécessite une application approuvée par Spotware (clientId/secret)",
                "Créer une app sur https://openapi.ctrader.com pour obtenir les credentials",
                "Protocole binaire Protobuf sur TCP - lib ctrader-open-api requise",
                "Peu de brokers exposent cTrader (Pepperstone, IC Markets, FxPro)",
            ],
        )
    elif broker_type == BrokerType.BINANCE:
        return BrokerCapabilities(
            name="Binance (Crypto)",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=False,
            supports_cfd=False,
            supports_stocks=False,
            supports_crypto=True,
            supports_trailing_stop=True,
            supports_partial_close=True,
            supports_hedging=False,
            warnings=[
                "Crypto uniquement (BTC, ETH, etc.) - pas de forex",
                "Créer une API key sur https://binance.com/en/my/settings/api-management",
                "RESTREINDRE les permissions de la clé : Trading Spot OUI, Retraits NON",
                "Restreindre l'IP source si possible",
                "Binance bloqué pour les résidents US (utiliser Binance.US)",
            ],
        )
    elif broker_type == BrokerType.BYBIT:
        return BrokerCapabilities(
            name="Bybit (Crypto)",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=False,
            supports_cfd=False,
            supports_stocks=False,
            supports_crypto=True,
            supports_trailing_stop=True,
            supports_partial_close=True,
            supports_hedging=True,
            warnings=[
                "Crypto uniquement (spot et perpetual futures)",
                "Créer une API key sur https://bybit.com/app/user/api-management",
                "RESTREINDRE les permissions : Trade OUI, Retraits NON",
                "Bybit non disponible dans certains pays (US, UK, Canada)",
            ],
        )
    elif broker_type == BrokerType.KRAKEN:
        return BrokerCapabilities(
            name="Kraken (Crypto)",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=False,
            supports_cfd=False,
            supports_stocks=False,
            supports_crypto=True,
            supports_trailing_stop=False,
            supports_partial_close=True,
            supports_hedging=False,
            warnings=[
                "Crypto uniquement",
                "Créer une API key sur https://kraken.com/u/security/api",
                "Permissions : Query Funds + Query Open Orders + Create & Modify Orders OUI",
                "Permission Withdraw Funds : NON",
                "Kraken régulé US (Wyoming) - disponible en Europe",
            ],
        )
    elif broker_type == BrokerType.COINBASE:
        return BrokerCapabilities(
            name="Coinbase Advanced",
            support_level=BrokerSupportLevel.EXPERIMENTAL,
            supports_forex=False,
            supports_cfd=False,
            supports_stocks=False,
            supports_crypto=True,
            supports_trailing_stop=False,
            supports_partial_close=True,
            supports_hedging=False,
            warnings=[
                "Crypto uniquement - API Coinbase Advanced Trade",
                "Créer une API key sur https://www.coinbase.com/settings/api",
                "Permissions : View + Trade. Pas Transfer.",
                "Frais plus élevés que Binance/Bybit",
                "Recommandé pour utilisateurs US (régulé)",
            ],
        )
    return BrokerCapabilities(
        name="Unknown",
        support_level=BrokerSupportLevel.UNSUPPORTED,
    )
