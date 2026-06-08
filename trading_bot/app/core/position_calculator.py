"""
Calculator de taille de position.
Outil utilitaire pour calculer combien de lots trader selon :
- Le capital du compte
- Le pourcentage de risque accepté
- La distance du stop loss en pips
- Le symbole tradé
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionCalculation:
    """Résultat du calcul de position"""
    capital: float                  # Capital du compte
    risk_percent: float             # % du capital risqué
    risk_amount: float              # Montant en devise
    stop_loss_pips: float           # SL en pips
    pip_value: float                # Valeur d'un pip pour 1 lot
    lot_size: float                 # Taille de position calculée (en lots)
    units: int                      # Unités équivalentes
    actual_risk: float              # Risque réel après arrondi
    warnings: list = None


def calculate_pip_value(symbol: str, lot_size: float = 1.0,
                        account_currency: str = "EUR") -> float:
    """
    Calcule la valeur d'un pip pour un symbole donné.

    Approximations courantes :
    - EURUSD, GBPUSD, AUDUSD : 10 USD par pip pour 1 lot
    - USDJPY : ~9.5 USD par pip
    - XAUUSD : 10 USD pour 0.1 mouvement (pip = 0.1)

    Pour un calcul précis, il faudrait le prix actuel et la conversion devise.
    Ici on donne une estimation pour les paires majeures.
    """
    symbol = symbol.upper().replace("/", "")

    # Tables de référence pour 1 lot standard (100 000 unités)
    pip_values_per_lot = {
        # Paires en USD comme devise de cote (10 USD/pip pour 1 lot)
        "EURUSD": 10.0, "GBPUSD": 10.0, "AUDUSD": 10.0, "NZDUSD": 10.0,
        # JPY comme devise de cote (10 USD/pip pour 1 lot, mais pip = 0.01)
        "USDJPY": 9.5, "EURJPY": 9.5, "GBPJPY": 9.5, "AUDJPY": 9.5,
        # USD comme devise de base : variable selon prix
        "USDCHF": 11.0, "USDCAD": 7.5,
        # Or
        "XAUUSD": 10.0,  # 10 USD pour 1 mouvement de 0.10
        # Crypto
        "BTCUSD": 1.0, "ETHUSD": 1.0,
    }
    return pip_values_per_lot.get(symbol, 10.0) * lot_size


def calculate_position_size(
    capital: float,
    risk_percent: float,
    stop_loss_pips: float,
    symbol: str = "EURUSD",
    account_currency: str = "EUR",
) -> PositionCalculation:
    """
    Calcule la taille de position optimale.

    Formule :
        risk_amount = capital × (risk_percent / 100)
        lot_size = risk_amount / (stop_loss_pips × pip_value_per_lot)
    """
    warnings = []

    if capital <= 0:
        warnings.append("Capital invalide")
        return PositionCalculation(
            capital=capital, risk_percent=risk_percent,
            risk_amount=0, stop_loss_pips=stop_loss_pips,
            pip_value=0, lot_size=0, units=0, actual_risk=0,
            warnings=warnings,
        )

    if risk_percent <= 0 or risk_percent > 10:
        warnings.append(
            f"Risque par trade {risk_percent}% : {'trop bas' if risk_percent <= 0 else 'TRÈS élevé'}. "
            f"Recommandé : 0.5-2%."
        )

    if stop_loss_pips <= 0:
        warnings.append("Stop loss invalide")
        return PositionCalculation(
            capital=capital, risk_percent=risk_percent,
            risk_amount=0, stop_loss_pips=stop_loss_pips,
            pip_value=0, lot_size=0, units=0, actual_risk=0,
            warnings=warnings,
        )

    risk_amount = capital * (risk_percent / 100)
    pip_value_per_lot = calculate_pip_value(symbol, 1.0, account_currency)

    if pip_value_per_lot <= 0:
        warnings.append(f"Symbole {symbol} non reconnu - estimation imprécise")
        pip_value_per_lot = 10.0  # Fallback

    lot_size = risk_amount / (stop_loss_pips * pip_value_per_lot)

    # Arrondir au 0.01 lot (1 mini-lot)
    lot_size_rounded = round(lot_size, 2)

    # Limites raisonnables
    if lot_size_rounded < 0.01:
        warnings.append(
            f"Position trop petite ({lot_size_rounded} lot). "
            f"Réduisez le SL ou augmentez le capital."
        )
        lot_size_rounded = 0.01
    elif lot_size_rounded > 100:
        warnings.append(
            f"Position énorme ({lot_size_rounded} lot). "
            f"Vérifiez vos paramètres !"
        )

    units = int(lot_size_rounded * 100000)
    actual_risk = lot_size_rounded * stop_loss_pips * pip_value_per_lot

    return PositionCalculation(
        capital=capital,
        risk_percent=risk_percent,
        risk_amount=risk_amount,
        stop_loss_pips=stop_loss_pips,
        pip_value=pip_value_per_lot,
        lot_size=lot_size_rounded,
        units=units,
        actual_risk=actual_risk,
        warnings=warnings,
    )
