import pandas as pd

from core.trader import client
from config import *
from strategy.indicators import add_indicators

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

    return add_indicators(df)

def analyze_tf(tf):

    df = get_tf_dataframe(tf)

    last = df.iloc[-1]

    bullish = 0
    bearish = 0

    # ====================================
    # EMA TREND
    # ====================================

    if last["ema_fast"] > last["ema_slow"]:
        bullish += 2
    else:
        bearish += 2

    # ====================================
    # RSI
    # ====================================

    if last["rsi"] > 55:
        bullish += 1

    if last["rsi"] < 45:
        bearish += 1

    # ====================================
    # MACD
    # ====================================

    if last["macd"] > last["macd_signal"]:
        bullish += 1
    else:
        bearish += 1

    # ====================================
    # ADX TREND STRENGTH
    # ====================================

    strong_trend = last["adx"] >= 20

    if strong_trend:

        bullish += 1
        bearish += 1

    # ====================================
    # VOLUME SPIKE
    # ====================================

    high_volume = (
        last["volume"] >
        last["volume_ma"]
    )

    if high_volume:

        bullish += 1
        bearish += 1

    # ====================================
    # ATR VOLATILITY
    # ====================================

    volatility = last["atr"]

    signal = "NEUTRAL"

    if bullish > bearish:
        signal = "BULLISH"

    elif bearish > bullish:
        signal = "BEARISH"

    return {

        "signal": signal,

        "bullish": bullish,

        "bearish": bearish,

        "rsi": round(last["rsi"], 2),

        "adx": round(last["adx"], 2),

        "atr": round(volatility, 4),

        "high_volume": high_volume
    }:

    df = get_tf_dataframe(tf)

    last = df.iloc[-1]

    bullish = 0
    bearish = 0

    # EMA

    if last["ema_fast"] > last["ema_slow"]:
        bullish += 1
    else:
        bearish += 1

    # RSI

    if last["rsi"] > 55:
        bullish += 1

    if last["rsi"] < 45:
        bearish += 1

    # MACD

    if last["macd"] > last["macd_signal"]:
        bullish += 1
    else:
        bearish += 1

    signal = "NEUTRAL"

    if bullish > bearish:
        signal = "BULLISH"

    elif bearish > bullish:
        signal = "BEARISH"

    return {
        "signal": signal,
        "bullish": bullish,
        "bearish": bearish,
        "rsi": round(last["rsi"], 2)
    }
