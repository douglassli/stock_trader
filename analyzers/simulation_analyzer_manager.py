class SimulationAnalyzerManager:
    def __init__(self, analyzers, period_aggregators):
        # {
        #    window_size: [list analyzers]
        # }
        self.analyzers = analyzers
        # {
        #    window_size: aggregator
        # }
        self.period_aggregators = period_aggregators

    def process_quote(self, quote):
        for window_size, per_agg in self.period_aggregators.items():
            finished_period = per_agg.process_quote(quote)
            if finished_period:
                for analyzer in self.analyzers[window_size]:
                    analyzer.update_values(per_agg)

    def process_period(self, period):
        per_agg = self.period_aggregators[period.timeframe]
        per_agg.process_period(period)

        for analyzer in self.analyzers[period.timeframe]:
            analyzer.update_values(per_agg)

    def get_period_sizes(self):
        return self.period_aggregators.keys()
