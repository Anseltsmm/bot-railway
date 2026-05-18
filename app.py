from flask import Flask, render_template
from flask_socketio import SocketIO

import threading
import time
import os

from core.trader import *
from strategy.analyzer import analyze_multi_tf
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

def trading_loop():

    while True:

        try:

            # =========================
            # ANALYZE
            # =========================

            result = analyze_multi_tf()

            # =========================
            # MARKET
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
            # ENTRY
            # =========================
            now = time.time()

cooldown_passed = (
    now -
    bot_state["last_trade_time"]
) > TRADE_COOLDOWN

            if (
    result["signal"] == "LONG"
    and
    not has_open_position(SYMBOL)
    and
    cooldown_passed
):

    place_long()

    bot_state["last_trade_time"] = now

elif (
    result["signal"] == "SHORT"
    and
    not has_open_position(SYMBOL)
    and
    cooldown_passed
):

    place_short()

    bot_state["last_trade_time"] = now
            # =========================
            # SOCKET
            # =========================

            socketio.emit(
                "update",
                bot_state
            )

            print(
                f"{SYMBOL} | "
                f"{bot_state['signal']} | "
                f"{bot_state['position']} | "
                f"PNL: {bot_state['pnl']}"
            )

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
