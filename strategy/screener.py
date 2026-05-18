from strategy.signal_engine import signal
from core.config import INTERVAL

SCAN_COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "SOLUSDT"
]


def scan_market():

    best = None

    screener = []

    best_score = 0

    for symbol in SCAN_COINS:

        data = signal(symbol, INTERVAL)

        screener.append(data)

        score = max(
            data["mtf_bullish"],
            data["mtf_bearish"]
        )

        if (
            data["signal"] != "NONE"
            and score > best_score
        ):

            best_score = score
            best = data

    return best, screener
