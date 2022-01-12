from utils.utils import get_logger, get_alpaca_stream
from datetime import datetime
from utils.quote import Quote


class StreamListener:
    def __init__(self, account_type, signal_queue, trade_update_queue, strategies, period_aggregators):
        self.account_type = account_type
        self.signal_queue = signal_queue
        self.trade_update_queue = trade_update_queue
        self.strategies = strategies
        self.period_aggregators = period_aggregators
        self.quote_counts = {}
        self.period_counts = {}
        self.logger = get_logger("stream_listener")

    async def trade_update_callback(self, trade_update):
        self.trade_update_queue.put(trade_update._raw)

    def get_quote_call_back(self, symbol):
        async def quote_callback(q):
            self.process_quote(q, symbol)

        return quote_callback

    def process_quote(self, api_q, symbol):
        self.quote_counts[symbol] = self.quote_counts.get(symbol, 0) + 1

        if symbol not in self.period_counts:
            self.period_counts[symbol] = 0

        dt = datetime.utcfromtimestamp(api_q.timestamp.timestamp())
        quote = Quote(dt, float(api_q.ask_price), int(api_q.ask_size), float(api_q.bid_price), int(api_q.bid_size))

        strategy = self.strategies[symbol]
        period_aggregator = self.period_aggregators[symbol]

        finished_period = period_aggregator.process_quote(quote)
        if finished_period:
            self.period_counts[symbol] = self.period_counts.get(symbol, 0) + 1
            self.logger.info(f"FINISHED {symbol} PERIOD {self.period_counts[symbol]}, {self.quote_counts[symbol]} QUOTES")
            self.quote_counts[symbol] = 0
            strategy.update_analyzer_vals(period_aggregator)

            signal = strategy.generate_signal()  # TODO
            if signal is not None:
                signal_message = {
                    "symbol": symbol,
                    "type": signal,
                    "strength": None,  # TODO
                    "timestamp": dt
                }
                self.signal_queue.put(signal_message)

    def start(self):
        stream = get_alpaca_stream(self.account_type)
        stream.subscribe_trade_updates(self.trade_update_callback)
        for symbol in self.strategies.keys():
            stream.subscribe_quotes(self.get_quote_call_back(symbol), symbol)
        stream.run()


def start_listener_process(account_type, signal_queue, trade_update_queue, strategies, period_aggregators):
    stream_listener = StreamListener(account_type, signal_queue, trade_update_queue, strategies, period_aggregators)
    stream_listener.start()
