from strategy.screener import scan_market

from trading.order_manager import open_position

from trading.position_manager import (
    get_open_position
)

from trading.risk_manager import (
    calculate_qty,
    get_balance
)

from dashboard.emitter import emit_dashboard

from core.state import state

from extensions import socketio

from rich.console import Console

console = Console()


def run_bot():

    console.print(
        "[green]BOT STARTED[/green]"
    )

    while True:

        try:

            best, screener = scan_market()

            if best:

                emit_dashboard(
                    best,
                    screener
                )

            pos = get_open_position()

            if pos:

                socketio.sleep(10)
                continue

            if not best:

                socketio.sleep(10)
                continue

            if best["signal"] == "NONE":

                socketio.sleep(10)
                continue

            balance = get_balance()

            if balance <= 5:

                socketio.sleep(10)
                continue

            qty = calculate_qty(
                best["symbol"],
                best["price"]
            )

            order = open_position(

                best["symbol"],

                best["signal"],

                qty
            )

            if order:

                state.trade_count += 1

                console.print(
                    f"[green]ENTRY {best['signal']} {best['symbol']}[/green]"
                )

            socketio.sleep(15)

        except Exception as e:

            console.print(
                f"[red]{e}[/red]"
            )

            socketio.sleep(5)
socketio.run(
    app,
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 5000))
)
