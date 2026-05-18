from flask import Flask, render_template
from flask_socketio import SocketIO
import pandas as pd
import eventlet
import os

eventlet.monkey_patch()

from trader import *
from strategy import analyze
from state import bot_state
from config import *

app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
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

            df = get_klines()

            result = analyze(df)

            price = get_price(SYMBOL)

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
            # EMIT SOCKET
            # =========================

            socketio.emit(
                "update",
                bot_state
            )

            print("DATA SENT")
            print(bot_state)

        except Exception as e:

            print("BOT ERROR:", e)

        socketio.sleep(SOCKET_INTERVAL)

if __name__ == "__main__":

    socketio.start_background_task(trading_loop)

    PORT = int(os.environ.get("PORT", 5000))

    socketio.run(
        app,
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
