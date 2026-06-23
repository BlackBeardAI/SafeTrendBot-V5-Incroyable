"""
Auto-failover broker — bascule automatiquement sur un broker de secours.
"""
import time
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("broker_failover")


class BrokerHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class BrokerConfig:
    name: str
    broker_type: str
    priority: int  # 1 = principal, 2+ = backup
    connect_kwargs: Dict
    health_check_interval: int = 10


class BrokerFailover:
    """
    Gère plusieurs brokers avec basculement automatique.
    """

    def __init__(self, configs: List[BrokerConfig], factory_fn: Callable):
        self.configs = sorted(configs, key=lambda c: c.priority)
        self.factory_fn = factory_fn
        self.brokers: Dict[str, any] = {}
        self.health: Dict[str, BrokerHealth] = {}
        self.active_broker: Optional[str] = None
        self._last_health_check: Optional[datetime] = None
        self._consecutive_failures: Dict[str, int] = {}
        self._max_failures = 3

    def initialize(self):
        """Tente de connecter tous les brokers selon leur priorité"""
        for cfg in self.configs:
            try:
                broker = self.factory_fn(cfg.broker_type)
                if broker:
                    ok = broker.connect(**cfg.connect_kwargs)
                    if ok:
                        self.brokers[cfg.name] = broker
                        self.health[cfg.name] = BrokerHealth.HEALTHY
                        self._consecutive_failures[cfg.name] = 0
                        if self.active_broker is None:
                            self.active_broker = cfg.name
                            logger.warning(f"[FAILOVER] Principal actif : {cfg.name}")
                    else:
                        self.health[cfg.name] = BrokerHealth.DOWN
            except Exception as e:
                logger.warning(f"[FAILOVER] Échec connexion {cfg.name}: {e}")
                self.health[cfg.name] = BrokerHealth.DOWN

    def get_active(self):
        """Retourne le broker actif, bascule si nécessaire"""
        self._check_health()
        if self.active_broker and self.health.get(self.active_broker) == BrokerHealth.HEALTHY:
            return self.brokers[self.active_broker]

        # Basculement
        for cfg in self.configs:
            if self.health.get(cfg.name) == BrokerHealth.HEALTHY:
                old = self.active_broker
                self.active_broker = cfg.name
                logger.warning(f"[FAILOVER] Basculement {old} → {cfg.name}")
                return self.brokers[cfg.name]

        return None

    def _check_health(self):
        """Vérifie la santé de tous les brokers"""
        now = datetime.now()
        if self._last_health_check and (now - self._last_health_check).seconds < 10:
            return
        self._last_health_check = now

        for name, broker in self.brokers.items():
            try:
                if broker.is_connected():
                    # Test plus poussé : récupérer un tick
                    tick = broker.get_tick("EURUSD")
                    if tick:
                        self.health[name] = BrokerHealth.HEALTHY
                        self._consecutive_failures[name] = 0
                    else:
                        self._record_failure(name)
                else:
                    self._record_failure(name)
            except Exception:
                self._record_failure(name)

    def _record_failure(self, name: str):
        self._consecutive_failures[name] = self._consecutive_failures.get(name, 0) + 1
        if self._consecutive_failures[name] >= self._max_failures:
            self.health[name] = BrokerHealth.DOWN
            if self.active_broker == name:
                self.active_broker = None
                logger.warning(f"[FAILOVER] {name} déclaré DOWN après {self._max_failures} échecs")
        else:
            self.health[name] = BrokerHealth.DEGRADED

    def reconnect_all(self):
        """Tentative de reconnexion de tous les brokers DOWN"""
        for cfg in self.configs:
            if self.health.get(cfg.name) == BrokerHealth.DOWN:
                try:
                    broker = self.factory_fn(cfg.broker_type)
                    if broker:
                        ok = broker.connect(**cfg.connect_kwargs)
                        if ok:
                            self.brokers[cfg.name] = broker
                            self.health[cfg.name] = BrokerHealth.HEALTHY
                            self._consecutive_failures[cfg.name] = 0
                            logger.warning(f"[FAILOVER] {cfg.name} reconnecté")
                except Exception as e:
                    logger.warning(f"[FAILOVER] Reconnexion {cfg.name} échouée: {e}")

    def get_status(self) -> Dict:
        return {
            'active': self.active_broker,
            'health': {k: v.value for k, v in self.health.items()},
            'failures': dict(self._consecutive_failures),
        }
