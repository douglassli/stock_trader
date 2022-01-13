from utils.utils import get_logger


class PSARCrossStrategy:
    def __init__(self, brokerage, symbol, psar_analyzer, short_ma_analyzer, long_ma_analyzer):
        self.brokerage = brokerage
        self.symbol = symbol
        self.psar_analyzer = psar_analyzer
        self.short_ma_analyzer = short_ma_analyzer
        self.long_ma_analyzer = long_ma_analyzer
        self.state = "tracking"

    def update_analyzer_vals(self, period_aggregator):
        self.psar_analyzer.update_values(period_aggregator)
        self.short_ma_analyzer.update_values(period_aggregator)
        self.long_ma_analyzer.update_values(period_aggregator)

    def have_enough_info(self):
        if len(self.psar_analyzer.sars) == 0:
            return False

        for a in [self.short_ma_analyzer, self.long_ma_analyzer]:
            if len(a.averages) < 2 or a.averages[-2] is None:
                return False

        return True

    def make_decision(self):
        if self.state == "tracking":
            return

        if not self.have_enough_info():
            return

        short_val = self.short_ma_analyzer.averages[-1]
        long_val = self.long_ma_analyzer.averages[-1]

        if self.state == "buy" and self.psar_analyzer.is_rising and short_val > long_val:
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
        elif self.state == "sell" and not self.psar_analyzer.is_rising and short_val < long_val:
            self.brokerage.sell_stock(self.symbol)
            self.state = "buy"

    def generate_signal(self):
        if not self.have_enough_info():
            return

        short_val = self.short_ma_analyzer.averages[-1]
        long_val = self.long_ma_analyzer.averages[-1]

        if self.psar_analyzer.is_rising and short_val > long_val:
            return "buy"
        elif not self.psar_analyzer.is_rising and short_val < long_val:
            return "sell"
