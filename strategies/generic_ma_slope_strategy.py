class GenericSlopeStrategy:
    def __init__(self, brokerage, symbol, ma_analyzer):
        self.brokerage = brokerage
        self.symbol = symbol
        self.ma_analyzer = ma_analyzer
        self.state = "tracking"

    def process_quote(self, quote):
        self.ma_analyzer.process_quote(quote)
        self.make_decision()

    def make_decision(self):
        if len(self.ma_analyzer.averages) < 2 or self.ma_analyzer.averages[-2] is None:
            return

        cur_slope = self.ma_analyzer.averages[-1] - self.ma_analyzer.averages[-2]

        if self.state == "buy" and cur_slope > 0:
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
        elif self.state == "sell" and cur_slope < 0:
            self.brokerage.sell_stock(self.symbol)
            self.state = "buy"
