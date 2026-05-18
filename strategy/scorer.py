from strategy.mtf import (
    TIMEFRAMES,
    analyze_tf
)

# =========================================
# MULTI TF SCORER
# =========================================

def calculate_mtf():

    mtf = {}

    bullish_tf = 0
    bearish_tf = 0

    total_long = 0
    total_short = 0

    avg_rsi = 0

    success_tf = 0

    # =========================================
    # LOOP ALL TIMEFRAMES
    # =========================================

    for tf in TIMEFRAMES:

        try:

            result = analyze_tf(tf)

            mtf[tf] = result["signal"]

            total_long += result["bullish"]
            total_short += result["bearish"]

            avg_rsi += result["rsi"]

            success_tf += 1

            # =========================================
            # TF DIRECTION
            # =========================================

            if result["signal"] == "BULLISH":
                bullish_tf += 1

            elif result["signal"] == "BEARISH":
                bearish_tf += 1

        except Exception as e:

            print(f"{tf} SCORER ERROR:", e)

            mtf[tf] = "ERROR"

    # =========================================
    # AVERAGE RSI
    # =========================================

    if success_tf > 0:
        avg_rsi = avg_rsi / success_tf
    else:
        avg_rsi = 50

    # =========================================
    # RETURN
    # =========================================

    return {

        "mtf": mtf,

        "bullish_tf": bullish_tf,

        "bearish_tf": bearish_tf,

        "long_score": total_long,

        "short_score": total_short,

        "rsi": round(avg_rsi, 2)
    }
