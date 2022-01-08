# Buys on the first quote and never sells
class TrivialStrategy:
    def __init__(self, brokerage, symbol):
        self.brokerage = brokerage
        self.symbol = symbol
        self.state = "tracking"

    def process_quote(self, quote):
        pass

    def make_decision(self):
        if self.state == "buy":
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
