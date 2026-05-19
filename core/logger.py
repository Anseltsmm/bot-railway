import csv
import os

DATASET_FILE = "data/ai_dataset.csv"

HEADERS = [
    "rsi",
    "adx",
    "long_score",
    "short_score",
    "bullish_tf",
    "bearish_tf",
    "support_distance",
    "resistance_distance",
    "signal",
    "result"
]

# =========================================
# INIT DATASET
# =========================================

def init_dataset():

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
