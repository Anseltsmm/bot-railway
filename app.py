from flask import Flask, render_template
from flask_socketio import SocketIO

import threading
import time
import os
import pandas as pd
import numpy as np
import joblib

from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from core.trader import *
from strategy.analyzer import analyze_multi_tf
from state import bot_state
from config import *

# =========================================
# FLASK
# =========================================

app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

# =========================================
# LOAD AI
# =========================================

print("=" * 50)
print("LOADING AI MODEL...")
print("=" * 50)

ai_model = joblib.load("ai/model.pkl")

ai_scaler = joblib.load("ai/scaler.pkl")

print("AI MODEL LOADED")
print("=" * 50)

# =========================================
# ROUTE
# =========================================

@app.route("/")
def index():

    return render_template("dashboard.html")

# =========================================
# AI PREDICTION
# =========================================

def ai_predict(df):

    try:

        # =========================
        # EMA
        # =========================

        ema_fast = EMAIndicator(
            close=df["close"],
            window=20
        ).ema_indicator().iloc[-1]

        ema_slow = EMAIndicator(
            close=df["close"],
            window=50
        ).ema_indicator().iloc[-1]

        # =========================
        # RSI
        # =========================

        rsi = RSIIndicator(
            close=df["close"],
            window=14
        ).rsi().iloc[-1]

        # =========================
        # MACD
        # =========================

        macd_obj = MACD(df["close"])

        macd = macd_obj.macd().iloc[-1]

        macd_signal = macd_obj.macd_signal().iloc[-1]

        # =========================
        # ATR
        # =========================

        atr = AverageTrueRange(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=14
        ).average_true_range().iloc[-1]

        # =========================
        # ADX
        # =========================

        adx = ADXIndicator(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=14
        ).adx().iloc[-1]

        # =========================
        # VOLUME
        # =========================

        volume = df["volume"].iloc[-1]

        volume_ma = (
            df["volume"]
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        # =========================
        # FEATURES
        # =========================

        features = [[

            ema_fast,
            ema_slow,

            rsi,

            macd,
            macd_signal,

            atr,
            adx,

            volume,
            volume_ma
        ]]

        # =========================
        # SCALE
        # =========================

        scaled = ai_scaler.transform(features)

        # =========================
        # PREDICT
        # =========================

        prediction = ai_model.predict(scaled)[0]

        probabilities = ai_model.predict_proba(scaled)[0]

        confidence = round(
            max(probabilities) * 100,
            2
        )

        signal = "LONG" if prediction == 1 else "SHORT"

        return signal, confidence

    except Exception as e:

        print("AI ERROR:", e)

        return None, 0

# =========================================
# MAIN LOOP
# =========================================

def trading_loop():

    while True:

        try:

            # =========================
            # ANALYZE STRATEGY
            # =========================

            result = analyze_multi_tf()

            # =========================
            # MARKET INFO
            # =========================

            price = get_price(SYMBOL)

            bot_state["symbol"] = SYMBOL

            bot_state["price"] = price

            bot_state["balance"] = get_balance()

            # =========================
            # UPDATE SIGNAL
            # =========================

            bot_state.update(result)

            # =========================
            # SYNC POSITION
            # =========================

            sync_position()

            # =========================
            # UPDATE PNL
            # =========================

            update_pnl()

            # =========================
            # UPDATE STATS
            # =========================

            update_trade_stats()

            # =========================
            # AI ANALYSIS
            # =========================

            klines = client.futures_klines(
                symbol=SYMBOL,
                interval="5m",
                limit=100
            )

            df = pd.DataFrame(klines)

            df = df.iloc[:, :6]

            df.columns = [
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]

            df = df.astype(float)

            ai_signal, ai_confidence = ai_predict(df)

            bot_state["ai_signal"] = ai_signal

            bot_state["ai_confidence"] = ai_confidence

            # =========================
            # COOLDOWN
            # =========================

            now = time.time()

            cooldown_passed = (
                now - bot_state["last_trade_time"]
            ) > TRADE_COOLDOWN

            # =========================
            # LONG ENTRY
            # =========================

            if (

                result["signal"] == "LONG"

                and

                ai_signal == "LONG"

                and

                ai_confidence >= 70

                and

                not has_open_position(SYMBOL)

                and

                cooldown_passed
            ):

                print("=" * 50)
                print("LONG ENTRY CONFIRMED")
                print(f"AI CONFIDENCE: {ai_confidence}%")
                print("=" * 50)

                place_long()

                bot_state["last_trade_time"] = now

            # =========================
            # SHORT ENTRY
            # =========================

            elif (

                result["signal"] == "SHORT"

                and

                ai_signal == "SHORT"

                and

                ai_confidence >= 70

                and

                not has_open_position(SYMBOL)

                and

                cooldown_passed
            ):

                print("=" * 50)
                print("SHORT ENTRY CONFIRMED")
                print(f"AI CONFIDENCE: {ai_confidence}%")
                print("=" * 50)

                place_short()

                bot_state["last_trade_time"] = now

            # =========================
            # SOCKET UPDATE
            # =========================

            socketio.emit(
                "update",
                bot_state
            )

            # =========================
            # TERMINAL LOG
            # =========================

            print(

                f"{SYMBOL} | "

                f"SIGNAL: {bot_state['signal']} | "

                f"AI: {ai_signal} | "

                f"CONF: {ai_confidence}% | "

                f"POSITION: {bot_state['position']} | "

                f"PNL: {bot_state['pnl']}"
            )

        except Exception as e:

            print("=" * 50)
            print("BOT ERROR:", e)
            print("=" * 50)

        time.sleep(SOCKET_INTERVAL)

# =========================================
# START
# =========================================

if __name__ == "__main__":

    threading.Thread(
        target=trading_loop,
        daemon=True
    ).start()

    PORT = int(
        os.environ.get("PORT", 5000)
    )

    socketio.run(
        app,
        host="0.0.0.0",
        port=PORT,
        debug=False,
        allow_unsafe_werkzeug=True
            )
