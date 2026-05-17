import eventlet
eventlet.monkey_patch()
import os
import time
import math
import requests
import numpy as np
import pandas as pd

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

from threading import Thread
from dotenv import load_dotenv

from binance.client import Client
from binance.enums import *

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.trend import ADXIndicator

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# =========================
# LOAD ENV
# =========================
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

SYMBOL = os.getenv("SYMBOL", "DOGEUSDT")
INTERVAL = os.getenv("INTERVAL", "3m")

LEVERAGE = int(os.getenv("LEVERAGE", 5))
ORDER_USDT = float(os.getenv("ORDER_USDT", 20))

TP_ROI = float(os.getenv("TP_ROI", 0.008))
SL_ROI = float(os.getenv("SL_ROI", 0.005))
TRAIL_ROI = float(os.getenv("TRAIL_ROI", 0.004))

USD_IDR = int(os.getenv("USD_IDR", 15800))

MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED")

# =========================
# CLIENT
# =========================
client = Client(API_KEY, API_SECRET)

console = Console()

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
    "adx": 0,
    "volume_ratio": 0,
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
# MARKET DATA
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

    df = get_klines(symbol)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    ema9 = EMAIndicator(close, 9).ema_indicator()
    ema21 = EMAIndicator(close, 21).ema_indicator()
    ema200 = EMAIndicator(close, 200).ema_indicator()

    rsi = RSIIndicator(close, 14).rsi()

    adx = ADXIndicator(
        high,
        low,
        close,
        14
    ).adx()

    avg_volume = volume.rolling(20).mean()

    volume_ratio = (
        volume.iloc[-1] /
        avg_volume.iloc[-1]
    )

    price = close.iloc[-1]

    long_signal = (
        ema9.iloc[-1] > ema21.iloc[-1]
        and ema21.iloc[-1] > ema200.iloc[-1]
        and rsi.iloc[-1] > 60
        and adx.iloc[-1] > 20
        and volume_ratio > 1.3
    )

    short_signal = (
        ema9.iloc[-1] < ema21.iloc[-1]
        and ema21.iloc[-1] < ema200.iloc[-1]
        and rsi.iloc[-1] < 40
        and adx.iloc[-1] > 20
        and volume_ratio > 1.3
    )

    sig = "NONE"

    if long_signal:
        sig = "LONG"

    elif short_signal:
        sig = "SHORT"

    return {
        "signal": sig,
        "price": price,
        "ema9": ema9.iloc[-1],
        "ema21": ema21.iloc[-1],
        "ema200": ema200.iloc[-1],
        "rsi": rsi.iloc[-1],
        "adx": adx.iloc[-1],
        "volume_ratio": volume_ratio
    }

# =========================
# POSITION
# =========================
def get_position(symbol):

    try:

        positions = client.futures_position_information(
            symbol=symbol
        )

        for p in positions:

            if float(p["positionAmt"]) != 0:
                return p

    except:
        pass

    return None

# =========================
# PNL
# =========================
def unrealized_pnl(symbol):

    pos = get_position(symbol)

    if not pos:
        return 0

    return float(pos["unRealizedProfit"])

# =========================
# LOT FILTER
# =========================
def get_lot_filters(symbol):

    info = client.futures_exchange_info()

    for s in info["symbols"]:

        if s["symbol"] == symbol:

            for f in s["filters"]:

                if f["filterType"] == "LOT_SIZE":

                    return (
                        float(f["stepSize"]),
                        float(f["minQty"])
                    )

    return 0.001, 0.001

# =========================
# SAFE QTY
# =========================
def safe_qty(qty, step, min_qty):

    precision = max(
        0,
        int(round(-math.log(step, 10), 0))
    )

    qty = round(qty, precision)

    if qty < min_qty:
        qty = min_qty

    return qty

# =========================
# SETUP SYMBOL
# =========================
def setup_symbol(symbol):

    try:
        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )
    except:
        pass

    try:
        client.futures_change_margin_type(
            symbol=symbol,
            marginType=MARGIN_TYPE
        )
    except:
        pass

# =========================
# ORDER
# =========================
def open_position(symbol, side, qty):

    try:

        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY if side == "LONG" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )

        return order

    except Exception as e:

        console.print(f"[red]{e}[/red]")

    return None

# =========================
# CLOSE
# =========================
def close_position(symbol, side, qty):

    try:

        client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL if side == "LONG" else SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=qty,
            reduceOnly=True
        )

    except Exception as e:

        console.print(f"[red]{e}[/red]")

# =========================
# TRAILING STOP
# =========================
def update_trailing(symbol):

    pos = get_position(symbol)

    if not pos:
        return

    amt = float(pos["positionAmt"])

    side = "LONG" if amt > 0 else "SHORT"

    price = get_price(symbol)

    if side == "LONG":

        if price > state["highest"]:
            state["highest"] = price

        trail = state["highest"] * (1 - TRAIL_ROI)

        state["trail"] = trail

        if price <= trail:

            close_position(
                symbol,
                side,
                abs(amt)
            )

    else:

        if price < state["lowest"]:
            state["lowest"] = price

        trail = state["lowest"] * (1 + TRAIL_ROI)

        state["trail"] = trail

        if price >= trail:

            close_position(
                symbol,
                side,
                abs(amt)
            )

# =========================
# DASHBOARD UPDATE
# =========================
def update_dashboard(data):

    pnl = unrealized_pnl(SYMBOL)

    try:

        balance_info = client.futures_account_balance()

        usdt_balance = 0

        for b in balance_info:

            if b["asset"] == "USDT":
                usdt_balance = float(b["balance"])
                break

    except:
        usdt_balance = 0

    winrate = 0

    if state["trade_count"] > 0:

        winrate = (
            state["win"] /
            state["trade_count"]
        ) * 100

    web_data.update({
        "signal": data["signal"],
        "price": data["price"],
        "ema9": data["ema9"],
        "ema21": data["ema21"],
        "ema200": data["ema200"],
        "rsi": data["rsi"],
        "adx": data["adx"],
        "volume_ratio": data["volume_ratio"],
        "position": state["side"] or "NONE",
        "entry": state["entry"],
        "trail": state["trail"],
        "pnl": pnl,
        "pnl_idr": pnl * USD_IDR,
        "balance": usdt_balance,
        "trade_count": state["trade_count"],
        "winrate": round(winrate, 2)
    })

    socketio.emit(
    "update",
    web_data,
    broadcast=True
)

# =========================
# TERMINAL UI
# =========================
def terminal_dashboard(data):

    console.clear()

    table = Table(
        title="SNIPER SCALPING BOT",
        box=box.DOUBLE_EDGE
    )

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Signal", str(data["signal"]))
    table.add_row("Price", f'{data["price"]:.4f}')
    table.add_row("RSI", f'{data["rsi"]:.2f}')
    table.add_row("ADX", f'{data["adx"]:.2f}')
    table.add_row("Volume Ratio", f'{data["volume_ratio"]:.2f}')
    table.add_row("Position", str(state["side"]))
    table.add_row("PNL", f'{web_data["pnl"]:.4f}')

    console.print(table)

# =========================
# MAIN LOOP
# =========================
def run_bot():

    setup_symbol(SYMBOL)

    while True:

        try:

            data = signal(SYMBOL)

            update_dashboard(data)

            terminal_dashboard(data)

            pos = get_position(SYMBOL)

            if pos:

                update_trailing(SYMBOL)

                socketio.sleep(2)
                continue

            if data["signal"] != "NONE":

                step, min_qty = get_lot_filters(SYMBOL)

                raw_qty = (
                    ORDER_USDT * LEVERAGE
                ) / data["price"]

                qty = safe_qty(
                    raw_qty,
                    step,
                    min_qty
                )

                order = open_position(
                    SYMBOL,
                    data["signal"],
                    qty
                )

                if order:

                    state["side"] = data["signal"]
                    state["entry"] = data["price"]
                    state["qty"] = qty
                    state["highest"] = data["price"]
                    state["lowest"] = data["price"]
                    state["trade_count"] += 1

            socketio.sleep(5)

        except Exception as e:

            console.print(f"[red]{e}[/red]")

            socketio.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":

    socketio.start_background_task(run_bot)

    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        debug=False
    )
