import joblib
import numpy as np
import os

# =========================================
# PATH
# =========================================

MODEL_PATH = "ai/model.pkl"

SCALER_PATH = "ai/scaler.pkl"

# =========================================
# LOAD MODEL
# =========================================

model = None
scaler = None

try:

    if os.path.exists(MODEL_PATH):

        model = joblib.load(
            MODEL_PATH
        )

        print("AI MODEL LOADED")

    if os.path.exists(SCALER_PATH):

        scaler = joblib.load(
            SCALER_PATH
        )

        print("AI SCALER LOADED")

except Exception as e:

    print("AI LOAD ERROR:", e)

# =========================================
# AI PREDICT
# =========================================

def predict_signal(features):

    global model
    global scaler

    if model is None:

        return {

            "signal": "NONE",

            "confidence": 0
        }

    try:

        # =====================================
        # FEATURES
        # HARUS SAMA DENGAN train_ai.py
        # =====================================

        data = [[

            features["ema_fast"],
            features["ema_slow"],

            features["rsi"],

            features["macd"],
            features["macd_signal"],

            features["atr"],
            features["adx"],

            features["volume"],
            features["volume_ma"]

        ]]

        data = np.array(data)

        # =====================================
        # SCALE
        # =====================================

        if scaler is not None:

            data = scaler.transform(data)

        # =====================================
        # PREDICT
        # =====================================

        prediction = model.predict(
            data
        )[0]

        probabilities = model.predict_proba(
            data
        )[0]

        confidence = round(
            max(probabilities) * 100,
            2
        )

        # =====================================
        # SIGNAL
        # =====================================

        signal = "NONE"

        if prediction == 1:

            signal = "LONG"

        elif prediction == 0:

            signal = "SHORT"

        # =====================================
        # FILTER CONFIDENCE
        # =====================================

        if confidence < 55:

            signal = "NONE"

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
