class BaseAnalyzer:
    def update_values(self, period_aggregator):
        raise NotImplementedError

    def name(self):
        raise NotImplementedError

    def trace_type(self):
        raise NotImplementedError

    def get_last_value(self):
        raise NotImplementedError
