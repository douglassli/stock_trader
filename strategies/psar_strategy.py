class PSARStrategy:
    def __init__(self, brokerage, symbol, psar_analyzer):
        self.brokerage = brokerage
        self.symbol = symbol
        self.psar_analyzer = psar_analyzer
        self.state = "tracking"

    def process_quote(self, quote):
        self.psar_analyzer.process_quote(quote)
        self.make_decision()

    def make_decision(self):
        if len(self.psar_analyzer.sars) == 0:
            return

        if self.state == "buy" and self.psar_analyzer.is_rising:
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
        elif self.state == "sell" and not self.psar_analyzer.is_rising:
            self.brokerage.sell_stock(self.symbol)
            self.state = "buy"
