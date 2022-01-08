class MACDCrossStrategy:
    def __init__(self, brokerage, symbol, macd_analyzer):
        self.brokerage = brokerage
        self.symbol = symbol
        self.macd_analyzer = macd_analyzer
        self.state = "tracking"

    def process_quote(self, quote):
        self.macd_analyzer.process_quote(quote)
        self.make_decision()

    def make_decision(self):
        if len(self.macd_analyzer.signal_values) < 2 or self.macd_analyzer.signal_values[-1] is None:
            return

        signal_val = self.macd_analyzer.signal_values[-1]
        macd_val = self.macd_analyzer.macd_values[-1]

        if self.state == "buy" and macd_val > signal_val:
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
        elif self.state == "sell" and macd_val < signal_val:
            self.brokerage.sell_stock(self.symbol)
            self.state = "buy"
