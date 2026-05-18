import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template

from extensions import socketio

from bot import run_bot

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('dashboard.html')


if __name__ == '__main__':

    socketio.init_app(app)

    socketio.start_background_task(run_bot)

    socketio.run(
        app,
        host='0.0.0.0',
        port=5000
    )
