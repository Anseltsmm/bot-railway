from strategy.scorer import calculate_mtf

def analyze_multi_tf():

    data = calculate_mtf()

    signal = "NONE"

    confidence = 0

    trend = "SIDEWAYS"

    # ====================================
    # TREND
    # ====================================

    if data["bullish_tf"] >= 5:
        trend = "BULLISH"

    elif data["bearish_tf"] >= 5:
        trend = "BEARISH"

    # ====================================
    # ENTRY LONG
    # ====================================

    if (
        data["bullish_tf"] >= 5
        and
        data["long_score"] >
        data["short_score"]
    ):

        signal = "LONG"

        confidence = round(
            (
                data["bullish_tf"] / 8
            ) * 100,
            2
        )

    # ====================================
    # ENTRY SHORT
    # ====================================

    elif (
        data["bearish_tf"] >= 5
        and
        data["short_score"] >
        data["long_score"]
    ):

        signal = "SHORT"

        confidence = round(
            (
                data["bearish_tf"] / 8
            ) * 100,
            2
        )

    return {

        "signal": signal,

        "trend": trend,

        "structure": trend,

        "confidence": confidence,

        "long_score": data["long_score"],

        "short_score": data["short_score"],

        "rsi": data["rsi"],

        "mtf_bullish": data["bullish_tf"],

        "mtf_bearish": data["bearish_tf"],

        "mtf": data["mtf"]
    }
