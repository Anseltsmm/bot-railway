# =========================
# bot.py
# =========================

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import math
import time
import pandas as pd

from dotenv import load_dotenv

from binance.client import Client
from binance.enums import *

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
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

# =========================
# TIMEFRAMES
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
    "WIFUSDT",
    "NEARUSDT"
]

# =========================
# CONSOLE
# =========================
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

    "macd": 0,

    "volume_ratio": 0,

    "atr_percent": 0,

    "trend": "NONE",

    "structure": "NONE",

    "long_score": 0,

    "short_score": 0,

    "mtf_bullish": 0,

    "mtf_bearish": 0,

    "mtf_total": 0,

    "mtf_status": "NEUTRAL",

    "ai_confidence": 0,

    "timeframes": {},

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
# CACHE
# =========================
KLINE_CACHE = {}

CACHE_SECONDS = 10

# =========================
# GET KLINES
# =========================
def get_klines(symbol, interval):

    key = f"{symbol}_{interval}"

    now = time.time()

    if key in KLINE_CACHE:

        cache_time = KLINE_CACHE[key]["time"]

        if now - cache_time < CACHE_SECONDS:

            return KLINE_CACHE[key]["data"]

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

    KLINE_CACHE[key] = {

        "time": now,

        "data": df
    }

    return df

# =========================
# TIMEFRAME ANALYSIS
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

        macd = MACD(close)

        macd_line = macd.macd()
        signal_line = macd.macd_signal()

        bullish = (

            ema21.iloc[-1] >
            ema200.iloc[-1]

            and

            rsi.iloc[-1] > 50

            and

            macd_line.iloc[-1] >
            signal_line.iloc[-1]
        )

        bearish = (

            ema21.iloc[-1] <
            ema200.iloc[-1]

            and

            rsi.iloc[-1] < 50

            and

            macd_line.iloc[-1] <
            signal_line.iloc[-1]
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

        macd = MACD(close)

        macd_line = macd.macd()
        signal_line = macd.macd_signal()

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
        # MULTI TIMEFRAME
        # =========================
        mtf_bullish = 0
        mtf_bearish = 0

        tf_map = {}

        for tf in TIMEFRAMES:

            result = analyze_timeframe(
                symbol,
                tf
            )

            tf_map[tf] = result

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
            long_score += 20

        if bearish_trend:
            short_score += 20

        if rsi.iloc[-1] > 55:
            long_score += 15

        if rsi.iloc[-1] < 45:
            short_score += 15

        if good_volume:
            long_score += 15
            short_score += 15

        if bullish_reject:
            long_score += 10

        if bearish_reject:
            short_score += 10

        if macd_line.iloc[-1] > signal_line.iloc[-1]:
            long_score += 15

        if macd_line.iloc[-1] < signal_line.iloc[-1]:
            short_score += 15

        if structure == "BREAKOUT":
            long_score += 10

        if structure == "BREAKDOWN":
            short_score += 10

        long_score += (
            mtf_bullish * 5
        )

        short_score += (
            mtf_bearish * 5
        )

        ai_confidence = max(
            long_score,
            short_score
        )

        if ai_confidence > 100:
            ai_confidence = 100

        sig = "NONE"

        if (

            long_score >= 85

            and

            not_too_far

            and

            atr_percent > 0.05

            and

            mtf_bullish >= 5
        ):

            sig = "LONG"

        elif (

            short_score >= 85

            and

            not_too_far

            and

            atr_percent > 0.05

            and

            mtf_bearish >= 5
        ):

            sig = "SHORT"

        return {

            "symbol": symbol,

            "signal": sig,

            "price": current_price,

            "rsi": rsi.iloc[-1],

            "macd": macd_line.iloc[-1],

            "volume_ratio": volume_ratio,

            "atr_percent": atr_percent,

            "trend": trend,

            "structure": structure,

            "long_score": long_score,

            "short_score": short_score,

            "mtf_bullish": mtf_bullish,

            "mtf_bearish": mtf_bearish,

            "mtf_total": mtf_total,

            "mtf_status": mtf_status,

            "ai_confidence": ai_confidence,

            "timeframes": tf_map
        }

    except Exception as e:

        console.print(
            f"[red]SIGNAL ERROR {symbol}:[/red] {e}"
        )

        return None

# =========================
# MARKET SCAN
# =========================
def scan_market():

    best_coin = None
    best_score = 0

    screener = []

    console.print(
        "[cyan]SCANNING MARKET...[/cyan]"
    )

    for coin in SCAN_COINS:

        data = signal(coin)

        if not data:
            continue

        screener.append({

            "symbol": coin,

            "signal": data["signal"],

            "long_score": data["long_score"],

            "short_score": data["short_score"],

            "trend": data["trend"],

            "confidence": data["ai_confidence"]
        })

        score = max(
            data["long_score"],
            data["short_score"]
        )

        console.print(

            f"{coin} | "
            f"{data['signal']} | "
            f"CONF {data['ai_confidence']}%"
        )

        if (

            data["signal"] != "NONE"

            and

            score > best_score
        ):

            best_score = score

            best_coin = data

    return best_coin, screener

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
# UNREALIZED PNL
# =========================
def unrealized_pnl(symbol):

    pos = get_position(symbol)

    if not pos:
        return 0

    return float(
        pos["unRealizedProfit"]
    )

# =========================
# MAIN LOOP
# =========================
def start_bot():

    while True:

        try:

            best, screener = scan_market()

            if not best:

                web_data["screener"] = screener

                console.print(
                    "[yellow]NO SIGNAL FOUND[/yellow]"
                )

                time.sleep(10)

                continue

            web_data.update({

                "symbol": best["symbol"],

                "signal": best["signal"],

                "price": best["price"],

                "rsi": best["rsi"],

                "macd": best["macd"],

                "volume_ratio": best["volume_ratio"],

                "atr_percent": best["atr_percent"],

                "trend": best["trend"],

                "structure": best["structure"],

                "long_score": best["long_score"],

                "short_score": best["short_score"],

                "mtf_bullish": best["mtf_bullish"],

                "mtf_bearish": best["mtf_bearish"],

                "mtf_total": best["mtf_total"],

                "mtf_status": best["mtf_status"],

                "ai_confidence": best["ai_confidence"],

                "timeframes": best["timeframes"],

                "screener": screener
            })

            console.clear()

            table = Table(
                title="AI MULTI TF BOT",
                box=box.DOUBLE_EDGE
            )

            table.add_column("Metric")
            table.add_column("Value")

            table.add_row(
                "Symbol",
                best["symbol"]
            )

            table.add_row(
                "Signal",
                best["signal"]
            )

            table.add_row(
                "Trend",
                best["trend"]
            )

            table.add_row(
                "AI Confidence",
                f'{best["ai_confidence"]}%'
            )

            table.add_row(
                "MTF Bull",
                str(best["mtf_bullish"])
            )

            table.add_row(
                "MTF Bear",
                str(best["mtf_bearish"])
            )

            console.print(table)

            time.sleep(15)

        except Exception as e:

            console.print(
                f"[red]BOT ERROR:[/red] {e}"
            )

            time.sleep(5)
