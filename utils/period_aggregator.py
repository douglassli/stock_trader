from datetime import datetime, timedelta


class Period:
    def __init__(self, timeframe, start_time, end_time, open, close, high, low, volume):
        self.timeframe = timeframe
        self.start_time = start_time
        self.end_time = end_time
        self.open = open
        self.close = close
        self.high = high
        self.low = low
        self.volume = volume
        self.hl2 = None
        self.oc2 = None
        self.hlc3 = None
        self.ohlc4 = None
        self.hlcc4 = None

    def close_period(self):
        self.hl2 = (self.high + self.low) / 2
        self.oc2 = (self.open + self.close) / 2
        self.hlc3 = (self.high + self.low + self.close) / 3
        self.ohlc4 = (self.open + self.high + self.low + self.close) / 4
        self.hlcc4 = (self.high + self.low + self.close + self.close) / 4

    def get_value(self, source):
        return getattr(self, source)


class PeriodAggregator:
    def __init__(self, timeframe):
        self.timeframe = timeframe
        self.periods = []
        self.cur_period = None

    def parse_timestamp(self, quote):
        try:
            pieces = quote.t.split('.')
            if len(pieces) > 1:
                pieces[1] = pieces[1][:6].replace('Z', '')
                dt = datetime.strptime('.'.join(pieces), '%Y-%m-%dT%H:%M:%S.%f')
            else:
                dt = datetime.strptime(pieces[0].replace('Z', ''), '%Y-%m-%dT%H:%M:%S')

            return dt
        except Exception as e:
            print(quote.t)
            raise e

    def initialize_period(self, quote, parsed_ts):
        return Period(
                self.timeframe,
                parsed_ts,
                parsed_ts + timedelta(seconds=self.timeframe),
                quote.bp,  # TODO current aggregated data sets don't support opens
                quote.bp,
                quote.max_bp if hasattr(quote, "max_bp") else quote.bp,
                quote.min_bp if hasattr(quote, "min_bp") else quote.bp,
                quote.bs
            )

    def update_cur_period(self, quote):
        self.cur_period.close = quote.bp

        low_val = quote.min_bp if hasattr(quote, "min_bp") else quote.bp
        self.cur_period.low = min(self.cur_period.low, low_val)

        high_val = quote.max_bp if hasattr(quote, "max_bp") else quote.bp
        self.cur_period.high = max(self.cur_period.high, high_val)

        self.cur_period.volume += quote.bs

    def process_quote(self, quote):
        # dt = self.parse_timestamp(quote)
        dt = quote.t

        if self.cur_period is None:
            self.cur_period = self.initialize_period(quote, dt)
        elif dt > self.cur_period.end_time:
            self.cur_period.close_period()
            self.periods.append(self.cur_period)
            self.cur_period = self.initialize_period(quote, dt)
            return True
        else:
            self.update_cur_period(quote)

        return False

    def process_period(self, period):
        period.close_period()
        self.periods.append(period)

    def num_periods(self):
        return len(self.periods)

    def get_last_value(self, source):
        return self.periods[-1].get_value(source)

    def get_last_values(self, source, num_values):
        return [p.get_value(source) for p in self.periods[-num_values:]]
