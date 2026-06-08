"""
TEST SIGNAL - SafeTrendBot
==========================
Lance les stratégies SUR LES DONNÉES ACTUELLES de MT5 et montre
pourquoi le bot trade ou ne trade pas.

Usage :
    venv\Scripts\activate.bat
    python TEST_SIGNAL.py

Ce script n'ouvre AUCUNE position. Il analyse seulement.
"""

import sys

print("=" * 60)
print("  TEST SIGNAL SafeTrendBot")
print("  (aucune position ne sera ouverte)")
print("=" * 60)
print()

# Vérification MT5
try:
    import MetaTrader5 as mt5
except ImportError:
    print("❌ MetaTrader5 non installé. Lancez : pip install MetaTrader5")
    input("Entrée pour quitter...")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("❌ numpy non installé. Lancez : pip install numpy")
    input("Entrée pour quitter...")
    sys.exit(1)

# Connexion MT5
print("Connexion à MT5...")
if not mt5.initialize():
    print(f"❌ Échec : {mt5.last_error()}")
    print("  Assurez-vous que MT5 est ouvert et connecté.")
    input("Entrée pour quitter...")
    sys.exit(1)
print("✓ MT5 connecté")
print()

# Symboles à tester
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
TIMEFRAME = mt5.TIMEFRAME_H1   # H1 plus réactif que H4
N_CANDLES = 200

def ema(prices, period):
    """EMA simple"""
    result = [prices[0]]
    k = 2 / (period + 1)
    for p in prices[1:]:
        result.append(p * k + result[-1] * (1 - k))
    return result

def rsi(prices, period=14):
    """RSI"""
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(highs, lows, closes, period=14):
    """ATR"""
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    if len(trs) < period:
        return 0
    return sum(trs[-period:]) / period


print(f"Analyse des signaux sur {TIMEFRAME}...")
print(f"{'Symbole':<12} {'Signal':<12} {'EMA':<15} {'RSI':<12} {'ATR':<12} {'Raison'}")
print("-" * 80)

any_signal = False

for symbol in SYMBOLS:
    # Activer le symbole
    mt5.symbol_select(symbol, True)

    # Récupérer les bougies
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, N_CANDLES)
    if rates is None or len(rates) < 50:
        print(f"{symbol:<12} {'N/A':<12} Pas de données")
        continue

    closes = [r['close'] for r in rates]
    highs  = [r['high']  for r in rates]
    lows   = [r['low']   for r in rates]

    ema50  = ema(closes, 50)
    ema200 = ema(closes, 200) if len(closes) >= 200 else ema(closes, 50)
    rsi_val = rsi(closes[-15:])
    atr_val = atr(highs, lows, closes)

    current = closes[-1]
    e50 = ema50[-1]
    e200 = ema200[-1]

    # Signal simplifié
    trend_bull = e50 > e200 and current > e50
    trend_bear = e50 < e200 and current < e50
    rsi_ok_buy  = 30 < rsi_val < 70
    rsi_ok_sell = 30 < rsi_val < 70

    signal = "NEUTRE"
    reason = ""

    if trend_bull and rsi_ok_buy:
        signal = "🟢 BUY"
        reason = f"EMA50>{e50:.5f} RSI={rsi_val:.0f} OK"
        any_signal = True
    elif trend_bear and rsi_ok_sell:
        signal = "🔴 SELL"
        reason = f"EMA50<{e50:.5f} RSI={rsi_val:.0f} OK"
        any_signal = True
    elif not (trend_bull or trend_bear):
        reason = "Pas de tendance claire (EMA50 ≈ EMA200)"
    elif rsi_val > 70:
        reason = f"RSI={rsi_val:.0f} surachat (>70)"
    elif rsi_val < 30:
        reason = f"RSI={rsi_val:.0f} survente (<30)"
    else:
        reason = "Conditions non remplies"

    ema_str = f"{e50:.5f}"
    rsi_str = f"{rsi_val:.1f}"
    atr_str = f"{atr_val:.5f}"

    print(f"{symbol:<12} {signal:<12} {ema_str:<15} {rsi_str:<12} {atr_str:<12} {reason}")

print()

if any_signal:
    print("✅ Des signaux sont disponibles !")
    print()
    print("Si le bot ne les trade pas, vérifiez :")
    print("  1. Le bot est-il DÉMARRÉ ? (bouton ▶ dans la sidebar)")
    print("  2. Êtes-vous en mode Paper Trading ? (recommandé)")
    print("  3. Dans Profils trading, sélectionnez 'Normal'")
    print("     (min 2 stratégies d'accord + 50% confiance)")
    print("  4. Les filtres (volatilité, news) peuvent bloquer.")
    print("     Vérifiez l'onglet Journaux pour voir pourquoi.")
else:
    print("⏳ Pas de signal fort en ce moment.")
    print()
    print("C'est normal. Le marché n'est pas toujours en tendance.")
    print("Sur H1, des signaux apparaissent typiquement :")
    print("  • Plusieurs fois par jour (H1)")
    print("  • 1-3 fois par semaine (H4)")
    print()
    print("💡 Pour voir plus de trades : allez dans 'Profils trading'")
    print("   et choisissez un profil plus réactif.")

print()
mt5.shutdown()
print("MT5 déconnecté proprement.")
input("\nEntrée pour quitter...")
