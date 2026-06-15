"""
SafeTrendBot Broker Factory — Fabrique d'adapters broker
========================================================
"""

import logging
from typing import Optional, Dict, Type

from app.core.trading_engine import BrokerAdapter, BrokerType

logger = logging.getLogger("BrokerFactory")


# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS DES ADAPTERS
# ═══════════════════════════════════════════════════════════════════════════════

def _import_adapters():
    """Importe dynamiquement les adapters disponibles."""
    adapters = {}
    
    # MT5
    try:
        from app.brokers.mt5_adapter import MT5Adapter
        adapters[BrokerType.MT5] = MT5Adapter
        logger.info("MT5 adapter disponible")
    except ImportError as e:
        logger.warning(f"MT5 adapter non disponible: {e}")
    
    # cTrader
    try:
        from app.brokers.ctrader_adapter import cTraderAdapter
        adapters[BrokerType.CTRADER] = cTraderAdapter
        logger.info("cTrader adapter disponible")
    except ImportError as e:
        logger.warning(f"cTrader adapter non disponible: {e}")
    
    # XTB
    try:
        from app.brokers.xtb_adapter import XTBAdapter
        adapters[BrokerType.XTB] = XTBAdapter
        logger.info("XTB adapter disponible")
    except ImportError as e:
        logger.warning(f"XTB adapter non disponible: {e}")
    
    # Binance
    try:
        from app.brokers.crypto_adapter import BinanceAdapter
        adapters[BrokerType.BINANCE] = BinanceAdapter
        logger.info("Binance adapter disponible")
    except ImportError as e:
        logger.warning(f"Binance adapter non disponible: {e}")
    
    return adapters


# ═══════════════════════════════════════════════════════════════════════════════
# BROKER FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

class BrokerFactory:
    """
    Factory pour créer l'adapter broker approprié.
    
    Usage:
        from app.brokers.factory import BrokerFactory
        
        # Méthode 1: par type
        broker = BrokerFactory.create(BrokerType.MT5, config)
        
        # Méthode 2: auto-détection
        broker = BrokerFactory.auto_detect()
        
        # Méthode 3: par nom
        broker = BrokerFactory.create_by_name("binance", config)
    """
    
    _adapters: Dict[BrokerType, Type[BrokerAdapter]] = {}
    _initialized = False
    
    @classmethod
    def _ensure_init(cls):
        """Initialise les adapters une seule fois."""
        if not cls._initialized:
            cls._adapters = _import_adapters()
            cls._initialized = True
    
    @classmethod
    def create(cls, broker_type: BrokerType, config: dict = None) -> Optional[BrokerAdapter]:
        """
        Crée un adapter pour le broker spécifié.
        
        Args:
            broker_type: Type de broker (BrokerType enum)
            config: Configuration optionnelle (dict)
            
        Returns:
            BrokerAdapter ou None si non disponible
        """
        cls._ensure_init()
        
        adapter_class = cls._adapters.get(broker_type)
        if not adapter_class:
            logger.error(f"Adapter non disponible: {broker_type.value}")
            return None
        
        return adapter_class(config)
    
    @classmethod
    def create_by_name(cls, name: str, config: dict = None) -> Optional[BrokerAdapter]:
        """
        Crée un adapter par nom de broker.
        
        Args:
            name: Nom du broker (mt5, ctrader, xtb, binance, etc.)
            config: Configuration optionnelle
        """
        try:
            broker_type = BrokerType(name.lower())
            return cls.create(broker_type, config)
        except ValueError:
            logger.error(f"Broker inconnu: {name}")
            return None
    
    @classmethod
    def auto_detect(cls, preferred: list = None) -> Optional[BrokerAdapter]:
        """
        Détecte automatiquement le premier broker disponible.
        
        Args:
            preferred: Liste ordonnée de BrokerType à essayer
            
        Returns:
            Premier broker disponible ou None
        """
        cls._ensure_init()
        
        order = preferred or [
            BrokerType.MT5,
            BrokerType.CTRADER,
            BrokerType.XTB,
            BrokerType.BINANCE,
        ]
        
        for broker_type in order:
            if broker_type in cls._adapters:
                try:
                    adapter = cls._adapters[broker_type]()
                    logger.info(f"Broker détecté: {broker_type.value}")
                    return adapter
                except Exception as e:
                    logger.warning(f"Erreur {broker_type.value}: {e}")
        
        logger.error("Aucun broker disponible")
        return None
    
    @classmethod
    def list_available(cls) -> list:
        """Liste les brokers disponibles."""
        cls._ensure_init()
        return list(cls._adapters.keys())
    
    @classmethod
    def get_adapter_class(cls, broker_type: BrokerType) -> Optional[Type[BrokerAdapter]]:
        """Retourne la classe de l'adapter (pour inspection)."""
        cls._ensure_init()
        return cls._adapters.get(broker_type)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_broker(broker_name: str = "auto", config: dict = None) -> Optional[BrokerAdapter]:
    """Fonction utilitaire pour créer un broker."""
    if broker_name == "auto":
        return BrokerFactory.auto_detect()
    return BrokerFactory.create_by_name(broker_name, config)


def list_brokers() -> list:
    """Liste les brokers disponibles."""
    return BrokerFactory.list_available()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 50)
    print("SafeTrendBot Broker Factory")
    print("═" * 50)
    
    available = list_brokers()
    
    print(f"\nBrokers disponibles ({len(available)}):")
    for broker in available:
        print(f"  ✅ {broker.value}")
    
    print("\nBrokers non disponibles:")
    all_brokers = list(BrokerType)
    for broker in all_brokers:
        if broker not in available:
            print(f"  ❌ {broker.value}")