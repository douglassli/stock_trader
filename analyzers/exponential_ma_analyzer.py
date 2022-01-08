from analyzers.base_analyzer import BaseAnalyzer


# Exponential Moving Average Analyzer
class EMAAnalyzer(BaseAnalyzer):
    def __init__(self, period_aggregator, length=10, smoothing=2):
        super().__init__(period_aggregator)
        self.length = length  # Number of periods to average
        self.averages = []
        self.smoothing = smoothing
        self.multiplier = self.smoothing / (1 + self.length)

    # See below for math
    # https://www.investopedia.com/terms/e/ema.asp
    def update_values(self):
        if self.period_aggregator.num_periods() >= self.length:
            if len(self.averages) == 0:
                avg = sum(self.period_aggregator.get_last_closes(self.length)) / self.length
            else:
                avg = (self.period_aggregator.get_last_close() * self.multiplier) + (self.averages[-1] * (1 - self.multiplier))

            self.averages.append(avg)
