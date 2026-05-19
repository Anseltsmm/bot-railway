import csv
import os

DATASET_FILE = "data/ai_dataset.csv"

HEADERS = [

    # =========================
    # TREND
    # =========================

    "trend",
    "structure",

    # =========================
    # INDICATORS
    # =========================

    "rsi",
    "adx",

    "ema_fast",
    "ema_slow",

    "macd",
    "macd_signal",

    # =========================
    # SCORES
    # =========================

    "long_score",
    "short_score",

    # =========================
    # MTF
    # =========================

    "bullish_tf",
    "bearish_tf",

    # =========================
    # SNR
    # =========================

    "support_distance",
    "resistance_distance",

    # =========================
    # VOLUME
    # =========================

    "high_volume",

    # =========================
    # AI TARGET
    # =========================

    "signal",
    "result"
]

# =========================================
# INIT DATASET
# =========================================

def init_dataset():

    os.makedirs("data", exist_ok=True)

    if not os.path.exists(DATASET_FILE):

        with open(
            DATASET_FILE,
            "w",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow(HEADERS)

# =========================================
# SAVE TRADE
# =========================================

def save_trade(features):

    init_dataset()

    with open(
        DATASET_FILE,
        "a",
        newline=""
    ) as f:

        writer = csv.writer(f)

        writer.writerow(features)
