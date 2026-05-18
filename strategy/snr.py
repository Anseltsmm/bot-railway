import pandas as pd

# =========================
# SUPPORT RESISTANCE
# =========================

def get_support_resistance(df):

    # =========================
    # SWING HIGH
    # =========================

    resistance = (
        df["high"]
        .rolling(20)
        .max()
        .iloc[-1]
    )

    # =========================
    # SWING LOW
    # =========================

    support = (
        df["low"]
        .rolling(20)
        .min()
        .iloc[-1]
    )

    return {
        "support": round(support, 4),
        "resistance": round(resistance, 4)
    }

# =========================
# DISTANCE TO SNR
# =========================

def calculate_snr_distance(
    price,
    support,
    resistance
):

    distance_to_support = (
        (
            price - support
        ) / price
    ) * 100

    distance_to_resistance = (
        (
            resistance - price
        ) / price
    ) * 100

    return {
        "support_distance":
        round(distance_to_support, 2),

        "resistance_distance":
        round(distance_to_resistance, 2)
    }
