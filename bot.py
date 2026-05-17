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

SYMBOL = os.getenv("SYMBOL", "DOGEUSDT")
INTERVAL = os.getenv("INTERVAL", "5m")

LEVERAGE = int(os.getenv("LEVERAGE", 10))
ORDER_USDT = float(os.getenv("ORDER_USDT", 1))

TP_ROI = float(os.getenv("TP_ROI", 0.02))
SL_ROI = float(os.getenv("SL_ROI", 0.01))
TRAIL_ROI = float(os.getenv("TRAIL_ROI", 0.8))

USD_IDR = int(os.getenv("USD_IDR", 17438))

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

try:

    client.get_server_time()

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

    "trade_count": 0,

    "win": 0,

    "loss": 0,

    "tp_price": 0,

    "sl_price": 0,

    "last_trade": 0,

    "last_position_state": False
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

    "atr_percent": 0,

    "distance_ema": 0,

    "trend": "NONE",

    "structure": "NONE",

    "position": "NONE",

    "entry": 0,

    "tp_price": 0,

    "sl_price": 0,

    "pnl": 0,

    "pnl_idr": 0,

    "balance": 0,

    "trade_count": 0,

    "winrate": 0,

    "trail": 0
    
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

    for col in df.columns[1:]:

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

        ema9 = EMAIndicator(
            close,
            9
        ).ema_indicator()

        ema21 = EMAIndicator(
            close,
            21
        ).ema_indicator()

        ema200 = EMAIndicator(
            close,
            200
        ).ema_indicator()

        rsi = RSIIndicator(
            close,
            14
        ).rsi()

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

        if bullish_trend:
            trend = "BULLISH"

        elif bearish_trend:
            trend = "BEARISH"

        else:
            trend = "SIDEWAYS"

        recent_high = high.iloc[-10:].max()
        recent_low = low.iloc[-10:].min()

        if current_price >= recent_high:
            structure = "BREAKOUT"

        elif current_price <= recent_low:
            structure = "BREAKDOWN"

        else:
            structure = "RANGE"

        pullback_long = (
            current_price <=
            ema9.iloc[-1] * 1.002
        )

        pullback_short = (
            current_price >=
            ema9.iloc[-1] * 0.998
        )

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

        sig = "NONE"

        if (

            bullish_trend
            and pullback_long
            and bullish_reject
            and good_volume
            and not_too_far
            and rsi.iloc[-1] > 50
            and atr_percent > 0.05

        ):

            sig = "LONG"

        elif (

            bearish_trend
            and pullback_short
            and bearish_reject
            and good_volume
            and not_too_far
            and rsi.iloc[-1] < 50
            and atr_percent > 0.05

        ):

            sig = "SHORT"

        return {

            "signal": sig,

            "price": current_price,

            "ema9": ema9.iloc[-1],

            "ema21": ema21.iloc[-1],

            "ema200": ema200.iloc[-1],

            "rsi": rsi.iloc[-1],

            "volume_ratio": volume_ratio,

            "atr_percent": atr_percent,

            "distance_ema": distance_ema,

            "trend": trend,

            "structure": structure
        }

    except Exception as e:

        console.print(
            f"[red]SIGNAL ERROR:[/red] {e}"
        )

        return {
            "signal": "NONE"
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

            amt = float(
                p["positionAmt"]
            )

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
# SETUP
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
# CANCEL OLD ORDERS
# =========================
def cancel_orders(symbol):

    try:

        client.futures_cancel_all_open_orders(
            symbol=symbol
        )

    except:
        pass

# =========================
# OPEN POSITION
# =========================
def open_position(symbol, side, qty):

    try:

        cancel_orders(symbol)

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

        socketio.sleep(1)

        entry_price = get_price(symbol)

        if side == "LONG":

            tp_price = (
                entry_price *
                (1 + TP_ROI)
            )

            sl_price = (
                entry_price *
                (1 - SL_ROI)
            )

            activation_price = (
                entry_price * 1.003
            )

            stop_side = SIDE_SELL

        else:

            tp_price = (
                entry_price *
                (1 - TP_ROI)
            )

            sl_price = (
                entry_price *
                (1 + SL_ROI)
            )

            activation_price = (
                entry_price * 0.997
            )

            stop_side = SIDE_BUY

        state["tp_price"] = tp_price
        state["sl_price"] = sl_price
        state["trail"] = TRAIL_ROI

        # TAKE PROFIT
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="TAKE_PROFIT_MARKET",

            stopPrice=round(tp_price, 6),

            closePosition=True,

            workingType="MARK_PRICE"
        )

        # STOP LOSS
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="STOP_MARKET",

            stopPrice=round(sl_price, 6),

            closePosition=True,

            workingType="MARK_PRICE"
        )

        # TRAILING STOP
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="TRAILING_STOP_MARKET",

            callbackRate=max(
                0.5,
                TRAIL_ROI
            ),

            activationPrice=round(
                activation_price,
                6
            ),

            quantity=qty,

            workingType="MARK_PRICE"
        )

        return order

    except Exception as e:

        console.print(
            f"[red]ENTRY ERROR:[/red] {e}"
        )

    return None

# =========================
# MONITOR POSITION
# =========================
def monitor_position():

    pos = get_position(SYMBOL)

    currently_open = pos is not None

    if (
        state["last_position_state"]
        and not currently_open
    ):

        pnl = web_data["pnl"]

        if pnl > 0:
            state["win"] += 1
        else:
            state["loss"] += 1

        console.print(
            f"[cyan]POSITION CLOSED | PNL: {pnl:.4f}[/cyan]"
        )

        cancel_orders(SYMBOL)

        state["side"] = None
        state["entry"] = 0
        state["qty"] = 0
        state["tp_price"] = 0
        state["sl_price"] = 0

    state["last_position_state"] = currently_open

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

        "atr_percent": data["atr_percent"],

        "distance_ema": data["distance_ema"],

        "trend": data["trend"],

        "structure": data["structure"],

        "position": (
            state["side"]
            or "NONE"
        ),

        "entry": state["entry"],

        "tp_price": state["tp_price"],

        "sl_price": state["sl_price"],

        "pnl": pnl,

        "pnl_idr": pnl * USD_IDR,

        "balance": usdt_balance,

        "trade_count": state["trade_count"],

        "winrate": round(winrate, 2),

        "trail": state["trail"]
    })

    socketio.emit(
        "update",
        web_data
    )

# =========================
# TERMINAL
# =========================
def terminal_dashboard(data):

    console.clear()

    table = Table(
        title="MARKET STRUCTURE BOT",
        box=box.DOUBLE_EDGE
    )

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row(
        "Signal",
        str(data["signal"])
    )

    table.add_row(
        "Trend",
        str(data["trend"])
    )

    table.add_row(
        "Structure",
        str(data["structure"])
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
        "Volume",
        f'{data["volume_ratio"]:.2f}'
    )

    table.add_row(
        "ATR %",
        f'{data["atr_percent"]:.4f}'
    )

    table.add_row(
        "Distance EMA",
        f'{data["distance_ema"]:.4f}'
    )

    table.add_row(
        "Position",
        str(state["side"])
    )

    table.add_row(
        "Win",
        str(state["win"])
    )

    table.add_row(
        "Loss",
        str(state["loss"])
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

            monitor_position()

            terminal_dashboard(data)

            pos = get_position(SYMBOL)

            if pos:

                socketio.sleep(5)

                continue

            # =========================
            # COOLDOWN 10 MENIT
            # =========================
            cooldown = 600

            if (
                time.time() -
                state["last_trade"]
            ) < cooldown:

                remaining = int(
                    cooldown -
                    (
                        time.time() -
                        state["last_trade"]
                    )
                )

                console.print(
                    f"[yellow]ENTRY COOLDOWN {remaining}s[/yellow]"
                )

                socketio.sleep(5)

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

                notional = (
                    qty *
                    data["price"]
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

                    state["trade_count"] += 1

                    state["last_trade"] = time.time()

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

        port=int(
            os.getenv(
                "PORT",
                8080
            )
        ),

        debug=False
)
