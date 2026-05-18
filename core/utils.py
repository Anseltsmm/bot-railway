from core.exchange import client

def format_quantity(symbol, qty):

    info = client.futures_exchange_info()

    for s in info["symbols"]:

        if s["symbol"] == symbol:

            step = 0.001

            for f in s["filters"]:

                if f["filterType"] == "LOT_SIZE":
                    step = float(f["stepSize"])

            precision = len(
                str(step).split(".")[1].rstrip("0")
            )

            return round(qty, precision)

    return qty
