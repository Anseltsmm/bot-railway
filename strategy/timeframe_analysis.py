import pandas as pd

from core.client import client
from utils.indicators import ema, rsi


def get_klines(symbol, interval):

    df = pd.DataFrame(
        client.futures_klines(
            symbol=symbol,
            interval=interval,
            limit=300
        )
    )

    df = df.iloc[:, :6]

    df.columns = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for col in df.columns[1:]:
        df[col] = df[col].astype(float)

    return df


def analyze_tf(symbol, tf):

    try:

        df = get_klines(symbol, tf)

        close = df["close"]

        ema21 = ema(close, 21)
        ema200 = ema(close, 200)

        rsi14 = rsi(close, 14)

        bullish = (
            ema21.iloc[-1] > ema200.iloc[-1]
            and rsi14.iloc[-1] > 50
        )

        bearish = (
            ema21.iloc[-1] < ema200.iloc[-1]
            and rsi14.iloc[-1] < 50
        )

        if bullish:
            return "BULLISH"

        if bearish:
            return "BEARISH"

        return "SIDEWAYS"

    except:
        return "SIDEWAYS"
