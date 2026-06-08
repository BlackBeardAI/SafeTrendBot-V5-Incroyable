"""
Multi-comptes trading — gère plusieurs comptes/brokers en parallèle.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from threading import Thread, Lock
from datetime import datetime


@dataclass
class AccountConfig:
    name: str
    broker_type: str
    connect_kwargs: Dict
    risk_multiplier: float = 1.0  # 1.0 = normal, 0.5 = demi risque
    enabled: bool = True


class MultiAccountManager:
    """
    Gère plusieurs comptes de trading simultanément.
    Clone les trades sur tous les comptes actifs.
    """

    def __init__(self, factory_fn):
        self.factory_fn = factory_fn
        self.accounts: Dict[str, any] = {}  # name -> broker adapter
        self.configs: Dict[str, AccountConfig] = {}
        self._lock = Lock()
        self._trade_history: List[Dict] = []

    def add_account(self, config: AccountConfig) -> bool:
        """Ajoute et connecte un compte"""
        try:
            broker = self.factory_fn(config.broker_type)
            if broker:
                ok = broker.connect(**config.connect_kwargs)
                if ok:
                    with self._lock:
                        self.accounts[config.name] = broker
                        self.configs[config.name] = config
                    print(f"[MULTI] Compte '{config.name}' connecté")
                    return True
        except Exception as e:
            print(f"[MULTI] Échec connexion {config.name}: {e}")
        return False

    def execute_on_all(self, symbol: str, direction: int, volume: float,
                       sl: float, tp: float, magic: int):
        """Exécute le même trade sur tous les comptes actifs"""
        results = {}
        with self._lock:
            for name, broker in self.accounts.items():
                cfg = self.configs[name]
                if not cfg.enabled:
                    continue
                try:
                    adjusted_volume = volume * cfg.risk_multiplier
                    from app.brokers import OrderType
                    order_type = OrderType.MARKET_BUY if direction == 1 else OrderType.MARKET_SELL
                    result = broker.open_position(
                        symbol=symbol, order_type=order_type,
                        volume=adjusted_volume, stop_loss=sl, take_profit=tp,
                        magic=magic, comment=f'SafeTrendBotV5_{name}',
                    )
                    results[name] = {'success': result.success, 'ticket': result.ticket}
                    self._trade_history.append({
                        'time': datetime.now(), 'account': name, 'symbol': symbol,
                        'direction': direction, 'volume': adjusted_volume,
                    })
                except Exception as e:
                    results[name] = {'success': False, 'error': str(e)}
        return results

    def get_balances(self) -> Dict[str, Dict]:
        """Retourne les soldes de tous les comptes"""
        balances = {}
        with self._lock:
            for name, broker in self.accounts.items():
                try:
                    info = broker.get_account_info()
                    if info:
                        balances[name] = {
                            'balance': info.balance, 'equity': info.equity,
                            'profit': info.profit, 'currency': info.currency,
                        }
                except Exception:
                    pass
        return balances

    def get_total_equity(self) -> float:
        return sum(b.get('equity', 0) for b in self.get_balances().values())

    def close_account(self, name: str):
        with self._lock:
            if name in self.accounts:
                try:
                    self.accounts[name].disconnect()
                except Exception:
                    pass
                del self.accounts[name]
                del self.configs[name]

    def get_status(self) -> Dict:
        return {
            'accounts': list(self.accounts.keys()),
            'balances': self.get_balances(),
            'total_equity': self.get_total_equity(),
            'trades_replicated': len(self._trade_history),
        }
