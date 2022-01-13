from live_trader.trade_manager import LiveTradeManager
from analyzers.weighted_volume_ma_analyzer import VWMAAnalyzer
from analyzers.parabolic_sar_analyzer import PSARAnalyzer
from strategies.psar_ma_cross_strategy import PSARCrossStrategy
from utils.period_aggregator import PeriodAggregator
from utils.constants import PAPER


def create_strats_and_aggs(symbols):
    strats = {}
    per_aggs = {}

    for symbol in symbols:
        period_agg = PeriodAggregator(240)
        vwma_fast = VWMAAnalyzer(25, source="hlc3")
        vwma_slow = VWMAAnalyzer(30, source="hlc3")
        psar = PSARAnalyzer(step=0.02, max_step=0.1)
        psar_ma_cross_strat = PSARCrossStrategy(None, symbol, psar, vwma_fast, vwma_slow)

        strats[symbol] = psar_ma_cross_strat
        per_aggs[symbol] = period_agg

    return strats, per_aggs


if __name__ == '__main__':
    tracking_symbols = [
        "AAPL",
        "TSLA",
        "DIS",
        "GE",
        "HD",
        "BRK.B",
        "JPM",
        "NFLX",
        "BA",
        "JNJ",
        "PFE",
        "T",
        "WMT",
        "XOM",
        "CVX",
        "CAT"
    ]

    live_trader = LiveTradeManager(
        PAPER,
        lambda: create_strats_and_aggs(tracking_symbols),
        max_positions=4,
        dry_run=False,
        allow_margin=False,
        allow_shorting=False
    )

    live_trader.start_trading()
