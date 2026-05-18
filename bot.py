import eventlet
eventlet.monkey_patch()

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import math
import time
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

INTERVAL = os.getenv("INTERVAL", "5m")

LEVERAGE = int(os.getenv("LEVERAGE", 10))
ORDER_USDT = float(os.getenv("ORDER_USDT", 1.2))

TP_ROI = float(os.getenv("TP_ROI", 0.02))
SL_ROI = float(os.getenv("SL_ROI", 0.01))
TRAIL_ROI = float(os.getenv("TRAIL_ROI", 0.8))

USD_IDR = int(os.getenv("USD_IDR", 17438))

MARGIN_TYPE = os.getenv(
    "MARGIN_TYPE",
    "ISOLATED"
)

# =========================
# COIN SCREENER
# =========================
SCAN_COINS = [

    "BEATUSDT",
    "HUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "BNBUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "LTCUSDT"

]

console = Console()

# =========================
# BINANCE CLIENT
# =========================
client = Client(
    API_KEY,
    API_SECRET
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

    "symbol": None,

    "side": None,

    "entry": 0,

    "qty": 0,

    "trade_count": 0,

    "win": 0,

    "loss": 0,

    "tp_price": 0,

    "sl_price": 0,

    "trail": 0,

    "last_trade": 0,

    "last_position_state": False
}

# =========================
# WEB DATA
# =========================
web_data = {

    "symbol": "-",

    "signal": "NONE",

    "price": 0,

    "rsi": 0,

    "volume_ratio": 0,

    "atr_percent": 0,

    "trend": "NONE",

    "structure": "NONE",

    "long_score": 0,

    "short_score": 0,

    "position": "NONE",

    "entry": 0,

    "tp_price": 0,

    "sl_price": 0,

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
# GET KLINES
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

    for col in df.columns[1:]:
        df[col] = df[col].astype(float)

    return df

# =========================
# SIGNAL ENGINE
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

        atr_percent = (
            atr.iloc[-1] /
            close.iloc[-1]
        ) * 100

        current_price = close.iloc[-1]

        bullish_trend = (
            ema21.iloc[-1] >
            ema200.iloc[-1]
        )

        bearish_trend = (
            ema21.iloc[-1] <
            ema200.iloc[-1]
        )

        trend = "SIDEWAYS"

        if bullish_trend:
            trend = "BULLISH"

        elif bearish_trend:
            trend = "BEARISH"

        recent_high = high.iloc[-10:].max()
        recent_low = low.iloc[-10:].min()

        structure = "RANGE"

        if current_price >= recent_high:
            structure = "BREAKOUT"

        elif current_price <= recent_low:
            structure = "BREAKDOWN"

        bullish_reject = (
            close.iloc[-1] >
            openp.iloc[-1]
        )

        bearish_reject = (
            close.iloc[-1] <
            openp.iloc[-1]
        )

        distance_ema = abs(
            current_price -
            ema9.iloc[-1]
        ) / current_price

        not_too_far = (
            distance_ema <= 0.003
        )

        good_volume = (
            volume_ratio > 1.1
        )

        long_score = 0
        short_score = 0

        if bullish_trend:
            long_score += 25

        if bearish_trend:
            short_score += 25

        if rsi.iloc[-1] > 50:
            long_score += 25

        if rsi.iloc[-1] < 50:
            short_score += 25

        if good_volume:
            long_score += 25
            short_score += 25

        if bullish_reject:
            long_score += 25

        if bearish_reject:
            short_score += 25

        sig = "NONE"

        if (
            long_score >= 75
            and not_too_far
            and atr_percent > 0.05
        ):
            sig = "LONG"

        elif (
            short_score >= 75
            and not_too_far
            and atr_percent > 0.05
        ):
            sig = "SHORT"

        return {

            "symbol": symbol,

            "signal": sig,

            "price": current_price,

            "rsi": rsi.iloc[-1],

            "volume_ratio": volume_ratio,

            "atr_percent": atr_percent,

            "trend": trend,

            "structure": structure,

            "long_score": long_score,

            "short_score": short_score
        }

    except Exception as e:

        console.print(
            f"[red]SIGNAL ERROR {symbol}:[/red] {e}"
        )

        return None

# =========================
# SCREENER
# =========================
def scan_market():

    best_coin = None
    best_score = 0

    console.print(
        "[cyan]SCANNING MARKET...[/cyan]"
    )

    for coin in SCAN_COINS:

        data = signal(coin)

        if not data:
            continue

        score = max(
            data["long_score"],
            data["short_score"]
        )

        console.print(
            f"{coin} | "
            f"{data['signal']} | "
            f"SCORE {score}"
        )

        if (
            data["signal"] != "NONE"
            and score > best_score
        ):

            best_score = score
            best_coin = data

    return best_coin

# =========================
# GET POSITION
# =========================
def get_position(symbol):

    try:

        positions = client.futures_position_information(
            symbol=symbol
        )

        for p in positions:

            amt = float(
                p["positionAmt"]
            )

            if abs(amt) > 0.000001:
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

    precision = max(
        0,
        int(round(-math.log(step, 10), 0))
    )

    qty = round(qty, precision)

    qty = math.floor(qty / step) * step

    if qty < min_qty:
        qty = min_qty

    return float(f"{qty:.8f}")

# =========================
# OPEN POSITION
# =========================
def open_position(symbol, side, qty):

    try:

        order = client.futures_create_order(

            symbol=symbol,

            side=(
                SIDE_BUY
                if side == "LONG"
                else SIDE_SELL
            ),

            type=ORDER_TYPE_MARKET,

            quantity=qty
        )

        price = float(
            client.futures_mark_price(
                symbol=symbol
            )["markPrice"]
        )

        if side == "LONG":

            tp_price = (
                price * (1 + TP_ROI)
            )

            sl_price = (
                price * (1 - SL_ROI)
            )

            stop_side = SIDE_SELL

        else:

            tp_price = (
                price * (1 - TP_ROI)
            )

            sl_price = (
                price * (1 + SL_ROI)
            )

            stop_side = SIDE_BUY

        state["tp_price"] = tp_price
        state["sl_price"] = sl_price
        state["trail"] = TRAIL_ROI

        # TP
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="TAKE_PROFIT_MARKET",

            stopPrice=round(tp_price, 6),

            closePosition=True
        )

        # SL
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="STOP_MARKET",

            stopPrice=round(sl_price, 6),

            closePosition=True
        )

        console.print(
            f"[green]ENTRY {side} {symbol} SUCCESS[/green]"
        )

        return order

    except Exception as e:

        console.print(
            f"[red]ENTRY ERROR:[/red] {e}"
        )

    return None

# =========================
# UPDATE DASHBOARD
# =========================
def update_dashboard(data):

    pnl = 0

    if state["symbol"]:
        pnl = unrealized_pnl(
            state["symbol"]
        )

    try:

        balance_info = client.futures_account_balance()

        usdt_balance = 0

        for b in balance_info:

            if b["asset"] == "USDT":

                usdt_balance = float(
                    b["balance"]
                )

    except:

        usdt_balance = 0

    winrate = 0

    if state["trade_count"] > 0:

        winrate = (
            state["win"] /
            state["trade_count"]
        ) * 100

    web_data.update({

        "symbol": data["symbol"],

        "signal": data["signal"],

        "price": data["price"],

        "rsi": data["rsi"],

        "volume_ratio": data["volume_ratio"],

        "atr_percent": data["atr_percent"],

        "trend": data["trend"],

        "structure": data["structure"],

        "long_score": data["long_score"],

        "short_score": data["short_score"],

        "position": (
            state["side"]
            or "NONE"
        ),

        "entry": state["entry"],

        "tp_price": state["tp_price"],

        "sl_price": state["sl_price"],

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
# MAIN LOOP
# =========================
def run_bot():

    while True:

        try:

            current_position = None

            if state["symbol"]:

                current_position = get_position(
                    state["symbol"]
                )

            if current_position:

                console.print(
                    "[yellow]POSITION STILL OPEN[/yellow]"
                )

                socketio.sleep(5)
                continue

            best = scan_market()

            if not best:

                console.print(
                    "[yellow]NO SIGNAL FOUND[/yellow]"
                )

                socketio.sleep(10)
                continue

            update_dashboard(best)

            symbol = best["symbol"]

            step, min_qty = get_lot_filters(
                symbol
            )

            qty = (
                ORDER_USDT *
                LEVERAGE
            ) / best["price"]

            qty = safe_qty(
                qty,
                step,
                min_qty
            )

            order = open_position(

                symbol,

                best["signal"],

                qty
            )

            if order:

                state["symbol"] = symbol

                state["side"] = best["signal"]

                state["entry"] = best["price"]

                state["qty"] = qty

                state["trade_count"] += 1

            socketio.sleep(15)

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

        port=8080,

        debug=False
        )
