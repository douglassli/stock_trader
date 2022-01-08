class PSARSlopeStrategy:
    def __init__(self, brokerage, symbol, psar_analyzer, ma_analyzer):
        self.brokerage = brokerage
        self.symbol = symbol
        self.psar_analyzer = psar_analyzer
        self.ma_analyzer = ma_analyzer
        self.state = "tracking"

    def process_quote(self, quote):
        self.psar_analyzer.process_quote(quote)
        self.make_decision()

    def make_decision(self):
        if len(self.psar_analyzer.sars) == 0 or \
                len(self.ma_analyzer.averages) < 2 or \
                self.ma_analyzer.averages[-2] is None:
            return

        cur_slope = self.ma_analyzer.averages[-1] - self.ma_analyzer.averages[-2]

        if self.state == "buy" and self.psar_analyzer.is_rising and cur_slope > 0:
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
        elif self.state == "sell" and not self.psar_analyzer.is_rising and cur_slope < 0:
            self.brokerage.sell_stock(self.symbol)
            self.state = "buy"
