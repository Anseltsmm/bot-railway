import pandas as pd
import numpy as np
import joblib

from binance.client import Client

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler

from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

from config import *

# =========================================
# BINANCE
# =========================================

client = Client(
    API_KEY,
    API_SECRET
)

# =========================================
# DOWNLOAD DATA
# =========================================

print("DOWNLOADING MARKET DATA...")

klines = client.futures_klines(
    symbol=SYMBOL,
    interval="5m",
    limit=1500
)

df = pd.DataFrame(klines)

df = df.iloc[:, :6]

df.columns = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "volume"
]

df = df.astype(float)

# =========================================
# INDICATORS
# =========================================

print("CALCULATING INDICATORS...")

# EMA

df["ema_fast"] = EMAIndicator(
    close=df["close"],
    window=20
).ema_indicator()

df["ema_slow"] = EMAIndicator(
    close=df["close"],
    window=50
).ema_indicator()

# RSI

df["rsi"] = RSIIndicator(
    close=df["close"],
    window=14
).rsi()

# MACD

macd = MACD(df["close"])

df["macd"] = macd.macd()

df["macd_signal"] = macd.macd_signal()

# ATR

atr = AverageTrueRange(
    high=df["high"],
    low=df["low"],
    close=df["close"],
    window=14
)

df["atr"] = atr.average_true_range()

# ADX

adx = ADXIndicator(
    high=df["high"],
    low=df["low"],
    close=df["close"],
    window=14
)

df["adx"] = adx.adx()

# VOLUME MA

df["volume_ma"] = (
    df["volume"]
    .rolling(20)
    .mean()
)

# =========================================
# TARGET
# =========================================

print("CREATING TARGET...")

future_close = df["close"].shift(-3)

df["target"] = np.where(
    future_close > df["close"],
    1,
    0
)

# =========================================
# CLEAN DATA
# =========================================

df.dropna(inplace=True)

# =========================================
# FEATURES
# =========================================

features = [

    "ema_fast",
    "ema_slow",

    "rsi",

    "macd",
    "macd_signal",

    "atr",
    "adx",

    "volume",
    "volume_ma"
]

X = df[features]

y = df["target"]

# =========================================
# SCALE
# =========================================

print("SCALING DATA...")

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X)

# =========================================
# TRAIN TEST SPLIT
# =========================================

X_train, X_test, y_train, y_test = train_test_split(

    X_scaled,
    y,

    test_size=0.2,

    shuffle=False
)

# =========================================
# MODEL
# =========================================

print("TRAINING AI MODEL...")

model = RandomForestClassifier(

    n_estimators=200,

    max_depth=10,

    random_state=42
)

model.fit(
    X_train,
    y_train
)

# =========================================
# TEST
# =========================================

pred = model.predict(X_test)

acc = accuracy_score(
    y_test,
    pred
)

# =========================================
# SAVE MODEL
# =========================================

joblib.dump(
    model,
    "ai/model.pkl"
)

joblib.dump(
    scaler,
    "ai/scaler.pkl"
)

# =========================================
# DONE
# =========================================

print("=" * 50)

print("MODEL TRAINED SUCCESSFULLY")

print(f"Accuracy: {acc:.4f}")

print("=" * 50)
