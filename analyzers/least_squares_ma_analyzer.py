from analyzers.base_analyzer import BaseAnalyzer


# Least Squares Moving Average Analyzer
class LSMAAnalyzer(BaseAnalyzer):
    def __init__(self, length=10):
        self.length = length  # Number of periods to average
        self.averages = []

    # See below for math
    # https://botrader.org/useful/least-squares-moving-average-indicator-lsma/
    def update_values(self, period_aggregator):
        if period_aggregator.num_periods() >= self.length:
            closes = period_aggregator.get_last_closes(self.length)

            # sum_x_i         -> c
            # sum_y_i         -> d
            # sum_x_i_squared -> e
            # sum_x_i_y_i     -> f

            # System of equations:
            # ae + bc = f
            # ac + bn = d
            # n is self.length
            # Solve for a and b
            # a is line of best fit slope
            # b is price prediction

            # Solved equations:
            # a = (fn - cd) / (ne - c^2)
            # b = (d - ac) / n
            c = 0
            d = 0
            e = 0
            f = 0
            for i, close in enumerate(closes[::-1]):
                x_i = i + 1
                y_i = close
                x_i_squared = x_i * x_i
                x_i_y_i = x_i * y_i

                c += x_i
                d += y_i
                e += x_i_squared
                f += x_i_y_i

            n = self.length
            a = ((f * n) - (c * d)) / ((n * e) - (c * c))
            b = (d - (a * c)) / n

            self.averages.append(b)
