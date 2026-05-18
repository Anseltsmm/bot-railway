from binance.enums import *

from core.client import client
from core.config import (
    TP_ROI,
    SL_ROI,
    TRAIL_ROI
)

from core.state import state

from trading.leverage_manager import set_leverage


def open_position(symbol, side, qty):

    set_leverage(symbol)

    order = client.futures_create_order(

        symbol=symbol,

        side=(
            SIDE_BUY
            if side == "LONG"
            else SIDE_SELL
        ),

        type=ORDER_TYPE_MARKET,

        quantity=qty
    )

    pos = client.futures_position_information(
        symbol=symbol
    )[0]

    entry = float(pos["entryPrice"])

    if side == "LONG":

        tp = entry * (1 + TP_ROI)
        sl = entry * (1 - SL_ROI)

        close_side = SIDE_SELL

    else:

        tp = entry * (1 - TP_ROI)
        sl = entry * (1 + SL_ROI)

        close_side = SIDE_BUY

    client.futures_create_order(

        symbol=symbol,

        side=close_side,

        type="TAKE_PROFIT_MARKET",

        stopPrice=round(tp, 4),

        closePosition=True,

        workingType="MARK_PRICE"
    )

    client.futures_create_order(

        symbol=symbol,

        side=close_side,

        type="STOP_MARKET",

        stopPrice=round(sl, 4),

        closePosition=True,

        workingType="MARK_PRICE"
    )

    client.futures_create_order(

        symbol=symbol,

        side=close_side,

        type="TRAILING_STOP_MARKET",

        callbackRate=TRAIL_ROI,

        quantity=qty,

        workingType="MARK_PRICE"
    )

    state.symbol = symbol
    state.side = side
    state.entry_price = entry
    state.qty = qty

    state.tp_price = tp
    state.sl_price = sl
    state.trailing = TRAIL_ROI

    return order
