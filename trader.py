from binance.client import Client
from binance.enums import *
from config import *
from state import bot_state

client = Client(API_KEY, API_SECRET)

def get_balance():

    acc = client.futures_account()

    for a in acc["assets"]:

        if a["asset"] == "USDT":
            return float(a["walletBalance"])

    return 0

def get_price(symbol):

    ticker = client.futures_symbol_ticker(
        symbol=symbol
    )

    return float(ticker["price"])

def place_long():

    price = get_price(SYMBOL)

    qty = round(
        (USDT_PER_TRADE * LEVERAGE) / price,
        3
    )

    client.futures_create_order(
        symbol=SYMBOL,
        side=SIDE_BUY,
        type=FUTURE_ORDER_TYPE_MARKET,
        quantity=qty
    )

    sl = price * (1 - SL_PERCENT / 100)
    tp = price * (1 + TP_PERCENT / 100)

    client.futures_create_order(
        symbol=SYMBOL,
        side=SIDE_SELL,
        type="STOP_MARKET",
        stopPrice=round(sl, 2),
        closePosition=True
    )

    client.futures_create_order(
        symbol=SYMBOL,
        side=SIDE_SELL,
        type="TAKE_PROFIT_MARKET",
        stopPrice=round(tp, 2),
        closePosition=True
    )

    bot_state["position"] = "LONG"
    bot_state["entry"] = price
    bot_state["sl_price"] = sl
    bot_state["tp_price"] = tp
    bot_state["trail"] = TRAILING_PERCENT

def place_short():

    price = get_price(SYMBOL)

    qty = round(
        (USDT_PER_TRADE * LEVERAGE) / price,
        3
    )

    client.futures_create_order(
        symbol=SYMBOL,
        side=SIDE_SELL,
        type=FUTURE_ORDER_TYPE_MARKET,
        quantity=qty
    )

    sl = price * (1 + SL_PERCENT / 100)
    tp = price * (1 - TP_PERCENT / 100)

    client.futures_create_order(
        symbol=SYMBOL,
        side=SIDE_BUY,
        type="STOP_MARKET",
        stopPrice=round(sl, 2),
        closePosition=True
    )

    client.futures_create_order(
        symbol=SYMBOL,
        side=SIDE_BUY,
        type="TAKE_PROFIT_MARKET",
        stopPrice=round(tp, 2),
        closePosition=True
    )

    bot_state["position"] = "SHORT"
    bot_state["entry"] = price
    bot_state["sl_price"] = sl
    bot_state["tp_price"] = tp
    bot_state["trail"] = TRAILING_PERCENT
