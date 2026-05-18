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
    os.getenv("TRAIL_ROI", 0.002)
)

USD_IDR = int(
    os.getenv("USD_IDR", 17438)
)

MARGIN_TYPE = os.getenv(
    "MARGIN_TYPE",
    "ISOLATED"
).upper()

# =========================
# MULTI TIMEFRAME
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
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "NEARUSDT"
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
    "confidence": 0,

    "mtf_bullish": 0,
    "mtf_bearish": 0,
    "mtf_total": 0,
    "mtf_status": "NONE",

    "mtf": {},

    "position": "NONE",

    "entry": 0,
    "tp_price": 0,
    "sl_price": 0,
    "trail": 0,

    "pnl": 0,
    "pnl_idr": 0,

    "balance": 0,

    "trade_count": 0,
    "winrate": 0,

    "screener": [],

    "chart_symbol": "BINANCE:BTCUSDT",
    "chart_interval": "1"
}

# =========================
# GET KLINES
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
# ANALYZE TIMEFRAME
# =========================
def analyze_timeframe(symbol, timeframe):

    try:

        df = get_klines(
            symbol,
            timeframe
        )

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

        mtf_total = len(TIMEFRAMES)

        mtf_status = "NEUTRAL"

        if mtf_bullish > mtf_bearish:
            mtf_status = "BULLISH"

        elif mtf_bearish > mtf_bullish:
            mtf_status = "BEARISH"

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

        if confidence > 100:
            confidence = 100

        sig = "NONE"

        if (
            long_score >= 85
            and mtf_bullish >= 5
            and not_too_far
            and atr_percent > 0.05
        ):
            sig = "LONG"

        elif (
            short_score >= 85
            and mtf_bearish >= 5
            and not_too_far
            and atr_percent > 0.05
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
            "structure": structure,

            "long_score": long_score,
            "short_score": short_score,

            "confidence": confidence,

            "mtf_bullish": mtf_bullish,
            "mtf_bearish": mtf_bearish,
            "mtf_total": mtf_total,
            "mtf_status": mtf_status,

            "mtf": mtf_map
        }

    except Exception as e:

        console.print(
            f"[red]SIGNAL ERROR {symbol}:[/red] {e}"
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
# GET ANY POSITION
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
# RESTORE POSITION
# =========================
def restore_position_state():

    try:

        pos = get_any_open_position()

        if not pos:

            console.print(
                "[cyan]NO ACTIVE POSITION[/cyan]"
            )

            state["symbol"] = None
            state["side"] = None
            state["entry"] = 0
            state["qty"] = 0

            return

        symbol = pos["symbol"]

        amt = float(
            pos["positionAmt"]
        )

        entry_price = float(
            pos["entryPrice"]
        )

        state["symbol"] = symbol

        state["entry"] = entry_price

        state["qty"] = abs(amt)

        if amt > 0:

            state["side"] = "LONG"

            tp_price = entry_price * (1 + TP_ROI)

            sl_price = entry_price * (1 - SL_ROI)

        else:

            state["side"] = "SHORT"

            tp_price = entry_price * (1 - TP_ROI)

            sl_price = entry_price * (1 + SL_ROI)

        state["tp_price"] = tp_price
        state["sl_price"] = sl_price
        state["trail"] = TRAIL_ROI

        console.print(
            f"[green]RESTORED POSITION:[/green] "
            f"{state['side']} "
            f"{symbol}"
        )

    except Exception as e:

        console.print(
            f"[red]RESTORE ERROR:[/red] {e}"
        )

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

    except Exception as e:

        console.print(
            f"[red]BALANCE ERROR:[/red] {e}"
        )

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

    except Exception as e:

        console.print(
            f"[red]LEVERAGE ERROR:[/red] {e}"
        )

    try:

        client.futures_change_margin_type(
            symbol=symbol,
            marginType=MARGIN_TYPE
        )

    except Exception as e:

        if "No need to change margin type" not in str(e):

            console.print(
                f"[red]MARGIN ERROR:[/red] {e}"
            )

# =========================
# CANCEL ORDERS
# =========================
def cancel_open_orders(symbol):

    try:

        client.futures_cancel_all_open_orders(
            symbol=symbol
        )

    except Exception as e:

        console.print(
            f"[red]CANCEL ERROR:[/red] {e}"
        )

# =========================
# OPEN POSITION
# =========================
def open_position(symbol, side, qty):

    try:

        if get_any_open_position():

            console.print(
                "[yellow]GLOBAL POSITION EXISTS[/yellow]"
            )

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

            console.print(
                "[red]FAILED GET POSITION[/red]"
            )

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

        state["symbol"] = symbol
        state["side"] = side
        state["entry"] = entry_price
        state["qty"] = qty

        state["tp_price"] = tp_price
        state["sl_price"] = sl_price
        state["trail"] = TRAIL_ROI

        # TAKE PROFIT
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

        # STOP LOSS
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

        # TRAILING STOP
        callback_rate = max(
            0.1,
            min(TRAIL_ROI * 100, 5)
        )

        client.futures_create_order(

            symbol=symbol,

            side=stop_side,

            type="TRAILING_STOP_MARKET",

            callbackRate=round(
                callback_rate,
                2
            ),

            quantity=qty,

            workingType="MARK_PRICE"
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
# DASHBOARD
# =========================
def update_dashboard(data, screener):

    pnl = 0

    if state["symbol"]:

        pnl = unrealized_pnl(
            state["symbol"]
        )

    usdt_balance = get_usdt_balance()

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
        "confidence": data["confidence"],

        "mtf_bullish": data["mtf_bullish"],
        "mtf_bearish": data["mtf_bearish"],
        "mtf_total": data["mtf_total"],
        "mtf_status": data["mtf_status"],

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

        "balance": usdt_balance,

        "trade_count": state["trade_count"],

        "winrate": round(
            winrate,
            2
        ),

        "screener": screener,

        "chart_symbol": f"BINANCE:{data['symbol']}",

        "chart_interval": "1"
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
        title="AI MULTI TF BOT",
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
# RUN BOT
# =========================
def run_bot():

    console.print(
        "[green]BOT STARTED SUCCESSFULLY[/green]"
    )

    restore_position_state()

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
                    and score > best_score
                ):

                    best_score = score
                    best_coin = data

            if best_coin:

                update_dashboard(
                    best_coin,
                    screener
                )

                terminal_dashboard(
                    best_coin
                )

            existing_position = get_any_open_position()

            if existing_position:

                symbol = existing_position["symbol"]

                amt = float(
                    existing_position["positionAmt"]
                )

                entry_price = float(
                    existing_position["entryPrice"]
                )

                state["symbol"] = symbol

                state["entry"] = entry_price

                state["qty"] = abs(amt)

                if amt > 0:
                    state["side"] = "LONG"
                else:
                    state["side"] = "SHORT"

                console.print(
                    f"[yellow]ACTIVE POSITION:[/yellow] "
                    f"{state['side']} "
                    f"{symbol}"
                )

                socketio.sleep(10)

                continue

            else:

                state["symbol"] = None
                state["side"] = None
                state["entry"] = 0
                state["qty"] = 0

            if best_coin:

                symbol = best_coin["symbol"]

                if best_coin["signal"] not in [
                    "LONG",
                    "SHORT"
                ]:

                    socketio.sleep(10)
                    continue

                if get_any_open_position():

                    socketio.sleep(10)
                    continue

                available_balance = get_usdt_balance()

                if available_balance < ORDER_USDT:

                    console.print(
                        "[red]INSUFFICIENT BALANCE[/red]"
                    )

                    socketio.sleep(10)

                    continue

                step, min_qty = get_lot_filters(
                    symbol
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

                if qty <= 0:

                    socketio.sleep(10)

                    continue

                console.print(
                    f"[cyan]TRY ENTRY "
                    f"{best_coin['signal']} "
                    f"{symbol}[/cyan]"
                )

                order = open_position(

                    symbol,

                    best_coin["signal"],

                    qty
                )

                if order:

                    state["trade_count"] += 1

                    console.print(
                        "[green]POSITION OPENED[/green]"
                    )

            socketio.sleep(15)

        except Exception as e:

            console.print(
                f"[red]MAIN LOOP ERROR:[/red] {e}"
            )

            socketio.sleep(5)
