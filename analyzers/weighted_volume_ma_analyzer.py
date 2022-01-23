from analyzers.base_analyzer import BaseAnalyzer
from utils.constants import MA_TRACE


# Volume Weighted Moving Average Analyzer
class VWMAAnalyzer(BaseAnalyzer):
    def __init__(self, length=10, source="close"):
        self.length = length  # Number of periods to average
        self.averages = []
        self.source = source

    def name(self):
        return f"vwma_{self.length}_{self.source}"

    def trace_type(self):
        return MA_TRACE

    def get_last_value(self):
        if len(self.averages) == 0:
            return None
        else:
            return self.averages[-1]

    # See below for math
    # https://www.tradingsetupsreview.com/volume-weighted-moving-average-vwma/
    def update_values(self, period_aggregator):
        if period_aggregator.num_periods() >= self.length:
            vol_close_sum = 0
            vol_sum = 0
            for i in range(self.length):
                index = i + 1
                period = period_aggregator.periods[-index]
                vol_close_sum += (period.get_value(self.source) * period.volume)
                vol_sum += period.volume

            avg = vol_close_sum / vol_sum
            self.averages.append(avg)
