from utils.utils import get_logger


class PSARCrossStrategy:
    def __init__(self, brokerage, symbol, psar_analyzer, short_ma_analyzer, long_ma_analyzer):
        self.brokerage = brokerage
        self.symbol = symbol
        self.psar_analyzer = psar_analyzer
        self.short_ma_analyzer = short_ma_analyzer
        self.long_ma_analyzer = long_ma_analyzer
        self.state = "tracking"
        self.logger = get_logger("psar_strat")

    def update_analyzer_vals(self, period_aggregator):
        self.psar_analyzer.update_values(period_aggregator)
        self.short_ma_analyzer.update_values(period_aggregator)
        self.long_ma_analyzer.update_values(period_aggregator)

    def make_decision(self):
        # old_state = self.state

        if self.state == "tracking":
            return

        if len(self.psar_analyzer.sars) == 0:
            return

        for a in [self.short_ma_analyzer, self.long_ma_analyzer]:
            if len(a.averages) < 2 or a.averages[-2] is None:
                return

        short_val = self.short_ma_analyzer.averages[-1]
        long_val = self.long_ma_analyzer.averages[-1]

        if self.state == "buy" and self.psar_analyzer.is_rising and short_val > long_val:
            self.brokerage.buy_stock(self.symbol)
            self.state = "sell"
        elif self.state == "sell" and not self.psar_analyzer.is_rising and short_val < long_val:
            self.brokerage.sell_stock(self.symbol)
            self.state = "buy"

        # self.logger.debug(f"PSAR MA Cross {self.symbol} made decision {old_state} -> {self.state}")
