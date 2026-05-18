from core.client import client


def get_open_position():

    positions = client.futures_position_information()

    for p in positions:

        amt = float(p["positionAmt"])

        if abs(amt) > 0:
            return p

    return None
