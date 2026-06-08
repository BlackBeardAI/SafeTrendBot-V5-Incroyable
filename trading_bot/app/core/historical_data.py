"""
Récupération de données historiques (jusqu'à 5 ans) pour analyse de tendances.

Utilise yfinance (gratuit) pour les actions/forex et ccxt pour le crypto.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class TrendAnalysis:
    """Résultat de l'analyse de tendance"""
    symbol: str
    period_years: float
    start_price: float
    end_price: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    volatility_pct: float           # Volatilité annualisée
    sharpe_ratio: float
    long_term_trend: str            # "Haussière", "Baissière", "Latérale"
    current_position: str           # "Près des plus hauts", "Plus bas", etc.
    candles_count: int


def fetch_historical_yfinance(symbol: str, years: int = 5) -> Optional[Dict]:
    """
    Récupère l'historique sur N années via yfinance.

    Symboles compatibles yfinance :
    - Forex : EURUSD=X, GBPUSD=X, USDJPY=X
    - Or : GC=F (Gold futures), XAUUSD=X
    - Indices : ^GSPC (S&P500), ^IXIC (NASDAQ), ^FCHI (CAC40)
    - Actions : AAPL, MSFT, etc.
    - Crypto : BTC-USD, ETH-USD
    """
    try:
        import yfinance as yf
    except ImportError:
        return None

    try:
        # Convertir le symbole MT5 en format yfinance si nécessaire
        yf_symbol = _to_yfinance_symbol(symbol)

        ticker = yf.Ticker(yf_symbol)
        end = datetime.now()
        start = end - timedelta(days=years * 365)

        df = ticker.history(start=start, end=end, interval='1d')
        if df is None or df.empty:
            return None

        return {
            'dates': df.index.tolist(),
            'open': df['Open'].tolist(),
            'high': df['High'].tolist(),
            'low': df['Low'].tolist(),
            'close': df['Close'].tolist(),
            'volume': df['Volume'].tolist(),
            'symbol': symbol,
            'yf_symbol': yf_symbol,
        }
    except Exception as e:
        print(f"Erreur fetch_historical pour {symbol}: {e}")
        return None


def _to_yfinance_symbol(symbol: str) -> str:
    """Convertit un symbole en format yfinance"""
    s = symbol.upper().replace("/", "")

    # Forex : 6 caractères type EURUSD → EURUSD=X
    if len(s) == 6 and s.isalpha():
        return f"{s}=X"

    # Or
    if s in ("XAU", "XAUUSD", "GOLD"):
        return "GC=F"

    # Si déjà au format yfinance
    if "=" in symbol or "-" in symbol or "^" in symbol:
        return symbol

    # Crypto
    if s.endswith("USD") and s[:-3] in ("BTC", "ETH", "XRP", "ADA", "SOL", "DOT"):
        return f"{s[:-3]}-USD"

    # Indices courants
    indices_map = {
        "SPX500": "^GSPC", "S&P500": "^GSPC", "SP500": "^GSPC",
        "NASDAQ": "^IXIC", "NAS100": "^IXIC",
        "CAC40": "^FCHI",
        "DAX": "^GDAXI", "DAX40": "^GDAXI",
        "DOW": "^DJI", "US30": "^DJI",
        "FTSE": "^FTSE", "UK100": "^FTSE",
        "NIKKEI": "^N225",
    }
    if s in indices_map:
        return indices_map[s]

    return symbol


def analyze_trend(historical_data: Dict) -> Optional[TrendAnalysis]:
    """Analyse une série historique pour en sortir des métriques de tendance."""
    if not historical_data or not historical_data.get('close'):
        return None

    closes = historical_data['close']
    if len(closes) < 30:
        return None

    try:
        import numpy as np
    except ImportError:
        # Fallback sans numpy
        return _analyze_trend_simple(historical_data)

    closes_arr = np.array(closes)
    start_price = float(closes_arr[0])
    end_price = float(closes_arr[-1])
    total_return = (end_price / start_price - 1) * 100

    # Période en années
    days = len(closes)
    years = days / 252  # ~252 jours de trading par an

    # Rendement annualisé
    if years > 0:
        annualized = ((end_price / start_price) ** (1 / years) - 1) * 100
    else:
        annualized = 0.0

    # Drawdown maximum
    peak = closes_arr[0]
    max_dd = 0.0
    for price in closes_arr:
        if price > peak:
            peak = price
        dd = (price / peak - 1) * 100
        if dd < max_dd:
            max_dd = dd

    # Volatilité annualisée (écart-type des rendements quotidiens × √252)
    daily_returns = np.diff(closes_arr) / closes_arr[:-1]
    volatility = float(np.std(daily_returns) * np.sqrt(252) * 100)

    # Sharpe ratio simplifié (rendement / volatilité)
    sharpe = (annualized / volatility) if volatility > 0 else 0.0

    # Tendance long terme : moyenne mobile 200 jours vs prix actuel
    if len(closes_arr) >= 200:
        ma200 = float(np.mean(closes_arr[-200:]))
        ma50 = float(np.mean(closes_arr[-50:]))
        if end_price > ma200 * 1.05 and ma50 > ma200:
            trend = "Haussière (long terme)"
        elif end_price < ma200 * 0.95 and ma50 < ma200:
            trend = "Baissière (long terme)"
        else:
            trend = "Latérale / Indécise"
    else:
        trend = "Données insuffisantes"

    # Position actuelle vs plus hauts/bas
    high_5y = float(np.max(closes_arr))
    low_5y = float(np.min(closes_arr))
    range_pos = (end_price - low_5y) / (high_5y - low_5y) if high_5y > low_5y else 0.5

    if range_pos > 0.9:
        position = f"Près des plus hauts 5 ans ({range_pos*100:.0f}%)"
    elif range_pos > 0.6:
        position = f"Dans la moitié haute ({range_pos*100:.0f}%)"
    elif range_pos > 0.4:
        position = f"Au milieu du range ({range_pos*100:.0f}%)"
    elif range_pos > 0.1:
        position = f"Dans la moitié basse ({range_pos*100:.0f}%)"
    else:
        position = f"Près des plus bas 5 ans ({range_pos*100:.0f}%)"

    return TrendAnalysis(
        symbol=historical_data.get('symbol', '?'),
        period_years=years,
        start_price=start_price,
        end_price=end_price,
        total_return_pct=total_return,
        annualized_return_pct=annualized,
        max_drawdown_pct=max_dd,
        volatility_pct=volatility,
        sharpe_ratio=sharpe,
        long_term_trend=trend,
        current_position=position,
        candles_count=len(closes),
    )


def _analyze_trend_simple(historical_data: Dict) -> TrendAnalysis:
    """Version sans numpy (limitée)"""
    closes = historical_data['close']
    return TrendAnalysis(
        symbol=historical_data.get('symbol', '?'),
        period_years=len(closes) / 252,
        start_price=closes[0],
        end_price=closes[-1],
        total_return_pct=(closes[-1] / closes[0] - 1) * 100,
        annualized_return_pct=0,
        max_drawdown_pct=0,
        volatility_pct=0,
        sharpe_ratio=0,
        long_term_trend="Calcul indisponible (numpy requis)",
        current_position="?",
        candles_count=len(closes),
    )
