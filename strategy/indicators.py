import ta

def add_indicators(df):

    # ====================================
    # EMA
    # ====================================

    df["ema_fast"] = ta.trend.ema_indicator(
        df["close"],
        window=20
    )

    df["ema_slow"] = ta.trend.ema_indicator(
        df["close"],
        window=50
    )

    # ====================================
    # RSI
    # ====================================

    df["rsi"] = ta.momentum.rsi(
        df["close"],
        window=14
    )

    # ====================================
    # MACD
    # ====================================

    macd = ta.trend.MACD(df["close"])

    df["macd"] = macd.macd()

    df["macd_signal"] = macd.macd_signal()

    # ====================================
    # ATR
    # ====================================

    df["atr"] = ta.volatility.average_true_range(
        df["high"],
        df["low"],
        df["close"],
        window=14
    )

    # ====================================
    # ADX
    # ====================================

    df["adx"] = ta.trend.adx(
        df["high"],
        df["low"],
        df["close"],
        window=14
    )

    # ====================================
    # VOLUME MA
    # ====================================

    df["volume_ma"] = df["volume"].rolling(
        20
    ).mean()

    return df
