"""
Package brokers - Adapters pour les différentes plateformes de trading.

Contient :
- broker_adapter.py : Interface abstraite commune
- mt5_adapter.py : MetaTrader 5 (supporté)
- xtb_adapter.py : XTB xStation (expérimental)
- ib_adapter.py : Interactive Brokers (expérimental)
- factory.py : Crée le bon adapter selon la config
"""

from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerSupportLevel,
    OrderType, OrderStatus, AccountInfo, SymbolInfo,
    Tick, Candle, Position, OrderResult, BrokerCapabilities,
    BrokerConnectionError, BrokerNotInstalledError,
    get_broker_capabilities,
)
from app.brokers.factory import create_broker_adapter

__all__ = [
    'BrokerAdapter', 'BrokerType', 'BrokerSupportLevel',
    'OrderType', 'OrderStatus', 'AccountInfo', 'SymbolInfo',
    'Tick', 'Candle', 'Position', 'OrderResult', 'BrokerCapabilities',
    'BrokerConnectionError', 'BrokerNotInstalledError',
    'get_broker_capabilities', 'create_broker_adapter',
]
