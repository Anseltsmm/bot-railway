from indicators import add_indicators

def analyze(df):

    df = add_indicators(df)

    latest = df.iloc[-1]

    long_score = 0
    short_score = 0

    # EMA TREND

    if latest["ema20"] > latest["ema50"]:
        long_score += 40
        trend = "BULLISH"
    else:
        short_score += 40
        trend = "BEARISH"

    # RSI

    if latest["rsi"] > 55:
        long_score += 30

    if latest["rsi"] < 45:
        short_score += 30

    # STRUCTURE

    if latest["close"] > latest["ema20"]:
        long_score += 30
        structure = "UPTREND"
    else:
        short_score += 30
        structure = "DOWNTREND"

    signal = "NONE"

    confidence = max(long_score, short_score)

    if long_score >= 70:
        signal = "LONG"

    if short_score >= 70:
        signal = "SHORT"

    return {

        "signal": signal,

        "trend": trend,

        "structure": structure,

        "rsi": round(latest["rsi"], 2),

        "long_score": long_score,

        "short_score": short_score,

        "confidence": confidence
    }
