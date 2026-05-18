class BotState:

    def __init__(self):

        self.symbol = None
        self.side = None

        self.entry_price = 0
        self.qty = 0

        self.tp_price = 0
        self.sl_price = 0
        self.trailing = 0

        self.pnl = 0

        self.trade_count = 0
        self.win = 0
        self.loss = 0

state = BotState()
