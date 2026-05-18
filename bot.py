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

INTERVAL = os.getenv("INTERVAL", "5m")

LEVERAGE = int(
    os.getenv("LEVERAGE", 10)
)

ORDER_USDT = float(
    os.getenv("ORDER_USDT", 1.2)
)

TP_ROI = float(
    os.getenv("TP_ROI", 0.02)
)

SL_ROI = float(
    os.getenv("SL_ROI", 0.01)
)

TRAIL_ROI = float(
    os.getenv("TRAIL_ROI", 0.8)
)

USD_IDR = int(
    os.getenv("USD_IDR", 17438)
)

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

    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "BNBUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "LTCUSDT",
    "DOTUSDT",
    "NEARUSDT",
    "WIFUSDT"

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

    "screener": []
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
# ANALYZE TF
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

        avg_volume = (
            volume.rolling(20).mean()
        )

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

        # =========================
        # MULTI TF
        # =========================
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

        # =========================
        # SCORE
        # =========================
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

        # =========================
        # SIGNAL
        # =========================
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
# DASHBOARD
# =========================
def update_dashboard(data, screener):

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
# MAIN LOOP
# =========================
def run_bot():

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

                if score > best_score:

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

            socketio.sleep(10)

        except Exception as e:

            console.print(
                f"[red]MAIN LOOP ERROR:[/red] {e}"
            )

            socketio.sleep(5)
