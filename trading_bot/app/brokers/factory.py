"""
Factory pour créer le bon BrokerAdapter selon la configuration.
"""

from typing import Optional
from app.brokers.broker_adapter import (
    BrokerAdapter, BrokerType, BrokerNotInstalledError,
)


def create_broker_adapter(broker_type: BrokerType) -> Optional[BrokerAdapter]:
    """Crée une instance du BrokerAdapter approprié."""
    if broker_type == BrokerType.MT5:
        from app.brokers.mt5_adapter import MT5Adapter
        return MT5Adapter()
    elif broker_type == BrokerType.XTB:
        from app.brokers.xtb_adapter import XTBAdapter
        return XTBAdapter()
    elif broker_type == BrokerType.INTERACTIVE_BROKERS:
        from app.brokers.ib_adapter import IBAdapter
        return IBAdapter()
    elif broker_type == BrokerType.CTRADER:
        from app.brokers.ctrader_adapter import CTraderAdapter
        return CTraderAdapter()
    elif broker_type == BrokerType.BINANCE:
        from app.brokers.crypto_adapter import BinanceAdapter
        return BinanceAdapter()
    elif broker_type == BrokerType.BYBIT:
        from app.brokers.crypto_adapter import BybitAdapter
        return BybitAdapter()
    elif broker_type == BrokerType.KRAKEN:
        from app.brokers.crypto_adapter import KrakenAdapter
        return KrakenAdapter()
    elif broker_type == BrokerType.COINBASE:
        from app.brokers.crypto_adapter import CoinbaseAdapter
        return CoinbaseAdapter()
    return None


def list_available_brokers() -> dict:
    """Vérifie quels brokers sont installés."""
    result = {}

    try:
        import MetaTrader5  # noqa
        result[BrokerType.MT5] = True
    except ImportError:
        result[BrokerType.MT5] = False

    result[BrokerType.XTB] = True  # Pas de dép externe

    try:
        import ib_insync  # noqa
        result[BrokerType.INTERACTIVE_BROKERS] = True
    except ImportError:
        result[BrokerType.INTERACTIVE_BROKERS] = False

    try:
        import ctrader_open_api  # noqa
        result[BrokerType.CTRADER] = True
    except ImportError:
        result[BrokerType.CTRADER] = False

    try:
        import ccxt  # noqa
        result[BrokerType.BINANCE] = True
        result[BrokerType.BYBIT] = True
        result[BrokerType.KRAKEN] = True
        result[BrokerType.COINBASE] = True
    except ImportError:
        result[BrokerType.BINANCE] = False
        result[BrokerType.BYBIT] = False
        result[BrokerType.KRAKEN] = False
        result[BrokerType.COINBASE] = False

    return result
