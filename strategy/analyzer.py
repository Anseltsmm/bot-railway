from strategy.scorer import calculate_mtf
from strategy.snr import (
    get_support_resistance,
    calculate_snr_distance
)

# =========================================
# MAIN ANALYZER
# =========================================

def analyze_multi_tf():

    data = calculate_mtf()

    long_score = data["long_score"]
    short_score = data["short_score"]

    bullish_tf = data["bullish_tf"]
    bearish_tf = data["bearish_tf"]

    signal = "NONE"

    trend = "SIDEWAYS"

    confidence = 0

    # =========================================
    # TREND
    # =========================================

    if bullish_tf > bearish_tf:
        trend = "BULLISH"

    elif bearish_tf > bullish_tf:
        trend = "BEARISH"

    # =========================================
    # SIGNAL LOGIC
    # =========================================

    score_diff = abs(
        long_score - short_score
    )

    confidence = min(
        100,
        score_diff * 5
    )

    # =========================================
    # LONG
    # =========================================

    if (
        bullish_tf >= 5
        and
        long_score > short_score
        and
        confidence >= 60
    ):

        signal = "LONG"

    # =========================================
    # SHORT
    # =========================================

    elif (
        bearish_tf >= 5
        and
        short_score > long_score
        and
        confidence >= 60
    ):

        signal = "SHORT"

    # =========================================
    # STRUCTURE
    # =========================================

    structure = "RANGING"

    if confidence >= 70:

        if signal == "LONG":
            structure = "UPTREND"

        elif signal == "SHORT":
            structure = "DOWNTREND"

    # =========================================
    # RETURN
    # =========================================

    return {

        "signal": signal,

        "trend": trend,

        "structure": structure,

        "confidence": confidence,

        "long_score": long_score,

        "short_score": short_score,

        "rsi": data["rsi"],

        "mtf": data["mtf"]
    }
