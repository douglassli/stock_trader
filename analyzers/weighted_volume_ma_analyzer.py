from analyzers.base_analyzer import BaseAnalyzer


# Volume Weighted Moving Average Analyzer
class VWMAAnalyzer(BaseAnalyzer):
    def __init__(self, period_aggregator, length=10, source="close"):
        super().__init__(period_aggregator)
        self.length = length  # Number of periods to average
        self.averages = []
        self.source = source

    # See below for math
    # https://www.tradingsetupsreview.com/volume-weighted-moving-average-vwma/
    def update_values(self):
        if self.period_aggregator.num_periods() >= self.length:
            vol_close_sum = 0
            vol_sum = 0
            for i in range(self.length):
                index = i + 1
                period = self.period_aggregator.periods[-index]
                vol_close_sum += (period.get_value(self.source) * period.volume)
                vol_sum += period.volume

            avg = vol_close_sum / vol_sum
            self.averages.append(avg)
