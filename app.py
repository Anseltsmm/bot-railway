from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time
import os
import pandas as pd

from trader import *
from strategy import analyze
from state import bot_state
from config import *

app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

@app.route("/")
def index():
    return render_template("dashboard.html")

def get_klines():

    klines = client.futures_klines(
        symbol=SYMBOL,
        interval=INTERVAL,
        limit=200
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

    return df

def trading_loop():

    while True:

        try:

            # =========================
            # MARKET DATA
            # =========================

            df = get_klines()

            result = analyze(df)

            price = get_price(SYMBOL)

            # =========================
            # UPDATE STATE
            # =========================

            bot_state["symbol"] = SYMBOL
            bot_state["price"] = price
            bot_state["balance"] = get_balance()

            bot_state.update(result)

            # =========================
            # ENTRY
            # =========================

            if (
                result["signal"] == "LONG"
                and
                bot_state["position"] == "NONE"
            ):
                place_long()

            elif (
                result["signal"] == "SHORT"
                and
                bot_state["position"] == "NONE"
            ):
                place_short()

            # =========================
            # SOCKET EMIT
            # =========================

            socketio.emit(
                "update",
                bot_state
            )

            print("DATA SENT")
            print(bot_state)

        except Exception as e:

            print("BOT ERROR:", e)

        time.sleep(SOCKET_INTERVAL)

if __name__ == "__main__":

    threading.Thread(
        target=trading_loop,
        daemon=True
    ).start()

    PORT = int(os.environ.get("PORT", 5000))

    socketio.run(
        app,
        host="0.0.0.0",
        port=PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )
