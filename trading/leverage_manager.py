from core.client import client
from core.config import (
    LEVERAGE,
    MARGIN_TYPE
)


def set_leverage(symbol):

    try:

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

    except:
        pass

    try:

        client.futures_change_margin_type(
            symbol=symbol,
            marginType=MARGIN_TYPE
        )

    except:
        pass
