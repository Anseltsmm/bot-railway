# =========================
# app.py
# =========================

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify

from extensions import socketio
from bot import run_bot, web_data

# =========================
# CREATE FLASK APP
# =========================
app = Flask(__name__)

# =========================
# INIT SOCKETIO
# =========================
socketio.init_app(
    app,
    cors_allowed_origins="*"
)

# =========================
# ROUTES
# =========================
@app.route("/")
def home():

    return render_template(
        "dashboard.html"
    )

@app.route("/api/data")
def api_data():

    return jsonify(
        web_data
    )

# =========================
# HEALTH CHECK
# =========================
@app.route("/health")
def health():

    return {

        "status": "running",

        "bot": "active"
    }

# =========================
# REALTIME SOCKET EMITTER
# =========================
def socket_sender():

    while True:

        try:

            socketio.emit(
                "update",
                web_data
            )

            socketio.sleep(2)

        except Exception as e:

            print(
                f"SOCKET ERROR: {e}"
            )

            socketio.sleep(2)

# =========================
# START SERVER
# =========================
if __name__ == "__main__":

    print(
        "===================================="
    )

    print(
        " BINANCE AI SCREENER STARTED "
    )

    print(
        "===================================="
    )

    # =========================
    # START SOCKET EMITTER
    # =========================
    socketio.start_background_task(
        socket_sender
    )

    # =========================
    # START BOT ENGINE
    # =========================
    socketio.start_background_task(
        run_bot
    )

    # =========================
    # RUN FLASK
    # =========================
    socketio.run(

        app,

        host="0.0.0.0",

        port=8080,

        debug=False
    )
