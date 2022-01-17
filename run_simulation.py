from analyzers.weighted_volume_ma_analyzer import VWMAAnalyzer
from brokerages.simulated_brokerage import SimulatedBrokerage
from datetime import datetime, time
from utils.utils import format_datetime, get_alpaca_rest_api, quotes_from_file, periods_from_file
from utils.constants import PAPER
from utils.period_aggregator import PeriodAggregator, Period
from strategies.trivial_strategy import TrivialStrategy
from strategies.generic_ma_crossover_strategy import GenericMACrossStrategy
from strategies.generic_ma_slope_strategy import GenericSlopeStrategy
from strategies.macd_crossover_strategy import MACDCrossStrategy
from strategies.psar_strategy import PSARStrategy
from strategies.psar_ma_cross_strategy import PSARCrossStrategy
from analyzers.least_squares_ma_analyzer import LSMAAnalyzer
from analyzers.exponential_ma_analyzer import EMAAnalyzer
from analyzers.simple_ma_analyzer import SMAAnalyzer
from analyzers.macd_analyzer import MACDAnalyzer
from analyzers.arnaud_legoux_ma_analyzer import ALMAAnalyzer
from analyzers.parabolic_sar_analyzer import PSARAnalyzer
from analyzers.simulation_analyzer_manager import SimulationAnalyzerManager
import logging
from csv import DictWriter
from tqdm import tqdm
from pathlib import Path


class Quote:
    def __init__(self, t, ap, as_, bp, bs):
        self.t = t
        self.ap = ap
        self.as_ = as_
        self.bp = bp
        self.bs = bs


def quotes_from_api(symb, start_date_str, end_date_str):
    rest_api = get_alpaca_rest_api(PAPER)

    # UTC timestamps
    start = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M:%S')
    end = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
    return rest_api.get_quotes(symb, format_datetime(start), format_datetime(end))


def generate_generic_ma_slope_strats(symbol, init_cash, ma_analyzer_class, strat_prefix):
    strategies = {}
    analyzers = {}
    window_sizes = [180, 120, 60, 30, 15, 10, 5]
    roll_lengths = [5, 10, 15, 20, 25, 30, 35, 40, 45]
    aggregators = {n: PeriodAggregator(n) for n in window_sizes}

    for window_size in window_sizes:
        for roll_length in roll_lengths:
            name = f"{strat_prefix}_slope_{window_size}_{roll_length}"
            analyzer = ma_analyzer_class(roll_length)
            analyzers[(window_size, roll_length)] = analyzer
            strategies[name] = GenericSlopeStrategy(SimulatedBrokerage(init_cash), symbol, analyzer)

    sim_analyzers = {}
    for k, a in analyzers.items():
        window = k[0]
        if window not in sim_analyzers:
            sim_analyzers[window] = []

        sim_analyzers[window].append(a)

    return strategies, analyzers, SimulationAnalyzerManager(sim_analyzers, aggregators)


def generate_sma_slope_strats(symbol, init_cash):
    return generate_generic_ma_slope_strats(symbol, init_cash, SMAAnalyzer, "sma")


def generate_lsma_slope_strats(symbol, init_cash):
    return generate_generic_ma_slope_strats(symbol, init_cash, LSMAAnalyzer, "lsma")


def generate_ema_slope_strats(symbol, init_cash):
    return generate_generic_ma_slope_strats(symbol, init_cash, EMAAnalyzer, "ema")


def generate_vwma_slope_strats(symbol, init_cash):
    return generate_generic_ma_slope_strats(symbol, init_cash, VWMAAnalyzer, "vwma")


def generate_alma_slope_strats(symbol, init_cash):
    return generate_generic_ma_slope_strats(symbol, init_cash, ALMAAnalyzer, "alma")


def generate_generic_ma_crossing_strats(symbol, init_cash, ma_analyzer_class, strat_prefix):
    strategies = {}
    analyzers = {}
    window_sizes = [180, 120, 60, 30, 15, 10, 5]
    roll_lengths = [5, 10, 15, 20, 25, 30, 35, 40, 45]
    length_pairs = {(a, b) for a in roll_lengths for b in roll_lengths if a < b}
    aggregators = {n: PeriodAggregator(n) for n in window_sizes}

    for window_size in window_sizes:
        for pair in length_pairs:
            name = f"{strat_prefix}_cross_{window_size}_{pair[0]}_{pair[1]}"
            if (window_size, pair[0]) not in analyzers:
                analyzers[(window_size, pair[0])] = ma_analyzer_class(pair[0])

            if (window_size, pair[1]) not in analyzers:
                analyzers[(window_size, pair[1])] = ma_analyzer_class(pair[1])

            strategy = GenericMACrossStrategy(
                SimulatedBrokerage(init_cash),
                symbol,
                analyzers[(window_size, pair[0])],
                analyzers[(window_size, pair[1])]
            )
            strategies[name] = strategy

    sim_analyzers = {}
    for k, a in analyzers.items():
        window = k[0]
        if window not in sim_analyzers:
            sim_analyzers[window] = []

        sim_analyzers[window].append(a)

    return strategies, analyzers, SimulationAnalyzerManager(sim_analyzers, aggregators)


def generate_sma_crossing_strats(symbol, init_cash):
    return generate_generic_ma_crossing_strats(symbol, init_cash, SMAAnalyzer, "sma")


def generate_lsma_crossing_strats(symbol, init_cash):
    return generate_generic_ma_crossing_strats(symbol, init_cash, LSMAAnalyzer, "lsma")


def generate_ema_crossing_strats(symbol, init_cash):
    return generate_generic_ma_crossing_strats(symbol, init_cash, EMAAnalyzer, "ema")


def generate_vwma_crossing_strats(symbol, init_cash):
    return generate_generic_ma_crossing_strats(symbol, init_cash, VWMAAnalyzer, "vwma")


def generate_alma_crossing_strats(symbol, init_cash):
    return generate_generic_ma_crossing_strats(symbol, init_cash, ALMAAnalyzer, "alma")


def generate_macd_cross_strats(symbol, init_cash):
    strategies = {}
    analyzers = {}
    window_sizes = [180, 120, 60, 30, 15, 10, 5]
    lengths = [5, 10, 15, 20, 25, 30, 35, 40, 45]
    length_triples = {(a, b, c) for a in lengths for b in lengths for c in lengths if a < b < c}
    aggregators = {n: PeriodAggregator(n) for n in window_sizes}

    for window_size in window_sizes:
        for triplet in length_triples:
            name = f"macd_cross_{window_size}_{triplet[1]}_{triplet[2]}_{triplet[0]}"
            analyzer = MACDAnalyzer(aggregators[window_size], triplet[1], triplet[2], triplet[0])
            analyzers[(window_size, triplet[1], triplet[2], triplet[0])] = analyzer

            strategy = MACDCrossStrategy(
                SimulatedBrokerage(init_cash),
                symbol,
                analyzer
            )
            strategies[name] = strategy

    sim_analyzers = {}
    for k, a in analyzers.items():
        window = k[0]
        if window not in sim_analyzers:
            sim_analyzers[window] = []

        sim_analyzers[window].append(a)

    return strategies, analyzers, SimulationAnalyzerManager(sim_analyzers, aggregators)


def generate_psar_strats(symbol, init_cash):
    strategies = {}
    analyzers = {}
    window_sizes = [180, 120, 60, 30, 15, 10, 5]
    step_sizes = [0.005, 0.01, 0.02, 0.03, 0.04, 0.05]
    max_steps = [0.1, 0.2, 0.3, 0.4, 0.5]
    aggregators = {n: PeriodAggregator(n) for n in window_sizes}

    for window_size in window_sizes:
        for step_size in step_sizes:
            for max_step in max_steps:
                name = f"psar_{window_size}_{step_size}_{max_step}"
                analyzer = PSARAnalyzer(step_size, max_step)
                analyzers[(window_size, name)] = analyzer

                strategy = PSARStrategy(
                    SimulatedBrokerage(init_cash),
                    symbol,
                    analyzer
                )
                strategies[name] = strategy

    sim_analyzers = {}
    for k, a in analyzers.items():
        window = k[0]
        if window not in sim_analyzers:
            sim_analyzers[window] = []

        sim_analyzers[window].append(a)

    return strategies, analyzers, SimulationAnalyzerManager(sim_analyzers, aggregators)


def generate_psar_ma_cross_strats(symbol, init_cash):
    strategies = {}
    analyzers = {}
    window_sizes = [240, 180]
    lengths = [25, 30, 35, 40]  # [5, 10, 15, 20, 25, 30, 35, 40, 45]
    step_sizes = [0.01, 0.02]  # [0.005, 0.01, 0.02, 0.03, 0.04, 0.05]
    max_steps = [0.1, 0.2]  # [0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.2, 0.3, 0.4, 0.5]
    sources = ["open", "close", "high", "low", "hl2", "hlc3", "ohlc4", "hlcc4"]
    length_pairs = {(a, b) for a in lengths for b in lengths if a < b}
    aggregators = {n: PeriodAggregator(n) for n in window_sizes}

    for window_size in window_sizes:
        for pair in length_pairs:
            for step_size in step_sizes:
                for max_step in max_steps:
                    for source in sources:
                        name = f"psar_ma_cross_{window_size}_{pair[0]}_{pair[1]}_{step_size}_{max_step}_{source}"

                        if (window_size, "ma", pair[0], source) not in analyzers:
                            analyzers[(window_size, "ma", pair[0], source)] = VWMAAnalyzer(pair[0], source=source)

                        if (window_size, "ma", pair[1], source) not in analyzers:
                            analyzers[(window_size, "ma", pair[1], source)] = VWMAAnalyzer(pair[1], source=source)

                        if (window_size, f"psar_{step_size}_{max_step}") not in analyzers:
                            analyzers[(window_size, f"psar_{step_size}_{max_step}")] = PSARAnalyzer(step_size, max_step)

                        strategy = PSARCrossStrategy(
                            SimulatedBrokerage(init_cash),
                            symbol,
                            analyzers[(window_size, f"psar_{step_size}_{max_step}")],
                            analyzers[(window_size, "ma", pair[0], source)],
                            analyzers[(window_size, "ma", pair[1], source)]
                        )
                        strategies[name] = strategy

    sim_analyzers = {}
    for k, a in analyzers.items():
        window = k[0]
        if window not in sim_analyzers:
            sim_analyzers[window] = []

        sim_analyzers[window].append(a)

    return strategies, analyzers, SimulationAnalyzerManager(sim_analyzers, aggregators)


def get_all_aapl_2021_12_dates():
    return [
        '2021-12-01',
        '2021-12-02',
        '2021-12-03',
        '2021-12-06',
        '2021-12-07',
        '2021-12-08',
        '2021-12-09',
        '2021-12-10',
        '2021-12-13',
        '2021-12-14',
        '2021-12-15',
        '2021-12-16',
        '2021-12-17',
        '2021-12-20',
        '2021-12-21',
        '2021-12-22',
        '2021-12-23',
        '2021-12-27',
        '2021-12-28',
        '2021-12-29',
        '2021-12-30'
    ]


def write_csv_dict(csv_file_name, fieldnames, dict_rows):
    with open(csv_file_name, 'w', newline='') as csvfile:
        writer = DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dict_rows)


def write_stats(out_stats, dates, record_trades):
    timestamp = datetime.now().isoformat()
    Path.mkdir(Path.joinpath(Path.cwd(), 'simulation_output', timestamp))

    profit_rows = []
    trade_count_rows = []
    for strategy_name, data in out_stats.items():
        profit_row = {"analyzer_name": strategy_name}
        trade_count_row = {"analyzer_name": strategy_name}

        prct_sum = 0.0
        trade_count_sum = 0
        for date, stats in data.items():
            profit_row[date] = f"{stats['profit_pct']:.3f}"
            trade_count_row[date] = stats['num_buys']
            prct_sum += stats['profit_pct']
            trade_count_sum += stats['num_buys']

            if record_trades and len(stats["trades"]) > 0:
                Path.mkdir(Path.joinpath(Path.cwd(), 'simulation_output', timestamp, "trades", strategy_name, date),
                           parents=True)
                file_name = f"simulation_output/{timestamp}/trades/{strategy_name}/{date}/trades.csv"
                write_csv_dict(file_name, stats["trades"][0].keys(), stats["trades"])

        profit_row["avg_prct_profit"] = f"{prct_sum / len(data):.3f}"
        trade_count_row["avg_trade_count"] = f"{trade_count_sum / len(data):.3f}"

        profit_rows.append(profit_row)
        trade_count_rows.append(trade_count_row)

    profit_filename = f"simulation_output/{timestamp}/profits.csv"
    trade_count_filename = f"simulation_output/{timestamp}/trade_counts.csv"
    base_field_names = ['analyzer_name'] + dates

    profit_rows.sort(key=lambda x: x['avg_prct_profit'], reverse=True)

    write_csv_dict(profit_filename, base_field_names + ['avg_prct_profit'], profit_rows)
    write_csv_dict(trade_count_filename, base_field_names + ['avg_trade_count'], trade_count_rows)


def run_simulation(symbol, data_source, dates, strategy_gen_function, record_trades, disable_logging, initial_cash):
    # {
    #   analyzer_name: {
    #     date: {
    #       "profit_pct": float,
    #       "num_buys": int,
    #       "num_sells": int,
    #       "trades": list
    #     }
    #   }
    # }
    out_stats = {}

    for date in dates:
        # input_file_name = f"data_sets/2021-12/{symbol}/{data_source}/AAPL_{date}T14:30:00_{date}T21:00:00.csv"
        input_file_name = f"data_sets/2021-12/{symbol}/{data_source}/AAPL_{date}_with_premarket.csv"
        print(f"Starting simulation for {input_file_name}")

        strategies = {
            "trivial": TrivialStrategy(SimulatedBrokerage(initial_cash), symbol)
        }

        additional_strats, analyzers, sim_analyzer_manager = strategy_gen_function(symbol, initial_cash)
        strategies.update(additional_strats)

        logging.getLogger('sim_broker').disabled = disable_logging

        hist_quotes = quotes_from_file(input_file_name)
        # hist_quotes = quotes_from_api('AAPL', '2021-12-17T14:30:00', '2021-12-17T21:00:00')

        for quote in tqdm(hist_quotes):
            # ts_time = datetime.strptime(quote.t.split('.')[0].replace('Z', ''), '%Y-%m-%dT%H:%M:%S').time()
            ts_time = quote.t

            if ts_time.time() >= time(hour=21):
                break

            # for analyzer in analyzers.values():
            #     analyzer.process_quote(quote)
            sim_analyzer_manager.process_quote(quote)

            for strategy in strategies.values():
                strategy.brokerage.update_value(symbol, quote.bp, quote.t)

                if ts_time.time() >= time(hour=14, minute=30) and strategy.state == "tracking":
                    strategy.state = "buy"

                strategy.make_decision()

        for name, strategy in strategies.items():
            if name not in out_stats:
                out_stats[name] = {}

            profit_percent = (float(strategy.brokerage.get_equity()) - float(initial_cash)) / float(initial_cash) * 100
            out_stats[name][date] = {
                "profit_pct": profit_percent,
                "num_buys": strategy.brokerage.num_buys,
                "num_sells": strategy.brokerage.num_sells,
                "trades": strategy.brokerage.trades
            }

    write_stats(out_stats, dates, record_trades)


def run_sim_from_periods(symbol, dates, strategy_gen_function, record_trades, disable_logging, initial_cash):
    out_stats = {}
    logging.getLogger('sim_broker').disabled = disable_logging

    for date in tqdm(dates):
        strategies = {
            "trivial": TrivialStrategy(SimulatedBrokerage(initial_cash), symbol)
        }

        additional_strats, analyzers, sim_analyzer_manager = strategy_gen_function(symbol, initial_cash)
        strategies.update(additional_strats)

        period_sizes = sim_analyzer_manager.get_period_sizes()

        for period_size in period_sizes:
            input_file_name = f"data_sets/2021-12/{symbol}/periods/{period_size}/{date}_periods_{period_size}.csv"

            periods = periods_from_file(input_file_name)

            for period in periods:
                if period.end_time.time() >= time(hour=21):
                    break

                sim_analyzer_manager.process_period(period)

                for strategy in strategies.values():
                    strategy.brokerage.update_value(symbol, period.close, period.end_time)

                    if period.end_time.time() >= time(hour=14, minute=30) and strategy.state == "tracking":
                        strategy.state = "buy"

                    strategy.make_decision()

            for name, strategy in strategies.items():
                if name not in out_stats:
                    out_stats[name] = {}

                profit_percent = (float(strategy.brokerage.get_equity()) - float(initial_cash)) / float(initial_cash) * 100
                out_stats[name][date] = {
                    "profit_pct": profit_percent,
                    "num_buys": strategy.brokerage.num_buys,
                    "num_sells": strategy.brokerage.num_sells,
                    "trades": strategy.brokerage.trades
                }

    write_stats(out_stats, dates, record_trades)


if __name__ == '__main__':
    run_sim_from_periods(
        symbol="AAPL",
        dates=get_all_aapl_2021_12_dates(),
        strategy_gen_function=generate_psar_ma_cross_strats,
        disable_logging=True,
        initial_cash="30000.00",
        record_trades=False
    )
