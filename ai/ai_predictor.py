import joblib
import numpy as np
import os

MODEL_PATH = "models/ai_model.pkl"

model = None

# =========================================
# LOAD MODEL
# =========================================

if os.path.exists(MODEL_PATH):

    try:

        model = joblib.load(MODEL_PATH)

        print("AI MODEL LOADED")

    except Exception as e:

        print("MODEL LOAD ERROR:", e)

# =========================================
# AI PREDICT
# =========================================

def predict_signal(features):

    global model

    if model is None:

        return {
            "signal": "NONE",
            "confidence": 0
        }

    try:

        data = np.array([[
            features["rsi"],
            features["adx"],
            features["long_score"],
            features["short_score"],
            features["bullish_tf"],
            features["bearish_tf"],
            features["support_distance"],
            features["resistance_distance"]
        ]])

        prediction = model.predict(data)[0]

        probability = model.predict_proba(data)[0]

        confidence = round(
            max(probability) * 100,
            2
        )

        signal = "NONE"

        # =====================================
        # LABEL
        # =====================================

        if prediction == 1:
            signal = "LONG"

        elif prediction == -1:
            signal = "SHORT"

        return {
            "signal": signal,
            "confidence": confidence
        }

    except Exception as e:

        print("AI PREDICT ERROR:", e)

        return {
            "signal": "NONE",
            "confidence": 0
        }
