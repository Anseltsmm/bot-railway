from core.client import client
from core.config import (
    ORDER_USDT,
    LEVERAGE
)

from utils.quantity import safe_qty


def get_balance():

    balances = client.futures_account_balance()

    for b in balances:

        if b["asset"] == "USDT":
            return float(b["availableBalance"])

    return 0


def calculate_qty(symbol, price):

    info = client.futures_exchange_info()

    step = 0.001
    min_qty = 0.001

    for s in info["symbols"]:

        if s["symbol"] == symbol:

            for f in s["filters"]:

                if f["filterType"] == "LOT_SIZE":

                    step = float(f["stepSize"])
                    min_qty = float(f["minQty"])

    notional = ORDER_USDT * LEVERAGE

    qty = notional / price

    return safe_qty(
        qty,
        step,
        min_qty
    )
