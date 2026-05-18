from core.exchange import client
import pandas as pd

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

def get_tf_signal(symbol, tf):

    klines = client.futures_klines(
        symbol=symbol,
        interval=tf,
        limit=100
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

    ema20 = df["close"].ewm(span=20).mean()
    ema50 = df["close"].ewm(span=50).mean()

    last_ema20 = ema20.iloc[-1]
    last_ema50 = ema50.iloc[-1]

    if last_ema20 > last_ema50:
        return "BULLISH"

    if last_ema20 < last_ema50:
        return "BEARISH"

    return "SIDEWAYS"


def analyze_mtf(symbol):

    result = {}

    bullish = 0
    bearish = 0

    for tf in TIMEFRAMES:

        signal = get_tf_signal(symbol, tf)

        result[tf] = signal

        if signal == "BULLISH":
            bullish += 1

        if signal == "BEARISH":
            bearish += 1

    return result, bullish, bearish
