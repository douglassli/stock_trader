from utils.utils import get_logger


class StreamListener:
    def __init__(self, stream, indicator_queue, trade_update_queue):
        self.stream = stream
        self.indicator_queue = indicator_queue
        self.trade_update_queue = trade_update_queue
        self.strategies = {}
        self.quote_counts = {}
        self.period_counts = {}
        self.logger = get_logger("stream_listener")

    def trade_update_callback(self, tu):
        pass

    def get_quote_call_back(self, symbol):
        async def quote_callback(q):
            self.process_quote(q, symbol)

        return quote_callback

    def process_quote(self, api_q, symbol):
        if symbol not in self.quote_counts:
            self.quote_counts[symbol] = 0

        if symbol not in self.per_counts:
            self.per_counts[symbol] = 0
        self.quote_counts[symbol] += 1

        # dt = parse_timestamp(api_q.timestamp)
        dt = datetime.utcfromtimestamp(api_q.timestamp.timestamp())
        quote = Quote(dt, float(api_q.ask_price), int(api_q.ask_size), float(api_q.bid_price), int(api_q.bid_size))

        strategy = self.strategies[symbol]
        period_aggregator = self.per_aggs[symbol]

        if strategy.state == "tracking" and dt.time() >= time(hour=14, minute=30):
            strategy.state = "buy"

        finished_period = period_aggregator.process_quote(quote)
        if finished_period:
            self.per_counts[symbol] += 1
            self.logger.info(f"FINISHED {symbol} PERIOD {self.per_counts[symbol]}, {self.quote_counts[symbol]} QUOTES")
            self.quote_counts[symbol] = 0
            strategy.update_analyzer_vals()

            try:
                old_state = strategy.state
                strategy.make_decision()
                self.logger.debug(f"PSAR MA Cross {symbol} made decision {old_state} -> {strategy.state}")
            except TooManyPositionsError:
                pass

    def start(self):
        self.stream.subscribe_trade_updates(self.trade_update_callback)
        self.stream.run()
