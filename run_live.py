from brokerages.brokerage import AlpacaBrokerage
from analyzers.weighted_volume_ma_analyzer import VWMAAnalyzer
from analyzers.parabolic_sar_analyzer import PSARAnalyzer
from strategies.psar_ma_cross_strategy import PSARCrossStrategy
from utils.period_aggregator import PeriodAggregator
from datetime import datetime
from utils.quote import Quote
from utils.utils import get_logger
from utils.constants import PAPER
from utils.utils import get_alpaca_stream, get_alpaca_rest_api
from datetime import time
from exceptions import TooManyPositionsError


class SingleStockLiveTrader:
    def __init__(self, brokerage, stream, tracking_symbols):
        self.brokerage = brokerage
        self.per_aggs = {}
        self.strategies = {}
        self.stream = stream
        self.tracking_symbols = tracking_symbols
        self.per_counts = {}
        self.quote_counts = {}
        self.logger = get_logger("live_trader")

    def generate_strategies(self):
        for symbol in self.tracking_symbols:
            period_agg = PeriodAggregator(240)
            vwma_fast = VWMAAnalyzer(period_agg, 25)
            vwma_slow = VWMAAnalyzer(period_agg, 30)
            psar = PSARAnalyzer(step=0.02, max_step=0.1)
            psar_ma_cross_strat = PSARCrossStrategy(self.brokerage, symbol, psar, vwma_fast, vwma_slow)

            self.strategies[symbol] = psar_ma_cross_strat
            self.per_aggs[symbol] = period_agg

    def get_call_back(self, symbol):
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

    def run(self):
        self.generate_strategies()

        for symbol in self.tracking_symbols:
            self.stream.subscribe_quotes(self.get_call_back(symbol), symbol)

        self.stream.run()


if __name__ == '__main__':
    stocks = ["AAPL", "TSLA", "DIS", "GE", "HD"]

    api = get_alpaca_rest_api(PAPER)
    live_brokerage = AlpacaBrokerage(api, num_stocks=1, dry_run=False)
    stock_stream = get_alpaca_stream(PAPER)
    live_trader = SingleStockLiveTrader(live_brokerage, stock_stream, stocks)

    live_trader.run()
