from math import exp
from analyzers.base_analyzer import BaseAnalyzer


# Arnaud Legoux Moving Average Analyzer
class ALMAAnalyzer(BaseAnalyzer):
    def __init__(self, period_aggregator, length=10, sigma=6, offset=0.85):
        super().__init__(period_aggregator)
        self.length = length  # Number of periods to average
        self.sigma = sigma
        self.offset = offset
        self.averages = []

    # See below for math
    # https://www.prorealcode.com/prorealtime-indicators/alma-arnaud-legoux-moving-average/
    def update_values(self):
        if self.period_aggregator.num_periods() >= self.length:
            closes = self.period_aggregator.get_last_closes(self.length)

            m = (self.offset * (self.length - 1))
            s = self.length / self.sigma

            wtd_sum = 0
            cum_wt = 0

            for k in range(self.length):
                wtd = exp(-((k - m) * (k - m)) / (2 * s * s))
                wtd_sum += wtd * closes[-(self.length - k)]
                cum_wt += wtd

            alma = wtd_sum / cum_wt

            self.averages.append(alma)
