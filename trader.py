from binance.client import Client
from binance.enums import *

from math import floor

from config import *
from state import bot_state

# =========================
# BINANCE CLIENT
# =========================

client = Client(
    API_KEY,
    API_SECRET
)

# =========================
# PRECISION CACHE
# =========================

exchange_info = client.futures_exchange_info()

# =========================
# GET BALANCE
# =========================

def get_balance():

    try:

        acc = client.futures_account()

        for asset in acc["assets"]:

            if asset["asset"] == "USDT":

                return float(
                    asset["walletBalance"]
                )

    except Exception as e:

        print("BALANCE ERROR:", e)

    return 0

# =========================
# GET PRICE
# =========================

def get_price(symbol):

    try:

        ticker = client.futures_symbol_ticker(
            symbol=symbol
        )

        return float(
            ticker["price"]
        )

    except Exception as e:

        print("PRICE ERROR:", e)

    return 0

# =========================
# GET SYMBOL INFO
# =========================

def get_symbol_info(symbol):

    for s in exchange_info["symbols"]:

        if s["symbol"] == symbol:

            return s

    return None

# =========================
# GET QTY PRECISION
# =========================

def get_quantity_precision(symbol):

    info = get_symbol_info(symbol)

    if info:

        return info["quantityPrecision"]

    return 3

# =========================
# GET PRICE PRECISION
# =========================

def get_price_precision(symbol):

    info = get_symbol_info(symbol)

    if info:

        return info["pricePrecision"]

    return 2

# =========================
# FORMAT QUANTITY
# =========================

def format_quantity(symbol, qty):

    precision = get_quantity_precision(
        symbol
    )

    factor = 10 ** precision

    return floor(qty * factor) / factor

# =========================
# FORMAT PRICE
# =========================

def format_price(symbol, price):

    precision = get_price_precision(
        symbol
    )

    return round(
        price,
        precision
    )

# =========================
# CHANGE LEVERAGE
# =========================

def set_leverage(symbol):

    try:

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

    except Exception as e:

        print("LEVERAGE ERROR:", e)

# =========================
# CHECK POSITION
# =========================

def has_open_position(symbol):

    try:

        positions = client.futures_position_information(
            symbol=symbol
        )

        for pos in positions:

            amt = float(pos["positionAmt"])

            if amt != 0:

                return True

    except Exception as e:

        print("POSITION ERROR:", e)

    return False

# =========================
# PLACE LONG
# =========================

def place_long():

    try:

        if has_open_position(SYMBOL):

            print("LONG SKIPPED: POSITION EXISTS")
            return

        set_leverage(SYMBOL)

        price = get_price(SYMBOL)

        raw_qty = (
            USDT_PER_TRADE * LEVERAGE
        ) / price

        qty = format_quantity(
            SYMBOL,
            raw_qty
        )

        print("LONG QTY:", qty)

        # =========================
        # MARKET BUY
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_BUY,

            type=FUTURE_ORDER_TYPE_MARKET,

            quantity=qty
        )

        # =========================
        # TP SL
        # =========================

        sl = price * (
            1 - SL_PERCENT / 100
        )

        tp = price * (
            1 + TP_PERCENT / 100
        )

        sl = format_price(
            SYMBOL,
            sl
        )

        tp = format_price(
            SYMBOL,
            tp
        )

        # =========================
        # STOP LOSS
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_SELL,

            type="STOP_MARKET",

            stopPrice=sl,

            closePosition=True
        )

        # =========================
        # TAKE PROFIT
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_SELL,

            type="TAKE_PROFIT_MARKET",

            stopPrice=tp,

            closePosition=True
        )

        # =========================
        # TRAILING STOP
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_SELL,

            type="TRAILING_STOP_MARKET",

            callbackRate=TRAILING_PERCENT,

            quantity=qty
        )

        # =========================
        # SAVE STATE
        # =========================

        bot_state["position"] = "LONG"

        bot_state["entry"] = price

        bot_state["sl_price"] = sl

        bot_state["tp_price"] = tp

        bot_state["trail"] = TRAILING_PERCENT

        print("LONG OPENED")

    except Exception as e:

        print("LONG ERROR:", e)

# =========================
# PLACE SHORT
# =========================

def place_short():

    try:

        if has_open_position(SYMBOL):

            print("SHORT SKIPPED: POSITION EXISTS")
            return

        set_leverage(SYMBOL)

        price = get_price(SYMBOL)

        raw_qty = (
            USDT_PER_TRADE * LEVERAGE
        ) / price

        qty = format_quantity(
            SYMBOL,
            raw_qty
        )

        print("SHORT QTY:", qty)

        # =========================
        # MARKET SELL
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_SELL,

            type=FUTURE_ORDER_TYPE_MARKET,

            quantity=qty
        )

        # =========================
        # TP SL
        # =========================

        sl = price * (
            1 + SL_PERCENT / 100
        )

        tp = price * (
            1 - TP_PERCENT / 100
        )

        sl = format_price(
            SYMBOL,
            sl
        )

        tp = format_price(
            SYMBOL,
            tp
        )

        # =========================
        # STOP LOSS
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_BUY,

            type="STOP_MARKET",

            stopPrice=sl,

            closePosition=True
        )

        # =========================
        # TAKE PROFIT
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_BUY,

            type="TAKE_PROFIT_MARKET",

            stopPrice=tp,

            closePosition=True
        )

        # =========================
        # TRAILING STOP
        # =========================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_BUY,

            type="TRAILING_STOP_MARKET",

            callbackRate=TRAILING_PERCENT,

            quantity=qty
        )

        # =========================
        # SAVE STATE
        # =========================

        bot_state["position"] = "SHORT"

        bot_state["entry"] = price

        bot_state["sl_price"] = sl

        bot_state["tp_price"] = tp

        bot_state["trail"] = TRAILING_PERCENT

        print("SHORT OPENED")

    except Exception as e:

        print("SHORT ERROR:", e)

# =========================
# UPDATE PNL
# =========================

def update_pnl():

    try:

        positions = client.futures_position_information(
            symbol=SYMBOL
        )

        for pos in positions:

            amt = float(pos["positionAmt"])

            if amt != 0:

                pnl = float(
                    pos["unRealizedProfit"]
                )

                bot_state["pnl"] = pnl

                bot_state["pnl_idr"] = pnl * 16000

                return

        bot_state["pnl"] = 0
        bot_state["pnl_idr"] = 0

    except Exception as e:

        print("PNL ERROR:", e)
