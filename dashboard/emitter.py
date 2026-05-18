from extensions import socketio

from core.state import state

from trading.risk_manager import get_balance

from trading.position_manager import (
    get_open_position
)


def emit_dashboard(data, screener):

    pnl = 0

    pos = get_open_position()

    if pos:
        pnl = float(pos["unRealizedProfit"])

    payload = {

        "symbol": data["symbol"],

        "signal": data["signal"],

        "price": data["price"],

        "position": state.side,

        "entry": state.entry_price,

        "tp_price": state.tp_price,

        "sl_price": state.sl_price,

        "trail": state.trailing,

        "pnl": pnl,

        "balance": get_balance(),

        "rsi": data["rsi"],

        "mtf": data["mtf"],

        "mtf_bullish": data["mtf_bullish"],

        "mtf_bearish": data["mtf_bearish"],

        "trade_count": state.trade_count,

        "screener": screener
    }

    socketio.emit(
        "update",
        payload
    )
