from binance.client import Client
from binance.enums import *

from math import floor

from config import *
from state import bot_state

# =========================================
# BINANCE CLIENT
# =========================================

client = Client(
    API_KEY,
    API_SECRET
)

# =========================================
# EXCHANGE INFO CACHE
# =========================================

exchange_info = client.futures_exchange_info()

# =========================================
# GET SYMBOL INFO
# =========================================

def get_symbol_info(symbol):

    for s in exchange_info["symbols"]:

        if s["symbol"] == symbol:
            return s

    return None

# =========================================
# GET PRICE PRECISION
# =========================================

def get_price_precision(symbol):

    info = get_symbol_info(symbol)

    if info:
        return info["pricePrecision"]

    return 2

# =========================================
# GET QTY PRECISION
# =========================================

def get_quantity_precision(symbol):

    info = get_symbol_info(symbol)

    if info:
        return info["quantityPrecision"]

    return 3

# =========================================
# FORMAT PRICE
# =========================================

def format_price(symbol, price):

    precision = get_price_precision(symbol)

    return round(
        float(price),
        precision
    )

# =========================================
# FORMAT QUANTITY
# =========================================

def format_quantity(symbol, qty):

    precision = get_quantity_precision(symbol)

    factor = 10 ** precision

    return floor(qty * factor) / factor

# =========================================
# GET BALANCE
# =========================================

def get_balance():

    try:

        account = client.futures_account()

        for asset in account["assets"]:

            if asset["asset"] == "USDT":

                return float(
                    asset["walletBalance"]
                )

    except Exception as e:

        print("BALANCE ERROR:", e)

    return 0

# =========================================
# GET PRICE
# =========================================

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

# =========================================
# SET LEVERAGE
# =========================================

def set_leverage(symbol):

    try:

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

    except Exception as e:

        print("LEVERAGE ERROR:", e)

# =========================================
# CANCEL ALL OPEN ORDERS
# =========================================

def cancel_all_orders(symbol):

    try:

        client.futures_cancel_all_open_orders(
            symbol=symbol
        )

    except Exception as e:

        print("CANCEL ERROR:", e)

# =========================================
# CHECK OPEN POSITION
# =========================================

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

# =========================================
# SYNC POSITION
# =========================================

def sync_position():

    try:

        positions = client.futures_position_information(
            symbol=SYMBOL
        )

        active = False

        for pos in positions:

            amt = float(pos["positionAmt"])

            if amt > 0:

                bot_state["position"] = "LONG"

                bot_state["entry"] = float(
                    pos["entryPrice"]
                )

                active = True

            elif amt < 0:

                bot_state["position"] = "SHORT"

                bot_state["entry"] = float(
                    pos["entryPrice"]
                )

                active = True

        if not active:

            bot_state["position"] = "NONE"

            bot_state["entry"] = 0
            bot_state["sl_price"] = 0
            bot_state["tp_price"] = 0
            bot_state["trail"] = 0

    except Exception as e:

        print("SYNC ERROR:", e)

# =========================================
# UPDATE PNL
# =========================================

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

                bot_state["pnl_idr"] = pnl * USD_TO_IDR

                return

        bot_state["pnl"] = 0
        bot_state["pnl_idr"] = 0

    except Exception as e:

        print("PNL ERROR:", e)

# =========================================
# CALCULATE QUANTITY
# =========================================

def calculate_quantity(price):

    raw_qty = (
        USDT_PER_TRADE * LEVERAGE
    ) / price

    qty = format_quantity(
        SYMBOL,
        raw_qty
    )

    return qty

# =========================================
# CREATE SL TP TRAILING
# =========================================

def create_risk_orders(
    side,
    qty,
    sl_price,
    tp_price
):

    try:

        # =====================================
        # STOP LOSS
        # =====================================

        client.futures_create_order(

            symbol=SYMBOL,

            side=side,

            type="STOP_MARKET",

            stopPrice=sl_price,

            closePosition=True,

            workingType="MARK_PRICE"
        )

        # =====================================
        # TAKE PROFIT
        # =====================================

        client.futures_create_order(

            symbol=SYMBOL,

            side=side,

            type="TAKE_PROFIT_MARKET",

            stopPrice=tp_price,

            closePosition=True,

            workingType="MARK_PRICE"
        )

        # =====================================
        # TRAILING STOP
        # =====================================

        client.futures_create_order(

            symbol=SYMBOL,

            side=side,

            type="TRAILING_STOP_MARKET",

            callbackRate=TRAILING_PERCENT,

            quantity=qty,

            workingType="MARK_PRICE"
        )

    except Exception as e:

        print("RISK ORDER ERROR:", e)

# =========================================
# PLACE LONG
# =========================================

def place_long():

    try:

        if has_open_position(SYMBOL):

            print("LONG SKIPPED")

            return

        cancel_all_orders(SYMBOL)

        set_leverage(SYMBOL)

        price = get_price(SYMBOL)

        qty = calculate_quantity(price)

        print("LONG QTY:", qty)

        # =====================================
        # MARKET BUY
        # =====================================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_BUY,

            type=FUTURE_ORDER_TYPE_MARKET,

            quantity=qty
        )

        # =====================================
        # SL TP
        # =====================================

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

        # =====================================
        # RISK MANAGEMENT
        # =====================================

        create_risk_orders(
            SIDE_SELL,
            qty,
            sl,
            tp
        )

        # =====================================
        # SAVE STATE
        # =====================================

        bot_state["position"] = "LONG"

        bot_state["entry"] = price

        bot_state["sl_price"] = sl

        bot_state["tp_price"] = tp

        bot_state["trail"] = TRAILING_PERCENT

        print("LONG OPENED")

    except Exception as e:

        print("LONG ERROR:", e)

# =========================================
# PLACE SHORT
# =========================================

def place_short():

    try:

        if has_open_position(SYMBOL):

            print("SHORT SKIPPED")

            return

        cancel_all_orders(SYMBOL)

        set_leverage(SYMBOL)

        price = get_price(SYMBOL)

        qty = calculate_quantity(price)

        print("SHORT QTY:", qty)

        # =====================================
        # MARKET SELL
        # =====================================

        client.futures_create_order(

            symbol=SYMBOL,

            side=SIDE_SELL,

            type=FUTURE_ORDER_TYPE_MARKET,

            quantity=qty
        )

        # =====================================
        # SL TP
        # =====================================

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

        # =====================================
        # RISK MANAGEMENT
        # =====================================

        create_risk_orders(
            SIDE_BUY,
            qty,
            sl,
            tp
        )

        # =====================================
        # SAVE STATE
        # =====================================

        bot_state["position"] = "SHORT"

        bot_state["entry"] = price

        bot_state["sl_price"] = sl

        bot_state["tp_price"] = tp

        bot_state["trail"] = TRAILING_PERCENT

        print("SHORT OPENED")

    except Exception as e:

        print("SHORT ERROR:", e)
