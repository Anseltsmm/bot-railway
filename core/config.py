import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

INTERVAL = os.getenv("INTERVAL", "1m")

LEVERAGE = int(os.getenv("LEVERAGE", 10))

ORDER_USDT = float(os.getenv("ORDER_USDT", 5))

TP_ROI = float(os.getenv("TP_ROI", 0.02))
SL_ROI = float(os.getenv("SL_ROI", 0.01))
TRAIL_ROI = float(os.getenv("TRAIL_ROI", 0.2))

USD_IDR = int(os.getenv("USD_IDR", 17400))

MARGIN_TYPE = os.getenv(
    "MARGIN_TYPE",
    "ISOLATED"
)
