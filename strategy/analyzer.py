from strategy.scorer import calculate_mtf
from strategy.snr import (
    get_support_resistance,
    calculate_snr_distance
)

from strategy.mtf import get_tf_dataframe

# =========================================
# MAIN ANALYZER
# =========================================

def analyze_multi_tf():

    # =========================================
    # MTF DATA
    # =========================================

    data = calculate_mtf()

    long_score = data["long_score"]
    short_score = data["short_score"]

    bullish_tf = data["bullish_tf"]
    bearish_tf = data["bearish_tf"]

    signal = "NONE"

    trend = "SIDEWAYS"

    confidence = 0

    # =========================================
    # GET MAIN TF DATA
    # =========================================

    df = get_tf_dataframe("5m")

    current_price = float(
        df.iloc[-1]["close"]
    )

    # =========================================
    # SUPPORT RESISTANCE
    # =========================================

    snr = get_support_resistance(df)

    support = snr["support"]
    resistance = snr["resistance"]

    # =========================================
    # DISTANCE
    # =========================================

    distance = calculate_snr_distance(
        price=current_price,
        support=support,
        resistance=resistance
    )

    support_distance = (
        distance["support_distance"]
    )

    resistance_distance = (
        distance["resistance_distance"]
    )

    # =========================================
    # TREND
    # =========================================

    if bullish_tf > bearish_tf:

        trend = "BULLISH"

    elif bearish_tf > bullish_tf:

        trend = "BEARISH"

    # =========================================
    # CONFIDENCE
    # =========================================

    score_diff = abs(
        long_score - short_score
    )

    confidence = min(
        100,
        score_diff * 5
    )

    # =========================================
    # LONG SIGNAL
    # =========================================

    if (

        bullish_tf >= 5

        and

        long_score > short_score

        and

        confidence >= 60

        and

        resistance_distance > 0.5

    ):

        signal = "LONG"

    # =========================================
    # SHORT SIGNAL
    # =========================================

    elif (

        bearish_tf >= 5

        and

        short_score > long_score

        and

        confidence >= 60

        and

        support_distance > 0.5

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

        "mtf": data["mtf"],

        # =========================
        # SUPPORT RESISTANCE
        # =========================

        "support": support,

        "resistance": resistance,

        "support_distance":
        support_distance,

        "resistance_distance":
        resistance_distance
    }
