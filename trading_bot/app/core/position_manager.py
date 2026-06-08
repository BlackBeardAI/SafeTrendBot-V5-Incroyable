"""
Gestionnaire de positions avancé.
Gère le trailing stop, le break-even, et la protection dynamique des positions.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
from enum import Enum

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


class PositionPhase(Enum):
    """Phase de gestion d'une position"""
    OPENED = "opened"                   # Tout nouveau
    AT_BREAKEVEN = "at_breakeven"       # SL déplacé au prix d'entrée
    TRAILING = "trailing"               # Trailing stop actif


@dataclass
class ManagedPosition:
    """État de gestion d'une position"""
    ticket: int
    symbol: str
    direction: int                      # 1 = long, -1 = short
    entry_price: float
    initial_sl: float
    initial_tp: float
    initial_risk: float                 # Distance SL - entrée (en prix)
    current_sl: float
    phase: PositionPhase = PositionPhase.OPENED
    peak_profit_points: float = 0.0     # Meilleur profit atteint (pour trailing)
    opened_at: datetime = field(default_factory=datetime.now)


class PositionManager:
    """
    Gère dynamiquement les positions ouvertes :
    - Break-even automatique
    - Trailing stop
    - Protection des profits
    """

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.positions: Dict[int, ManagedPosition] = {}

    def log(self, message: str):
        if self.logger:
            self.logger(message)

    def register_position(self, ticket: int, symbol: str, direction: int,
                          entry: float, sl: float, tp: float):
        """Enregistre une nouvelle position à gérer"""
        initial_risk = abs(entry - sl)
        self.positions[ticket] = ManagedPosition(
            ticket=ticket,
            symbol=symbol,
            direction=direction,
            entry_price=entry,
            initial_sl=sl,
            initial_tp=tp,
            initial_risk=initial_risk,
            current_sl=sl,
        )
        self.log(f"Position {ticket} enregistrée pour gestion dynamique "
                 f"(risque initial: {initial_risk:.5f})")

    def unregister_position(self, ticket: int):
        """Supprime une position (fermée)"""
        if ticket in self.positions:
            del self.positions[ticket]

    def manage_all_positions(self):
        """Appelé périodiquement pour gérer toutes les positions"""
        if not MT5_AVAILABLE:
            return

        # Synchroniser avec MT5 : supprimer les positions fermées
        try:
            open_tickets = set()
            positions = mt5.positions_get()
            if positions:
                open_tickets = {p.ticket for p in positions
                                if p.magic == self.config.strategy.magic_number}

            # Retirer de notre dict les positions qui ne sont plus ouvertes
            closed = [t for t in self.positions if t not in open_tickets]
            for t in closed:
                self.unregister_position(t)

            # Découvrir les nouvelles positions ouvertes
            for p in positions or []:
                if p.magic != self.config.strategy.magic_number:
                    continue
                if p.ticket not in self.positions:
                    direction = 1 if p.type == mt5.POSITION_TYPE_BUY else -1
                    self.register_position(
                        ticket=p.ticket,
                        symbol=p.symbol,
                        direction=direction,
                        entry=p.price_open,
                        sl=p.sl,
                        tp=p.tp,
                    )
        except Exception as e:
            self.log(f"Erreur sync positions: {e}")
            return

        # Gérer chaque position
        for ticket, managed in list(self.positions.items()):
            self._manage_position(managed)

    def _manage_position(self, managed: ManagedPosition):
        """Applique les règles de gestion à une position"""
        if not MT5_AVAILABLE:
            return

        try:
            # Récupérer l'état actuel de la position
            positions = mt5.positions_get(ticket=managed.ticket)
            if not positions:
                self.unregister_position(managed.ticket)
                return

            pos = positions[0]
            tick = mt5.symbol_info_tick(pos.symbol)
            if not tick:
                return

            # Prix actuel selon la direction
            current_price = tick.bid if managed.direction == 1 else tick.ask

            # Profit en unités de prix
            if managed.direction == 1:
                profit_distance = current_price - managed.entry_price
            else:
                profit_distance = managed.entry_price - current_price

            # Mettre à jour le pic
            if profit_distance > managed.peak_profit_points:
                managed.peak_profit_points = profit_distance

            # Règle 1 : Break-even à +1R
            if managed.phase == PositionPhase.OPENED:
                if profit_distance >= managed.initial_risk:
                    new_sl = managed.entry_price
                    # Ajouter une petite marge pour couvrir le spread/commission
                    sym_info = mt5.symbol_info(pos.symbol)
                    if sym_info:
                        spread_margin = sym_info.spread * sym_info.point * 2
                        if managed.direction == 1:
                            new_sl += spread_margin
                        else:
                            new_sl -= spread_margin

                    if self._modify_stop_loss(pos, new_sl):
                        managed.current_sl = new_sl
                        managed.phase = PositionPhase.AT_BREAKEVEN
                        self.log(f"✓ Position {managed.ticket} : break-even activé @ {new_sl:.5f}")

            # Règle 2 : Trailing stop à +2R
            if managed.phase in (PositionPhase.OPENED, PositionPhase.AT_BREAKEVEN):
                if profit_distance >= managed.initial_risk * 2:
                    managed.phase = PositionPhase.TRAILING

            if managed.phase == PositionPhase.TRAILING:
                # Le trailing suit à distance de 1R du pic atteint
                trail_distance = managed.initial_risk
                if managed.direction == 1:
                    new_sl = current_price - trail_distance
                    if new_sl > managed.current_sl:
                        if self._modify_stop_loss(pos, new_sl):
                            old_sl = managed.current_sl
                            managed.current_sl = new_sl
                            self.log(f"↗ Position {managed.ticket} : trailing {old_sl:.5f} → {new_sl:.5f}")
                else:
                    new_sl = current_price + trail_distance
                    if new_sl < managed.current_sl:
                        if self._modify_stop_loss(pos, new_sl):
                            old_sl = managed.current_sl
                            managed.current_sl = new_sl
                            self.log(f"↘ Position {managed.ticket} : trailing {old_sl:.5f} → {new_sl:.5f}")
        except Exception as e:
            self.log(f"Erreur gestion position {managed.ticket}: {e}")

    def _modify_stop_loss(self, position, new_sl: float) -> bool:
        """Modifie le SL d'une position"""
        if not MT5_AVAILABLE:
            return False

        try:
            request = {
                'action': mt5.TRADE_ACTION_SLTP,
                'position': position.ticket,
                'symbol': position.symbol,
                'sl': new_sl,
                'tp': position.tp,
                'magic': self.config.strategy.magic_number,
            }
            result = mt5.order_send(request)
            return result.retcode == mt5.TRADE_RETCODE_DONE
        except Exception as e:
            self.log(f"Erreur modification SL: {e}")
            return False

    def get_stats(self) -> dict:
        """Retourne les statistiques de gestion"""
        total = len(self.positions)
        at_be = sum(1 for p in self.positions.values() if p.phase == PositionPhase.AT_BREAKEVEN)
        trailing = sum(1 for p in self.positions.values() if p.phase == PositionPhase.TRAILING)
        return {
            'total_managed': total,
            'at_breakeven': at_be,
            'trailing': trailing,
            'new': total - at_be - trailing,
        }
