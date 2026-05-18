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

socketio.init_app(
    app,
    cors_allowed_origins="*"
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
# START
# =========================
if __name__ == "__main__":

    socketio.start_background_task(
        start_bot
    )

    socketio.run(

        app,

        host="0.0.0.0",

        port=8080,

        debug=False
    )
