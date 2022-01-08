from analyzers.base_analyzer import BaseAnalyzer


# Simple Moving Average Analyzer
class SMAAnalyzer(BaseAnalyzer):
    def __init__(self, length=10):
        self.length = length  # Number of periods to average
        self.averages = []

    def update_values(self, period_aggregator):
        if period_aggregator.num_periods() >= self.length:
            period_closes = period_aggregator.get_last_closes(self.length)
            avg = sum(period_closes) / self.length
            self.averages.append(avg)
