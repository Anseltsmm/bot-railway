from strategy.timeframe_analysis import (
    get_klines,
    analyze_tf
)

from utils.indicators import (
    ema,
    rsi,
    atr
)

TIMEFRAMES = [
    "1m",
    "5m",
    "15m",
    "1h",
    "4h"
]


def signal(symbol, interval):

    df = get_klines(symbol, interval)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    ema21 = ema(close, 21)
    ema200 = ema(close, 200)

    rsi14 = rsi(close, 14)

    atr14 = atr(high, low, close, 14)

    current_price = close.iloc[-1]

    bullish = (
        ema21.iloc[-1] > ema200.iloc[-1]
        and rsi14.iloc[-1] > 50
    )

    bearish = (
        ema21.iloc[-1] < ema200.iloc[-1]
        and rsi14.iloc[-1] < 50
    )

    mtf_bullish = 0
    mtf_bearish = 0

    mtf = {}

    for tf in TIMEFRAMES:

        result = analyze_tf(symbol, tf)

        mtf[tf] = result

        if result == "BULLISH":
            mtf_bullish += 1

        elif result == "BEARISH":
            mtf_bearish += 1

    sig = "NONE"

    if bullish and mtf_bullish >= 3:
        sig = "LONG"

    elif bearish and mtf_bearish >= 3:
        sig = "SHORT"

    return {

        "symbol": symbol,

        "signal": sig,

        "price": current_price,

        "rsi": round(rsi14.iloc[-1], 2),

        "atr": round(atr14.iloc[-1], 4),

        "mtf": mtf,

        "mtf_bullish": mtf_bullish,

        "mtf_bearish": mtf_bearish
    }
