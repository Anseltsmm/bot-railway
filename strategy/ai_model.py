import pandas as pd
import joblib
import os

from sklearn.ensemble import RandomForestClassifier

MODEL_PATH = "models/model.pkl"

# =========================================
# TRAIN MODEL
# =========================================

def train_ai():

    try:

        df = pd.read_csv(
            "data/ai_dataset.csv"
        )

        if len(df) < 30:

            print("AI DATA NOT ENOUGH")

            return

        X = df[[
            "rsi",
            "adx",
            "long_score",
            "short_score",
            "bullish_tf",
            "bearish_tf",
            "support_distance",
            "resistance_distance"
        ]]

        y = df["result"]

        model = RandomForestClassifier(
            n_estimators=100
        )

        model.fit(X, y)

        joblib.dump(
            model,
            MODEL_PATH
        )

        print("AI MODEL TRAINED")

    except Exception as e:

        print("AI TRAIN ERROR:", e)

# =========================================
# LOAD MODEL
# =========================================

def load_model():

    if not os.path.exists(MODEL_PATH):

        return None

    return joblib.load(MODEL_PATH)

# =========================================
# PREDICT
# =========================================

def predict_trade(features):

    model = load_model()

    if model is None:

        return {
            "probability": 50
        }

    X = [[

        features["rsi"],
        features["adx"],
        features["long_score"],
        features["short_score"],
        features["bullish_tf"],
        features["bearish_tf"],
        features["support_distance"],
        features["resistance_distance"]

    ]]

    probability = max(
        model.predict_proba(X)[0]
    ) * 100

    return {
        "probability": round(probability, 2)
    }
