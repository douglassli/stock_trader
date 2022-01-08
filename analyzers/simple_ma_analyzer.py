from analyzers.base_analyzer import BaseAnalyzer


# Simple Moving Average Analyzer
class SMAAnalyzer(BaseAnalyzer):
    def __init__(self, period_aggregator, length=10):
        super().__init__(period_aggregator)
        self.length = length  # Number of periods to average
        self.averages = []

    def update_values(self):
        if self.period_aggregator.num_periods() >= self.length:
            period_closes = self.period_aggregator.get_last_closes(self.length)
            avg = sum(period_closes) / self.length
            self.averages.append(avg)
