class GenericMACrossStrategy:
    def __init__(self, brokerage, symbol, short_ma_analyzer, long_ma_analyzer):
        self.brokerage = brokerage
        self.symbol = symbol
        self.short_ma_analyzer = short_ma_analyzer
        self.long_ma_analyzer = long_ma_analyzer
        self.state = "tracking"

    def make_decision(self):
        for a in [self.short_ma_analyzer, self.long_ma_analyzer]:
            if len(a.averages) < 2 or a.averages[-2] is None:
                return

        short_val = self.short_ma_analyzer.averages[-1]
        long_val = self.long_ma_analyzer.averages[-1]

        if self.state == "buy" and short_val > long_val:
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
        elif self.state == "sell" and short_val < long_val:
            self.brokerage.sell_stock(self.symbol)
            self.state = "buy"
