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

LEVERAGE = int(os.getenv("LEVERAGE", 10))
ORDER_USDT = float(os.getenv("ORDER_USDT", 5))

TP_ROI = float(os.getenv("TP_ROI", 0.004))
SL_ROI = float(os.getenv("SL_ROI", 0.003))
TRAIL_ROI = float(os.getenv("TRAIL_ROI", 0.002))

USD_IDR = int(os.getenv("USD_IDR", 15800))

MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED")

# =========================
# BINANCE CLIENT
# =========================
client = Client(
    API_KEY,
    API_SECRET,
    requests_params={
        "timeout": 20
    }
)

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

        # =========================
        # LONG SCORE
        # =========================
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

        # =========================
        # SHORT SCORE
        # =========================
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

        # =========================
        # SIGNAL
        # =========================
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

        console.print(
            f"""
[cyan]SIGNAL[/cyan]
LONG SCORE  : {long_score}
SHORT SCORE : {short_score}
RSI         : {rsi.iloc[-1]:.2f}
ATR %       : {atr_percent:.4f}
VOL RATIO   : {volume_ratio:.2f}
SIGNAL      : {sig}
"""
        )

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
            "short_score": 0
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

            amt = float(p["positionAmt"])

            if abs(amt) > 0.000001:
                return p

    except Exception as e:

        console.print(
            f"[red]POSITION ERROR:[/red] {e}"
        )

    return None

# =========================
# PNL
# =========================
def unrealized_pnl(symbol):

    pos = get_position(symbol)

    if not pos:
        return 0

    return float(
        pos["unRealizedProfit"]
    )

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

    qty = math.floor(qty / step) * step

    if qty < min_qty:
        qty = min_qty

    return float(f"{qty:.8f}")

# =========================
# SETUP
# =========================
def setup_symbol(symbol):

    try:

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

        console.print(
            f"[green]LEVERAGE SET:[/green] {LEVERAGE}x"
        )

    except Exception as e:

        console.print(
            f"[red]LEVERAGE ERROR:[/red] {e}"
        )

    try:

        client.futures_change_margin_type(
            symbol=symbol,
            marginType=MARGIN_TYPE
        )

        console.print(
            f"[green]MARGIN:[/green] {MARGIN_TYPE}"
        )

    except Exception as e:

        console.print(
            f"[yellow]MARGIN WARNING:[/yellow] {e}"
        )

# =========================
# OPEN POSITION
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

        console.print(
            f"[red]ENTRY ERROR:[/red] {e}"
        )

    return None

# =========================
# CLOSE POSITION
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

        console.print(
            "[green]POSITION CLOSED[/green]"
        )

        # RESET STATE
        state["side"] = None
        state["entry"] = 0
        state["qty"] = 0
        state["highest"] = 0
        state["lowest"] = 999999
        state["trail"] = 0

    except Exception as e:

        console.print(
            f"[red]CLOSE ERROR:[/red] {e}"
        )

# =========================
# TRAILING STOP
# =========================
def update_trailing(symbol):

    pos = get_position(symbol)

    if not pos:
        return

    amt = float(pos["positionAmt"])

    side = (
        "LONG"
        if amt > 0
        else "SHORT"
    )

    price = get_price(symbol)

    # =========================
    # LONG
    # =========================
    if side == "LONG":

        if price > state["highest"]:
            state["highest"] = price

        trail = (
            state["highest"] *
            (1 - TRAIL_ROI)
        )

        state["trail"] = trail

        if price <= trail:

            console.print(
                "[red]TRAIL HIT LONG[/red]"
            )

            close_position(
                symbol,
                side,
                abs(amt)
            )

    # =========================
    # SHORT
    # =========================
    else:

        if price < state["lowest"]:
            state["lowest"] = price

        trail = (
            state["lowest"] *
            (1 + TRAIL_ROI)
        )

        state["trail"] = trail

        if price >= trail:

            console.print(
                "[red]TRAIL HIT SHORT[/red]"
            )

            close_position(
                symbol,
                side,
                abs(amt)
            )

# =========================
# UPDATE DASHBOARD
# =========================
def update_dashboard(data):

    pnl = unrealized_pnl(SYMBOL)

    try:

        balance_info = client.futures_account_balance()

        usdt_balance = 0

        for b in balance_info:

            if b["asset"] == "USDT":

                usdt_balance = float(
                    b["balance"]
                )

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

        "volume_ratio": data["volume_ratio"],

        "candle_strength": data["candle_strength"],

        "atr_percent": data["atr_percent"],

        "long_score": data["long_score"],
        "short_score": data["short_score"],

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
        web_data
    )

# =========================
# DASHBOARD TERMINAL
# =========================
def terminal_dashboard(data):

    console.clear()

    table = Table(
        title="ADAPTIVE SNIPER BOT",
        box=box.DOUBLE_EDGE
    )

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row(
        "Signal",
        str(data["signal"])
    )

    table.add_row(
        "Price",
        f'{data["price"]:.4f}'
    )

    table.add_row(
        "RSI",
        f'{data["rsi"]:.2f}'
    )

    table.add_row(
        "ATR %",
        f'{data["atr_percent"]:.4f}'
    )

    table.add_row(
        "LONG Score",
        str(data["long_score"])
    )

    table.add_row(
        "SHORT Score",
        str(data["short_score"])
    )

    table.add_row(
        "Position",
        str(state["side"])
    )

    table.add_row(
        "PNL",
        f'{web_data["pnl"]:.4f}'
    )

    console.print(table)

# =========================
# MAIN LOOP
# =========================
def run_bot():

    setup_symbol(SYMBOL)

    while True:

        try:

            if not API_KEY or not API_SECRET:

                console.print(
                    "[red]API KEY MISSING[/red]"
                )

                socketio.sleep(10)

                continue

            data = signal(SYMBOL)

            update_dashboard(data)

            terminal_dashboard(data)

            pos = get_position(SYMBOL)

            # =========================
            # POSITION ACTIVE
            # =========================
            if pos:

                update_trailing(SYMBOL)

                socketio.sleep(2)

                continue

            # =========================
            # ENTRY
            # =========================
            if data["signal"] != "NONE":

                step, min_qty = get_lot_filters(
                    SYMBOL
                )

                raw_qty = (
                    ORDER_USDT *
                    LEVERAGE
                ) / data["price"]

                qty = safe_qty(
                    raw_qty,
                    step,
                    min_qty
                )

                notional = qty * data["price"]

                console.print(
                    f"""
[green]TRY ENTRY[/green]
SIDE      : {data["signal"]}
QTY       : {qty}
PRICE     : {data["price"]}
NOTIONAL  : {notional}
"""
                )

                if notional < 5:

                    console.print(
                        "[red]NOTIONAL TOO SMALL[/red]"
                    )

                    socketio.sleep(5)

                    continue

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

                    console.print(
                        f"[bold green]ENTRY {data['signal']} SUCCESS[/bold green]"
                    )

            socketio.sleep(5)

        except Exception as e:

            console.print(
                f"[red]MAIN LOOP ERROR:[/red] {e}"
            )

            socketio.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":

    socketio.start_background_task(
        run_bot
    )

    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        debug=False
    )
