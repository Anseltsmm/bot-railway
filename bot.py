import eventlet
eventlet.monkey_patch()

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import math
import pandas as pd

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

from dotenv import load_dotenv

from binance.client import Client
from binance.enums import *

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

from rich.console import Console
from rich.table import Table
from rich import box

# =========================
# LOAD ENV
# =========================
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

SYMBOL = os.getenv("SYMBOL", "DOGEUSDT")
INTERVAL = os.getenv("INTERVAL", "1m")

LEVERAGE = int(os.getenv("LEVERAGE", 5))
ORDER_USDT = float(os.getenv("ORDER_USDT", 1))

TP_ROI = float(os.getenv("TP_ROI", 0.05))
SL_ROI = float(os.getenv("SL_ROI", 0.03))
TRAIL_ROI = float(os.getenv("TRAIL_ROI", 0.02))

USD_IDR = int(os.getenv("USD_IDR", 15800))

MARGIN_TYPE = os.getenv(
    "MARGIN_TYPE",
    "ISOLATED"
)

# =========================
# PROXY
# =========================
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

# =========================
# PROXY URL
# =========================
proxy_url = None

if PROXY_HOST and PROXY_PORT:

    if PROXY_USER and PROXY_PASS:

        proxy_url = (
            f"http://{PROXY_USER}:{PROXY_PASS}"
            f"@{PROXY_HOST}:{PROXY_PORT}"
        )

    else:

        proxy_url = (
            f"http://{PROXY_HOST}:{PROXY_PORT}"
        )

console = Console()

# =========================
# BINANCE CLIENT
# =========================
client = Client(

    API_KEY,
    API_SECRET,

    requests_params={

        "timeout": 20,

        "proxies": {

            "http": proxy_url,
            "https": proxy_url

        } if proxy_url else None
    }
)

# =========================
# DEBUG
# =========================
if proxy_url:

    console.print(
        f"[green]PROXY ENABLED[/green] {proxy_url}"
    )

else:

    console.print(
        "[yellow]NO PROXY ENABLED[/yellow]"
    )

# =========================
# TEST BINANCE CONNECTION
# =========================
try:

    server_time = client.get_server_time()

    console.print(
        "[green]BINANCE CONNECTED[/green]"
    )

except Exception as e:

    console.print(
        f"[red]BINANCE ERROR:[/red] {e}"
    )

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
# STATE
# =========================
state = {
    "side": None,
    "entry": 0,
    "qty": 0,
    "highest": 0,
    "lowest": 999999,
    "trail": 0,
    "trade_count": 0,
    "win": 0,
    "loss": 0
}

# =========================
# WEB DATA
# =========================
web_data = {
    "status": "RUNNING",
    "symbol": SYMBOL,
    "signal": "NONE",
    "price": 0,
    "ema9": 0,
    "ema21": 0,
    "ema200": 0,
    "rsi": 0,
    "volume_ratio": 0,
    "candle_strength": 0,
    "atr_percent": 0,
    "long_score": 0,
    "short_score": 0,
    "position": "NONE",
    "entry": 0,
    "trail": 0,
    "pnl": 0,
    "pnl_idr": 0,
    "balance": 0,
    "trade_count": 0,
    "winrate": 0
}

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
# PRICE
# =========================
def get_price(symbol):

    return float(
        client.futures_mark_price(
            symbol=symbol
        )["markPrice"]
    )

# =========================
# KLINES
# =========================
def get_klines(symbol):

    df = pd.DataFrame(
        client.futures_klines(
            symbol=symbol,
            interval=INTERVAL,
            limit=300
        )
    )

    df = df.iloc[:, :6]

    df.columns = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for col in [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]:
        df[col] = df[col].astype(float)

    return df

# =========================
# SIGNAL
# =========================
def signal(symbol):

    try:

        df = get_klines(symbol)

        close = df["close"]
        high = df["high"]
        low = df["low"]
        openp = df["open"]
        volume = df["volume"]

        ema9 = EMAIndicator(close, 9).ema_indicator()
        ema21 = EMAIndicator(close, 21).ema_indicator()
        ema200 = EMAIndicator(close, 200).ema_indicator()

        rsi = RSIIndicator(close, 14).rsi()

        atr = AverageTrueRange(
            high,
            low,
            close,
            14
        ).average_true_range()

        avg_volume = volume.rolling(20).mean()

        volume_ratio = (
            volume.iloc[-1] /
            avg_volume.iloc[-1]
        )

        candle_body = abs(
            close.iloc[-1] -
            openp.iloc[-1]
        )

        candle_range = (
            high.iloc[-1] -
            low.iloc[-1]
        )

        candle_strength = 0

        if candle_range > 0:
            candle_strength = (
                candle_body /
                candle_range
            )

        atr_percent = (
            atr.iloc[-1] /
            close.iloc[-1]
        ) * 100

        long_score = 0

        if ema9.iloc[-1] > ema21.iloc[-1]:
            long_score += 25

        if ema21.iloc[-1] > ema200.iloc[-1]:
            long_score += 20

        if rsi.iloc[-1] > 52:
            long_score += 20

        if volume_ratio > 1.05:
            long_score += 20

        if candle_strength > 0.4:
            long_score += 15

        short_score = 0

        if ema9.iloc[-1] < ema21.iloc[-1]:
            short_score += 25

        if ema21.iloc[-1] < ema200.iloc[-1]:
            short_score += 20

        if rsi.iloc[-1] < 48:
            short_score += 20

        if volume_ratio > 1.05:
            short_score += 20

        if candle_strength > 0.4:
            short_score += 15

        sig = "NONE"

        if (
            long_score >= 60
            and atr_percent > 0.03
        ):
            sig = "LONG"

        elif (
            short_score >= 60
            and atr_percent > 0.03
        ):
            sig = "SHORT"

        return {
            "signal": sig,
            "price": close.iloc[-1],
            "ema9": ema9.iloc[-1],
            "ema21": ema21.iloc[-1],
            "ema200": ema200.iloc[-1],
            "rsi": rsi.iloc[-1],
            "volume_ratio": volume_ratio,
            "candle_strength": candle_strength,
            "atr_percent": atr_percent,
            "long_score": long_score,
            "short_score": short_score
        }

    except Exception as e:

        console.print(
            f"[red]SIGNAL ERROR:[/red] {e}"
        )

        return {
            "signal": "NONE"
        }

# lanjutkan function lain seperti sebelumnya:
# - get_position
# - safe_qty
# - open_position
# - close_position
# - update_trailing
# - update_dashboard
# - terminal_dashboard
# - run_bot
# - socketio.run
