import ta

def add_indicators(df):

    df["ema_fast"] = ta.trend.ema_indicator(
        df["close"],
        window=20
    )

    df["ema_slow"] = ta.trend.ema_indicator(
        df["close"],
        window=50
    )

    df["rsi"] = ta.momentum.rsi(
        df["close"],
        window=14
    )

    macd = ta.trend.MACD(df["close"])

    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    return df
