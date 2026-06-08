"""
Pont entre MetaTrader 5 et le dashboard Python.
Permet de récupérer les données du compte, positions, historique, etc.

Prérequis :
    pip install MetaTrader5

Note : MetaTrader5 (le package Python) fonctionne uniquement si MT5
est installé sur la même machine (Windows natif, ou via Wine sur Linux).
Pour Linux pur, utiliser le mode REST (voir alternative à la fin).
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Optional
import json
import os

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("MetaTrader5 non installé. Utilisez 'pip install MetaTrader5' sur Windows.")


@dataclass
class AccountInfo:
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    currency: str
    leverage: int
    name: str
    server: str


@dataclass
class Position:
    ticket: int
    symbol: str
    type: str  # "BUY" ou "SELL"
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    profit: float
    swap: float
    time: str
    magic: int
    comment: str


@dataclass
class HistoryDeal:
    ticket: int
    symbol: str
    type: str
    volume: float
    price: float
    profit: float
    commission: float
    swap: float
    time: str
    magic: int
    comment: str


class MT5Bridge:
    """Interface Python pour interagir avec MetaTrader 5"""

    def __init__(self, magic_number: int = 20260416):
        self.magic_number = magic_number
        self.connected = False

    def connect(self, path: Optional[str] = None, login: Optional[int] = None,
                password: Optional[str] = None, server: Optional[str] = None) -> bool:
        """Se connecter à MT5. Si MT5 est déjà ouvert, laisser les params à None."""
        if not MT5_AVAILABLE:
            raise RuntimeError("Le package MetaTrader5 n'est pas installé")

        if path:
            initialized = mt5.initialize(path=path, login=login, password=password, server=server)
        else:
            initialized = mt5.initialize()

        if not initialized:
            error = mt5.last_error()
            print(f"Échec de la connexion à MT5 : {error}")
            return False

        self.connected = True
        return True

    def disconnect(self):
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
            self.connected = False

    def get_account_info(self) -> Optional[AccountInfo]:
        if not self.connected:
            return None
        info = mt5.account_info()
        if info is None:
            return None
        return AccountInfo(
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            margin_level=info.margin_level,
            profit=info.profit,
            currency=info.currency,
            leverage=info.leverage,
            name=info.name,
            server=info.server,
        )

    def get_open_positions(self, only_bot: bool = True) -> List[Position]:
        if not self.connected:
            return []
        positions = mt5.positions_get()
        if positions is None:
            return []

        result = []
        for p in positions:
            if only_bot and p.magic != self.magic_number:
                continue
            result.append(Position(
                ticket=p.ticket,
                symbol=p.symbol,
                type="BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                volume=p.volume,
                price_open=p.price_open,
                price_current=p.price_current,
                sl=p.sl,
                tp=p.tp,
                profit=p.profit,
                swap=p.swap,
                time=datetime.fromtimestamp(p.time).strftime('%Y-%m-%d %H:%M:%S'),
                magic=p.magic,
                comment=p.comment,
            ))
        return result

    def get_history(self, days: int = 30, only_bot: bool = True) -> List[HistoryDeal]:
        if not self.connected:
            return []
        from_date = datetime.now() - timedelta(days=days)
        deals = mt5.history_deals_get(from_date, datetime.now())
        if deals is None:
            return []

        result = []
        for d in deals:
            if only_bot and d.magic != self.magic_number:
                continue
            # Type conversion
            type_str = "UNKNOWN"
            if d.type == mt5.DEAL_TYPE_BUY:
                type_str = "BUY"
            elif d.type == mt5.DEAL_TYPE_SELL:
                type_str = "SELL"

            result.append(HistoryDeal(
                ticket=d.ticket,
                symbol=d.symbol,
                type=type_str,
                volume=d.volume,
                price=d.price,
                profit=d.profit,
                commission=d.commission,
                swap=d.swap,
                time=datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M:%S'),
                magic=d.magic,
                comment=d.comment,
            ))
        return result

    def compute_stats(self, history: List[HistoryDeal]) -> dict:
        """Calcule les statistiques de performance à partir de l'historique"""
        # On s'intéresse aux deals de sortie (profit/perte réalisé)
        realized = [h for h in history if h.profit != 0]
        if not realized:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_profit': 0,
            }

        wins = [h.profit for h in realized if h.profit > 0]
        losses = [h.profit for h in realized if h.profit < 0]
        
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0

        return {
            'total_trades': len(realized),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': round(len(wins) / len(realized) * 100, 2) if realized else 0,
            'profit_factor': round(total_wins / total_losses, 2) if total_losses > 0 else float('inf'),
            'total_profit': round(sum(h.profit for h in realized), 2),
            'avg_win': round(sum(wins) / len(wins), 2) if wins else 0,
            'avg_loss': round(sum(losses) / len(losses), 2) if losses else 0,
        }

    def to_dict(self) -> dict:
        """Retourne un snapshot complet pour le dashboard"""
        account = self.get_account_info()
        positions = self.get_open_positions()
        history = self.get_history(days=30)
        stats = self.compute_stats(history)

        return {
            'timestamp': datetime.now().isoformat(),
            'connected': self.connected,
            'account': asdict(account) if account else None,
            'positions': [asdict(p) for p in positions],
            'history': [asdict(h) for h in history],
            'stats': stats,
        }


# ============================================================================
# MODE FICHIER (alternative multi-plateforme)
# ============================================================================
# Si MT5 tourne sur un VPS Windows et que le dashboard tourne ailleurs,
# on peut utiliser un fichier de synchronisation partagé (Dropbox, rsync, etc).
# L'EA MT5 écrit un JSON à intervalle régulier, le dashboard le lit.

class FileBridge:
    """Alternative : lecture depuis un fichier JSON écrit par l'EA MT5"""

    def __init__(self, json_path: str):
        self.json_path = json_path

    def read_snapshot(self) -> Optional[dict]:
        if not os.path.exists(self.json_path):
            return None
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erreur lecture snapshot : {e}")
            return None


if __name__ == '__main__':
    # Test simple de connexion
    bridge = MT5Bridge()
    if bridge.connect():
        print("Connecté à MT5")
        print(json.dumps(bridge.to_dict(), indent=2, default=str))
        bridge.disconnect()
    else:
        print("Connexion impossible. Vérifiez que MT5 est lancé.")
