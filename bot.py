# bot.py

import eventlet
eventlet.monkey_patch()

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import math
import pandas as pd

from dotenv import load_dotenv

from binance.client import Client
from binance.enums import *

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

from rich.console import Console
from rich.table import Table
from rich import box

from extensions import socketio

# =========================
# LOAD ENV
# =========================
load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

INTERVAL = os.getenv("INTERVAL", "1m")

LEVERAGE = int(
    os.getenv("LEVERAGE", 10)
)

ORDER_USDT = float(
    os.getenv("ORDER_USDT", 1.0)
)

TP_ROI = float(
    os.getenv("TP_ROI", 0.02)
)

SL_ROI = float(
    os.getenv("SL_ROI", 0.01)
)

TRAIL_ROI = float(
    os.getenv("TRAIL_ROI", 0.2)
)

USD_IDR = int(
    os.getenv("USD_IDR", 17438)
)

MARGIN_TYPE = os.getenv(
    "MARGIN_TYPE",
    "ISOLATED"
).upper()

# =========================
# MULTI TF
# =========================
TIMEFRAMES = [
    "1m",
    "5m",
    "15m",
    "1h",
    "2h",
    "4h",
    "1d",
    "1w"
]

# =========================
# COINS
# =========================
SCAN_COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "NEARUSDT",
    "TRXUSDT"
]

console = Console()

# =========================
# BINANCE
# =========================
client = Client(
    API_KEY,
    API_SECRET
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
    "trail": 0
}

# =========================
# WEB DATA
# =========================
web_data = {}

# =========================
# KLINES
# =========================
def get_klines(symbol, interval):

    df = pd.DataFrame(

        client.futures_klines(
            symbol=symbol,
            interval=interval,
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
# ANALYZE TF
# =========================
def analyze_timeframe(symbol, timeframe):

    try:

        df = get_klines(symbol, timeframe)

        close = df["close"]

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

        bullish = (
            ema21.iloc[-1] >
            ema200.iloc[-1]
            and
            rsi.iloc[-1] > 50
        )

        bearish = (
            ema21.iloc[-1] <
            ema200.iloc[-1]
            and
            rsi.iloc[-1] < 50
        )

        if bullish:
            return "BULLISH"

        if bearish:
            return "BEARISH"

        return "SIDEWAYS"

    except:
        return "SIDEWAYS"

# =========================
# SIGNAL ENGINE
# =========================
def signal(symbol):

    try:

        df = get_klines(
            symbol,
            INTERVAL
        )

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

        trend = "SIDEWAYS"

        if bullish_trend:
            trend = "BULLISH"

        elif bearish_trend:
            trend = "BEARISH"

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

        mtf_bullish = 0
        mtf_bearish = 0

        mtf_map = {}

        for tf in TIMEFRAMES:

            result = analyze_timeframe(
                symbol,
                tf
            )

            mtf_map[tf] = result

            if result == "BULLISH":
                mtf_bullish += 1

            elif result == "BEARISH":
                mtf_bearish += 1

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

        if bullish_reject:
            long_score += 25

        if bearish_reject:
            short_score += 25

        if good_volume:
            long_score += 25
            short_score += 25

        long_score += (
            mtf_bullish * 5
        )

        short_score += (
            mtf_bearish * 5
        )

        confidence = max(
            long_score,
            short_score
        )

        confidence = min(
            confidence,
            100
        )

        sig = "NONE"

        if (
            long_score >= 85
            and
            mtf_bullish >= 5
            and
            not_too_far
            and
            atr_percent > 0.05
        ):

            sig = "LONG"

        elif (
            short_score >= 85
            and
            mtf_bearish >= 5
            and
            not_too_far
            and
            atr_percent > 0.05
        ):

            sig = "SHORT"

        return {

            "symbol": symbol,
            "signal": sig,
            "price": current_price,

            "rsi": round(
                rsi.iloc[-1],
                2
            ),

            "volume_ratio": round(
                volume_ratio,
                2
            ),

            "atr_percent": round(
                atr_percent,
                4
            ),

            "trend": trend,

            "long_score": long_score,
            "short_score": short_score,

            "confidence": confidence,

            "mtf_bullish": mtf_bullish,
            "mtf_bearish": mtf_bearish,

            "mtf": mtf_map
        }

    except Exception as e:

        console.print(
            f"[red]SIGNAL ERROR:[/red] {e}"
        )

        return None

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
# ANY POSITION
# =========================
def get_any_open_position():

    try:

        positions = client.futures_position_information()

        for p in positions:

            amt = float(
                p["positionAmt"]
            )

            if abs(amt) > 0.000001:
                return p

    except Exception as e:

        console.print(
            f"[red]GLOBAL POSITION ERROR:[/red] {e}"
        )

    return None

# =========================
# BALANCE
# =========================
def get_usdt_balance():

    try:

        balances = client.futures_account_balance()

        for b in balances:

            if b["asset"] == "USDT":

                return float(
                    b["availableBalance"]
                )

    except:
        return 0

    return 0

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
# LEVERAGE
# =========================
def set_leverage(symbol):

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
# CANCEL
# =========================
def cancel_open_orders(symbol):

    try:

        client.futures_cancel_all_open_orders(
            symbol=symbol
        )

    except:
        pass

# =========================
# SYNC EXIT ORDERS
# =========================
def sync_exit_orders(symbol):

    try:

        orders = client.futures_get_open_orders(
            symbol=symbol
        )

        tp_price = 0
        sl_price = 0
        trail_rate = 0

        for o in orders:

            order_type = o["type"]

            if order_type == "TAKE_PROFIT_MARKET":

                tp_price = float(
                    o["stopPrice"]
                )

            elif order_type == "STOP_MARKET":

                sl_price = float(
                    o["stopPrice"]
                )

            elif order_type == "TRAILING_STOP_MARKET":

                trail_rate = float(
                    o.get(
                        "callbackRate",
                        0
                    )
                )

        state["tp_price"] = tp_price
        state["sl_price"] = sl_price
        state["trail"] = trail_rate

    except Exception as e:

        console.print(
            f"[red]SYNC EXIT ERROR:[/red] {e}"
        )

# =========================
# OPEN POSITION
# =========================
def open_position(symbol, side, qty):

    try:

        if get_any_open_position():
            return None

        set_leverage(symbol)

        cancel_open_orders(symbol)

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

        pos = get_position(symbol)

        if not pos:
            return None

        entry_price = float(
            pos["entryPrice"]
        )

        if side == "LONG":

            tp_price = (
                entry_price *
                (1 + TP_ROI)
            )

            sl_price = (
                entry_price *
                (1 - SL_ROI)
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

            stop_side = SIDE_BUY

        # TP
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="TAKE_PROFIT_MARKET",

            stopPrice=round(
                tp_price,
                6
            ),

            closePosition=True,

            workingType="MARK_PRICE",

            priceProtect=True
        )

        # SL
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="STOP_MARKET",

            stopPrice=round(
                sl_price,
                6
            ),

            closePosition=True,

            workingType="MARK_PRICE",

            priceProtect=True
        )

        # TRAILING
        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="TRAILING_STOP_MARKET",

            callbackRate=TRAIL_ROI,

            quantity=qty,

            workingType="MARK_PRICE"
        )

        state["symbol"] = symbol
        state["side"] = side
        state["entry"] = entry_price
        state["qty"] = qty

        sync_exit_orders(symbol)

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
# DASHBOARD
# =========================
def update_dashboard(data, screener):

    pnl = 0

    if state["symbol"]:

        pnl = unrealized_pnl(
            state["symbol"]
        )

    balance = get_usdt_balance()

    web_data.update({

        "symbol": data["symbol"],
        "signal": data["signal"],
        "price": data["price"],

        "rsi": data["rsi"],

        "trend": data["trend"],

        "long_score": data["long_score"],
        "short_score": data["short_score"],

        "confidence": data["confidence"],

        "mtf_bullish": data["mtf_bullish"],
        "mtf_bearish": data["mtf_bearish"],

        "mtf": data["mtf"],

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

        "balance": balance,

        "trade_count": state["trade_count"],

        "winrate": 0,

        "screener": screener
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
        title="AI BOT",
        box=box.DOUBLE_EDGE
    )

    table.add_column("Metric")
    table.add_column("Value")

    for key, value in data.items():

        table.add_row(
            str(key),
            str(value)
        )

    console.print(table)

# =========================
# RUN
# =========================
def run_bot():

    console.print(
        "[green]BOT STARTED[/green]"
    )

    while True:

        try:

            screener = []

            best_coin = None
            best_score = 0

            for coin in SCAN_COINS:

                data = signal(coin)

                if not data:
                    continue

                screener.append({

                    "symbol": data["symbol"],

                    "signal": data["signal"],

                    "long_score": data["long_score"],

                    "short_score": data["short_score"],

                    "trend": data["trend"],

                    "confidence": data["confidence"]
                })

                score = max(
                    data["long_score"],
                    data["short_score"]
                )

                if (
                    data["signal"] != "NONE"
                    and
                    score > best_score
                ):

                    best_score = score
                    best_coin = data

            existing_position = get_any_open_position()

            if existing_position:

                symbol = existing_position["symbol"]

                amt = float(
                    existing_position["positionAmt"]
                )

                entry = float(
                    existing_position["entryPrice"]
                )

                state["symbol"] = symbol
                state["entry"] = entry
                state["qty"] = abs(amt)

                sync_exit_orders(symbol)

                if amt > 0:
                    state["side"] = "LONG"
                else:
                    state["side"] = "SHORT"

            else:

                state["symbol"] = None
                state["side"] = None
                state["entry"] = 0
                state["qty"] = 0

                state["tp_price"] = 0
                state["sl_price"] = 0
                state["trail"] = 0

            if best_coin:

                update_dashboard(
                    best_coin,
                    screener
                )

                terminal_dashboard(
                    best_coin
                )

            if (
                not existing_position
                and
                best_coin
            ):

                if best_coin["signal"] in [
                    "LONG",
                    "SHORT"
                ]:

                    balance = get_usdt_balance()

                    if balance >= ORDER_USDT:

                        step, min_qty = get_lot_filters(
                            best_coin["symbol"]
                        )

                        notional = (
                            ORDER_USDT *
                            LEVERAGE
                        )

                        qty = (
                            notional /
                            best_coin["price"]
                        )

                        qty = qty * 0.98

                        qty = safe_qty(
                            qty,
                            step,
                            min_qty
                        )

                        open_position(

                            best_coin["symbol"],

                            best_coin["signal"],

                            qty
                        )

                        state["trade_count"] += 1

            socketio.sleep(15)

        except Exception as e:

            console.print(
                f"[red]MAIN LOOP ERROR:[/red] {e}"
            )

            socketio.sleep(5)
