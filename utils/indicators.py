from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange


def rsi(close, period=14):
    return RSIIndicator(close, period).rsi()


def ema(close, period):
    return EMAIndicator(close, period).ema_indicator()


def atr(high, low, close, period=14):
    return AverageTrueRange(
        high,
        low,
        close,
        period
    ).average_true_range()
