from strategy.mtf import TIMEFRAMES, analyze_tf

def calculate_mtf():

    mtf = {}

    bullish_tf = 0
    bearish_tf = 0

    total_long = 0
    total_short = 0

    rsi = 50

    for tf in TIMEFRAMES:

        result = analyze_tf(tf)

        mtf[tf] = result["signal"]

        total_long += result["bullish"]
        total_short += result["bearish"]

        rsi = result["rsi"]

        if result["signal"] == "BULLISH":
            bullish_tf += 1

        elif result["signal"] == "BEARISH":
            bearish_tf += 1

    return {
        "mtf": mtf,
        "bullish_tf": bullish_tf,
        "bearish_tf": bearish_tf,
        "long_score": total_long,
        "short_score": total_short,
        "rsi": rsi
    }
