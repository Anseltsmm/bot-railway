import ta

from core.mtf_analysis import analyze_mtf

def analyze(df, symbol):

    close = df["close"]

    ema20 = ta.trend.ema_indicator(close, 20)
    ema50 = ta.trend.ema_indicator(close, 50)

    rsi = ta.momentum.rsi(close, 14)

    price = close.iloc[-1]

    mtf, bull_tf, bear_tf = analyze_mtf(symbol)

    long_score = 0
    short_score = 0

    # EMA
    if ema20.iloc[-1] > ema50.iloc[-1]:
        long_score += 2
    else:
        short_score += 2

    # RSI
    if rsi.iloc[-1] < 70:
        long_score += 1

    if rsi.iloc[-1] > 30:
        short_score += 1

    # MTF
    if bull_tf >= 5:
        long_score += 3

    if bear_tf >= 5:
        short_score += 3

    signal = "NONE"

    if (
        long_score >= 5
        and
        long_score > short_score + 1
    ):
        signal = "LONG"

    if (
        short_score >= 5
        and
        short_score > long_score + 1
    ):
        signal = "SHORT"

    return {

        "signal": signal,

        "price": price,

        "rsi": round(rsi.iloc[-1], 2),

        "long_score": long_score,

        "short_score": short_score,

        "confidence": max(
            long_score,
            short_score
        ) * 10,

        "mtf": mtf,

        "mtf_bullish": bull_tf,

        "mtf_bearish": bear_tf,

        "trend":
        "BULLISH"
        if bull_tf > bear_tf
        else "BEARISH",

        "structure":
        "UPTRAND"
        if ema20.iloc[-1] > ema50.iloc[-1]
        else "DOWNTREND"
    }
