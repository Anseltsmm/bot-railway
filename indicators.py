import pandas as pd
import ta

def add_indicators(df):

    df["ema20"] = ta.trend.ema_indicator(
        df["close"],
        window=20
    )

    df["ema50"] = ta.trend.ema_indicator(
        df["close"],
        window=50
    )

    df["rsi"] = ta.momentum.rsi(
        df["close"],
        window=14
    )

    df["atr"] = ta.volatility.average_true_range(
        df["high"],
        df["low"],
        df["close"],
        window=14
    )

    return df
