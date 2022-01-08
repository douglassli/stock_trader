class BaseAnalyzer:
    def __init__(self, period_aggregator):
        self.period_aggregator = period_aggregator

    def update_values(self):
        raise NotImplementedError

    def update_stats(self, quote):
        finished_period = self.period_aggregator.process_quote(quote)
        if finished_period:
            self.update_values()

    def process_quote(self, quote):
        self.update_stats(quote)
