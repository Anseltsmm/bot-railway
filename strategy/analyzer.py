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
    # MULTI TF DATA
    # =========================================

    data = calculate_mtf()

    long_score = data["long_score"]
    short_score = data["short_score"]

    bullish_tf = data["bullish_tf"]
    bearish_tf = data["bearish_tf"]

    signal = "NONE"

    trend = "SIDEWAYS"

    structure = "RANGING"

    strategy_confidence = 0

    # =========================================
    # MAIN TF
    # =========================================

    df = get_tf_dataframe("5m")

    last = df.iloc[-1]

    current_price = float(
        last["close"]
    )

    # =========================================
    # SUPPORT RESISTANCE
    # =========================================

    snr = get_support_resistance(df)

    support = float(
        snr["support"]
    )

    resistance = float(
        snr["resistance"]
    )

    # =========================================
    # DISTANCE
    # =========================================

    distance = calculate_snr_distance(

        price=current_price,

        support=support,

        resistance=resistance
    )

    support_distance = float(
        distance["support_distance"]
    )

    resistance_distance = float(
        distance["resistance_distance"]
    )

    # =========================================
    # INDICATORS
    # =========================================

    rsi = float(last["rsi"])

    ema_fast = float(
        last["ema_fast"]
    )

    ema_slow = float(
        last["ema_slow"]
    )

    macd = float(
        last["macd"]
    )

    macd_signal = float(
        last["macd_signal"]
    )

    adx = float(
        last["adx"]
    )

    atr = float(
        last["atr"]
    )

    volume = float(
        last["volume"]
    )

    volume_ma = float(
        last["volume_ma"]
    )

    high_volume = (
        volume > volume_ma
    )

    # =========================================
    # TREND
    # =========================================

    if bullish_tf > bearish_tf:

        trend = "BULLISH"

    elif bearish_tf > bullish_tf:

        trend = "BEARISH"

    # =========================================
    # BASE CONFIDENCE
    # =========================================

    score_diff = abs(
        long_score - short_score
    )

    strategy_confidence = (
        score_diff * 5
    )

    # =========================================
    # EMA BONUS
    # =========================================

    if ema_fast > ema_slow:

        strategy_confidence += 5

    elif ema_fast < ema_slow:

        strategy_confidence += 5

    # =========================================
    # MACD BONUS
    # =========================================

    if macd > macd_signal:

        strategy_confidence += 5

    elif macd < macd_signal:

        strategy_confidence += 5

    # =========================================
    # ADX BONUS
    # =========================================

    if adx >= 25:

        strategy_confidence += 10

    elif adx >= 20:

        strategy_confidence += 5

    # =========================================
    # VOLUME BONUS
    # =========================================

    if high_volume:

        strategy_confidence += 5

    # =========================================
    # LIMIT CONFIDENCE
    # =========================================

    strategy_confidence = min(
        100,
        round(strategy_confidence)
    )

    # =========================================
    # LONG VALIDATION
    # =========================================

    long_valid = (

        bullish_tf >= 5

        and

        long_score > short_score

        and

        strategy_confidence >= 45

        and

        resistance_distance > 0.3

        and

        ema_fast > ema_slow

        and

        macd > macd_signal

        and

        rsi > 50
    )

    # =========================================
    # SHORT VALIDATION
    # =========================================

    short_valid = (

        bearish_tf >= 5

        and

        short_score > long_score

        and

        strategy_confidence >= 45

        and

        support_distance > 0.3

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

        # =====================================
        # SIGNAL
        # =====================================

        "signal": signal,

        "trend": trend,

        "structure": structure,

        "strategy_confidence":
        strategy_confidence,

        # =====================================
        # SCORES
        # =====================================

        "long_score": long_score,

        "short_score": short_score,

        "bullish_tf": bullish_tf,

        "bearish_tf": bearish_tf,

        # =====================================
        # INDICATORS
        # =====================================

        "rsi": round(rsi, 2),

        "adx": round(adx, 2),

        "atr": round(atr, 4),

        "ema_fast": round(
            ema_fast,
            4
        ),

        "ema_slow": round(
            ema_slow,
            4
        ),

        "macd": round(
            macd,
            4
        ),

        "macd_signal": round(
            macd_signal,
            4
        ),

        # =====================================
        # VOLUME
        # =====================================

        "volume": round(
            volume,
            2
        ),

        "volume_ma": round(
            volume_ma,
            2
        ),

        "high_volume": high_volume,

        # =====================================
        # MTF
        # =====================================

        "mtf": data["mtf"],

        # =====================================
        # SUPPORT RESISTANCE
        # =====================================

        "support": round(
            support,
            4
        ),

        "resistance": round(
            resistance,
            4
        ),

        "support_distance": round(
            support_distance,
            2
        ),

        "resistance_distance": round(
            resistance_distance,
            2
        ),

        # =====================================
        # EXTRA
        # =====================================

        "current_price": round(
            current_price,
            4
        )
    }
