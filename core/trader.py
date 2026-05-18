from core.exchange import client
from config import SYMBOL

def sync_position():

    positions = client.futures_position_information(
        symbol=SYMBOL
    )

    pos = positions[0]

    amt = float(pos["positionAmt"])

    if amt > 0:
        return "LONG"

    if amt < 0:
        return "SHORT"

    return "NONE"
