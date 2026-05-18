# =========================
# app.py
# =========================

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify
from extensions import socketio

from bot import start_bot, web_data

# =========================
# FLASK
# =========================
app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/api/data")
def api_data():
    return jsonify(web_data)

# =========================
# SOCKET EMITTER
# =========================
def socket_sender():

    while True:

        socketio.emit(
            "update",
            web_data
        )

        socketio.sleep(2)

# =========================
# START
# =========================
if __name__ == "__main__":

    socketio.start_background_task(
        socket_sender
    )

    socketio.start_background_task(
        start_bot
    )

    socketio.run(
        app,
        host="0.0.0.0",
        port=8080,
        debug=False
    )
