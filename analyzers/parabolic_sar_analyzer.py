from analyzers.base_analyzer import BaseAnalyzer
from utils.constants import PSAR_TRACE


# Parabolic Stop And Reverse Analyzer
class PSARAnalyzer(BaseAnalyzer):
    def __init__(self, step=0.02, max_step=0.2):
        self.accel_factor = 0.02
        self.cur_accel_factor = self.accel_factor
        self.step = step
        self.max_step = max_step
        self.wait_length = 5
        self.high_ep = None
        self.low_ep = None
        self.is_rising = False
        self.sars = []

    def name(self):
        return f"psar_{self.accel_factor}_{self.max_step}"

    def trace_type(self):
        return PSAR_TRACE

    def get_last_value(self):
        if len(self.sars) == 0:
            return None
        else:
            return self.sars[-1]

    # See below for math
    # https://school.stockcharts.com/doku.php?id=technical_indicators:parabolic_sar
    def update_values(self, period_aggregator):
        if period_aggregator.num_periods() < self.wait_length:
            return
        elif len(self.sars) == 0:
            last_two_closes = period_aggregator.get_last_values("close", 2)
            self.is_rising = last_two_closes[-1] > last_two_closes[-2]

            self.high_ep = max(period_aggregator.get_last_values("high", self.wait_length))
            self.low_ep = max(period_aggregator.get_last_values("low", self.wait_length))

            start_sars = self.low_ep if self.is_rising else self.high_ep
            self.sars.append(start_sars)

        last_low = period_aggregator.get_last_value("low")
        last_high = period_aggregator.get_last_value("high")
        flip = (self.is_rising and last_low < self.sars[-1]) or \
               (not self.is_rising and last_high > self.sars[-1])

        if flip:
            self.is_rising = not self.is_rising
            if self.is_rising:
                return_val = min(self.low_ep, last_low)
            else:
                return_val = max(self.high_ep, last_high)

            self.low_ep = last_low
            self.high_ep = last_high
            self.cur_accel_factor = self.accel_factor
            cur_sars = return_val
        elif self.is_rising:
            if last_high > self.high_ep:
                self.increment_accel()
                self.high_ep = last_high
            self.low_ep = min(self.low_ep, last_low)

            cur_sars = self.sars[-1] + (self.cur_accel_factor * (self.high_ep - self.sars[-1]))
        else:
            if last_low < self.low_ep:
                self.increment_accel()
                self.low_ep = last_low
            self.high_ep = max(self.high_ep, last_high)

            cur_sars = self.sars[-1] - (self.cur_accel_factor * (self.sars[-1] - self.low_ep))

        self.sars.append(cur_sars)

    def increment_accel(self):
        if self.cur_accel_factor < self.max_step:
            self.cur_accel_factor += self.step
