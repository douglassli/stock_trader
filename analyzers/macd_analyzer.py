from analyzers.base_analyzer import BaseAnalyzer


# Exponential Moving Average Analyzer
class MACDAnalyzer(BaseAnalyzer):
    def __init__(self, fast_length=12, slow_length=26, signal_length=9, smoothing=2):
        self.slow_averages = []
        self.fast_averages = []
        self.macd_values = []
        self.signal_values = []
        self.smoothing = smoothing
        self.fast_length = fast_length
        self.slow_length = slow_length
        self.signal_length = signal_length
        self.per12_mult = self.smoothing / (1 + self.fast_length)
        self.per26_mult = self.smoothing / (1 + self.slow_length)
        self.signal_mult = self.smoothing / (1 + self.signal_length)

    def update_ema(self, data_source, averages, multiplier, length):
        if len(data_source) >= length:
            if averages[-1] is None:
                averages.append(sum(data_source[-length:]) / length)
            else:
                averages.append((data_source[-1] * multiplier) + (averages[-1] * (1 - multiplier)))
        else:
            averages.append(None)

    def update_values(self, period_aggregator):
        closes = period_aggregator.get_last_closes(self.slow_length)
        self.update_ema(closes, self.fast_averages, self.per12_mult, self.fast_length)
        self.update_ema(closes, self.slow_averages, self.per26_mult, self.slow_length)

        if self.fast_averages[-1] is not None and self.slow_averages[-1] is not None:
            self.macd_values.append(self.fast_averages[-1] - self.slow_averages[-1])

        self.update_ema(self.macd_values, self.signal_values, self.signal_mult, self.signal_length)
