import pandas as pd

from core.trader import client
from config import *
from strategy.indicators import add_indicators

# =========================================
# MULTI TIME FRAME
# =========================================

TIMEFRAMES = [
    "1m",
    "5m",
    "15m",
    "1h",
    "2h",
    "4h",
    "1d",
    "1w"
]

# =========================================
# GET DATAFRAME
# =========================================

def get_tf_dataframe(tf):

    klines = client.futures_klines(
        symbol=SYMBOL,
        interval=tf,
        limit=200
    )

    df = pd.DataFrame(klines)

    df = df.iloc[:, :6]

    df.columns = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    df = df.astype(float)

    df = add_indicators(df)

    return df

# =========================================
# ANALYZE SINGLE TF
# =========================================

def analyze_tf(tf):

    df = get_tf_dataframe(tf)

    last = df.iloc[-1]

    bullish = 0
    bearish = 0

    # =========================================
    # EMA TREND
    # =========================================

    if last["ema_fast"] > last["ema_slow"]:
        bullish += 2
    else:
        bearish += 2

    # =========================================
    # RSI
    # =========================================

    if last["rsi"] > 55:
        bullish += 1

    if last["rsi"] < 45:
        bearish += 1

    # =========================================
    # MACD
    # =========================================

    if last["macd"] > last["macd_signal"]:
        bullish += 1
    else:
        bearish += 1

    # =========================================
    # ADX
    # =========================================

    strong_trend = last["adx"] >= 20

    if strong_trend:

        if bullish > bearish:
            bullish += 1

        elif bearish > bullish:
            bearish += 1

    # =========================================
    # VOLUME
    # =========================================

    high_volume = (
        last["volume"] >
        last["volume_ma"]
    )

    if high_volume:

        if bullish > bearish:
            bullish += 1

        elif bearish > bullish:
            bearish += 1

    # =========================================
    # ATR
    # =========================================

    volatility = last["atr"]

    # =========================================
    # SIGNAL
    # =========================================

    signal = "NEUTRAL"

    if bullish > bearish:
        signal = "BULLISH"

    elif bearish > bullish:
        signal = "BEARISH"

    # =========================================
    # RETURN
    # =========================================

    return {

        "signal": signal,

        "bullish": bullish,

        "bearish": bearish,

        "rsi": round(last["rsi"], 2),

        "adx": round(last["adx"], 2),

        "atr": round(volatility, 4),

        "high_volume": high_volume
    }
