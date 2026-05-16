import os
import time
import math
import requests

from flask import Flask
from threading import Thread

from dotenv import load_dotenv

from binance.client import Client
from binance.enums import *

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

import pandas as pd

# =========================
# LOAD ENV
# =========================
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

LEVERAGE = int(os.getenv("LEVERAGE", 10))
ORDER_USDT = float(os.getenv("ORDER_USDT", 20))

TP_ROI = float(os.getenv("TP_ROI", 0.05))
SL_ROI = float(os.getenv("SL_ROI", 0.03))
TRAIL_ROI = float(os.getenv("TRAIL_ROI", 0.02))

MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED")

USD_IDR = int(os.getenv("USD_IDR", 15800))

PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

# =========================
# PROXY
# =========================
proxy_url = None

if (
    PROXY_HOST
    and PROXY_PORT
    and PROXY_USER
    and PROXY_PASS
):

    proxy_url = (
        f"socks5://{PROXY_USER}:{PROXY_PASS}"
        f"@{PROXY_HOST}:{PROXY_PORT}"
    )

# =========================
# BINANCE CLIENT
# =========================
if proxy_url:

    client = Client(
        API_KEY,
        API_SECRET,
        requests_params={
            "proxies": {
                "http": proxy_url,
                "https": proxy_url
            },
            "timeout": 20
        }
    )

else:

    client = Client(
        API_KEY,
        API_SECRET
    )

console = Console()

# =========================
# FLASK
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "BOT RUNNING"

def run_web():
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )

# =========================
# CONFIG
# =========================
INTERVAL = "5m"

SYMBOL = os.getenv(
    "SYMBOL",
    "DOGEUSDT"
)

TRADE_COOLDOWN = 300

# =========================
# STATE
# =========================
state = {
    "in_position": False,
    "side": None,
    "entry": 0,
    "qty": 0,
    "highest_price": 0,
    "lowest_price": 999999999,
    "trail_price": 0
}

last_trade_time = 0

# =========================
# MARKET
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
            limit=200
        ),
        columns=[
            "t","o","h","l","c","v",
            "ct","qav","n","tb","tq","ig"
        ]
    )

    for col in ["o","h","l","c","v"]:
        df[col] = df[col].astype(float)

    return df

# =========================
# SIGNAL
# =========================
def signal(symbol):

    df = get_klines(symbol)

    close = df["c"]

    ema50 = close.ewm(
        span=50
    ).mean()

    ema200 = close.ewm(
        span=200
    ).mean()

    last_close = close.iloc[-1]
    prev_close = close.iloc[-2]

    signal = "NONE"

    # ================= LONG
    if (
        ema50.iloc[-1] > ema200.iloc[-1]
        and prev_close < ema50.iloc[-2]
        and last_close > ema50.iloc[-1]
    ):

        signal = "LONG"

    # ================= SHORT
    elif (
        ema50.iloc[-1] < ema200.iloc[-1]
        and prev_close > ema50.iloc[-2]
        and last_close < ema50.iloc[-1]
    ):

        signal = "SHORT"

    return {
        "signal": signal,
        "price": last_close,
        "ema50": ema50.iloc[-1],
        "ema200": ema200.iloc[-1]
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

    return float(
        pos["unRealizedProfit"]
    )

# =========================
# PRECISION
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
# ORDER
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

def open_position(symbol, side, qty):

    try:

        return client.futures_create_order(
            symbol=symbol,
            side=(
                SIDE_BUY
                if side == "LONG"
                else SIDE_SELL
            ),
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )

    except Exception as e:

        console.print(
            f"[red]ENTRY ERROR:[/red] {e}"
        )

    return None

def close_position(symbol, side, qty):

    try:

        client.futures_create_order(
            symbol=symbol,
            side=(
                SIDE_SELL
                if side == "LONG"
                else SIDE_BUY
            ),
            type=ORDER_TYPE_MARKET,
            quantity=qty,
            reduceOnly=True
        )

    except Exception as e:

        console.print(
            f"[red]CLOSE ERROR:[/red] {e}"
        )

# =========================
# TRAILING STOP
# =========================
def update_trailing_stop(symbol):

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

    # ================= LONG
    if side == "LONG":

        if state["highest_price"] == 0:
            state["highest_price"] = price

        if price > state["highest_price"]:
            state["highest_price"] = price

        trailing_sl = (
            state["highest_price"] *
            (1 - TRAIL_ROI)
        )

        state["trail_price"] = trailing_sl

        if price <= trailing_sl:

            console.print(
                "[bold red]TRAIL STOP LONG[/bold red]"
            )

            close_position(
                symbol,
                side,
                abs(amt)
            )

    # ================= SHORT
    else:

        if state["lowest_price"] == 999999999:
            state["lowest_price"] = price

        if price < state["lowest_price"]:
            state["lowest_price"] = price

        trailing_sl = (
            state["lowest_price"] *
            (1 + TRAIL_ROI)
        )

        state["trail_price"] = trailing_sl

        if price >= trailing_sl:

            console.print(
                "[bold red]TRAIL STOP SHORT[/bold red]"
            )

            close_position(
                symbol,
                side,
                abs(amt)
            )

# =========================
# DASHBOARD
# =========================
def dashboard(symbol, data):

    console.clear()

    pnl = unrealized_pnl(symbol)

    pnl_color = (
        "green"
        if pnl >= 0
        else "red"
    )

    header = Text()

    header.append(
        " RAILWAY FUTURES BOT ",
        style="bold white on blue"
    )

    header.append(
        f"\nPAIR : {symbol}",
        style="bold cyan"
    )

    market = Table(
        box=box.ROUNDED,
        style="white"
    )

    market.add_column(
        "Metric",
        style="bold cyan"
    )

    market.add_column(
        "Value",
        style="bold white"
    )

    signal_color = (
        "green"
        if data["signal"] == "LONG"
        else "red"
        if data["signal"] == "SHORT"
        else "yellow"
    )

    market.add_row(
        "Signal",
        f"[{signal_color}]{data['signal']}[/{signal_color}]"
    )

    market.add_row(
        "Price",
        f"[yellow]{data['price']:.4f}[/yellow]"
    )

    market.add_row(
        "EMA 50",
        f"[cyan]{data['ema50']:.4f}[/cyan]"
    )

    market.add_row(
        "EMA 200",
        f"[magenta]{data['ema200']:.4f}[/magenta]"
    )

    market.add_row(
        "Position",
        f"[green]{state['side']}[/green]"
        if state["side"]
        else "-"
    )

    market.add_row(
        "Entry",
        f"[white]{state['entry']:.4f}[/white]"
    )

    market.add_row(
        "Trailing SL",
        f"[red]{state['trail_price']:.4f}[/red]"
    )

    market.add_row(
        "Highest",
        f"[green]{state['highest_price']:.4f}[/green]"
    )

    market.add_row(
        "Lowest",
        f"[red]{state['lowest_price']:.4f}[/red]"
    )

    market.add_row(
        "PNL USDT",
        f"[{pnl_color}]{pnl:.4f}[/{pnl_color}]"
    )

    market.add_row(
        "PNL IDR",
        f"[{pnl_color}]Rp {pnl * USD_IDR:,.0f}[/{pnl_color}]"
    )

    console.print(
        Panel(
            header,
            border_style="blue"
        )
    )

    console.print(
        Panel(
            market,
            title="📊 MARKET ANALYSIS",
            border_style="cyan",
            box=box.DOUBLE
        )
    )

# =========================
# MAIN LOOP
# =========================
def run_bot():

    global last_trade_time

    setup_symbol(SYMBOL)

    while True:

        try:

            data = signal(SYMBOL)

            dashboard(
                SYMBOL,
                data
            )

            # =========================
            # POSITION CHECK
            # =========================
            pos = get_position(SYMBOL)

            if pos:

                state["in_position"] = True

                update_trailing_stop(
                    SYMBOL
                )

                time.sleep(3)
                continue

            else:

                state["in_position"] = False

                state["side"] = None

                state["entry"] = 0

                state["qty"] = 0

                state["highest_price"] = 0

                state["lowest_price"] = 999999999

                state["trail_price"] = 0

            # =========================
            # ENTRY
            # =========================
            if (
                data["signal"] != "NONE"
                and (
                    time.time() -
                    last_trade_time
                ) > TRADE_COOLDOWN
            ):

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

                order = open_position(
                    SYMBOL,
                    data["signal"],
                    qty
                )

                if order:

                    state["in_position"] = True

                    state["side"] = data["signal"]

                    state["entry"] = data["price"]

                    state["qty"] = qty

                    state["highest_price"] = data["price"]

                    state["lowest_price"] = data["price"]

                    last_trade_time = time.time()

                    console.print(
                        f"[bold green]ENTRY {data['signal']} SUCCESS[/bold green]"
                    )

            time.sleep(5)

        except Exception as e:

            console.print(
                f"[red]{e}[/red]"
            )

            time.sleep(5)

# =========================
# START
# =========================
if __name__ == "__main__":

    Thread(
        target=run_web
    ).start()

    run_bot()
