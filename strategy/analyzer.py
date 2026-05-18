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
    structure = "RANGING"
    confidence = 0

    # =========================================
    # MAIN TF DATA
    # =========================================

    df = get_tf_dataframe("1m")

    last = df.iloc[-1]

    current_price = float(last["close"])

    # =========================================
    # SUPPORT & RESISTANCE
    # =========================================

    snr = get_support_resistance(df)

    support = snr["support"]
    resistance = snr["resistance"]

    # =========================================
    # DISTANCE TO SNR
    # =========================================

    distance = calculate_snr_distance(
        price=current_price,
        support=support,
        resistance=resistance
    )

    support_distance = distance[
        "support_distance"
    ]

    resistance_distance = distance[
        "resistance_distance"
    ]

    # =========================================
    # INDICATORS
    # =========================================

    rsi = float(last["rsi"])

    ema_fast = float(last["ema_fast"])
    ema_slow = float(last["ema_slow"])

    macd = float(last["macd"])
    macd_signal = float(last["macd_signal"])

    adx = float(last["adx"])

    volume = float(last["volume"])
    volume_ma = float(last["volume_ma"])

    high_volume = volume > volume_ma

    # =========================================
    # TREND
    # =========================================

    if bullish_tf > bearish_tf:

        trend = "BULLISH"

    elif bearish_tf > bullish_tf:

        trend = "BEARISH"

    # =========================================
    # CONFIDENCE BASE
    # =========================================

    score_diff = abs(
        long_score - short_score
    )

    confidence = min(
        100,
        score_diff * 5
    )

    # =========================================
    # BONUS CONFIDENCE
    # =========================================

    # EMA TREND

    if ema_fast > ema_slow:

        confidence += 5

    else:

        confidence += 5

    # MACD

    if macd > macd_signal:

        confidence += 5

    else:

        confidence += 5

    # ADX

    if adx >= 25:

        confidence += 10

    # VOLUME

    if high_volume:

        confidence += 5

    # LIMIT MAX

    confidence = min(
        100,
        round(confidence)
    )

    # =========================================
    # LONG FILTER
    # =========================================

    long_valid = (

        bullish_tf >= 4

        and

        long_score > short_score

        and

        confidence >= 40

        and

        resistance_distance > 0.2

        and

        ema_fast > ema_slow

        and

        macd > macd_signal

        and

        rsi > 50

    )

    # =========================================
    # SHORT FILTER
    # =========================================

    short_valid = (

        bearish_tf >= 4

        and

        short_score > long_score

        and

        confidence >= 40

        and

        support_distance > 0.2

        and

        ema_fast < ema_slow

        and

        macd < macd_signal

        and

        rsi < 50

    )

    # =========================================
    # SIGNAL
    # =========================================

    if long_valid:

        signal = "LONG"

    elif short_valid:

        signal = "SHORT"

    # =========================================
    # STRUCTURE
    # =========================================

    if signal == "LONG":

        structure = "UPTREND"

    elif signal == "SHORT":

        structure = "DOWNTREND"

    # =========================================
    # RETURN
    # =========================================

    return {

        # =========================
        # SIGNAL
        # =========================

        "signal": signal,

        "trend": trend,

        "structure": structure,

        "confidence": confidence,

        # =========================
        # SCORE
        # =========================

        "long_score": long_score,

        "short_score": short_score,

        "bullish_tf": bullish_tf,

        "bearish_tf": bearish_tf,

        # =========================
        # INDICATORS
        # =========================

        "rsi": round(rsi, 2),

        "adx": round(adx, 2),

        # =========================
        # MTF
        # =========================

        "mtf": data["mtf"],

        # =========================
        # SUPPORT RESISTANCE
        # =========================

        "support": round(support, 4),

        "resistance": round(resistance, 4),

        "support_distance": round(
            support_distance,
            2
        ),

        "resistance_distance": round(
            resistance_distance,
            2
        ),

        # =========================
        # EXTRA
        # =========================

        "high_volume": high_volume
    }
