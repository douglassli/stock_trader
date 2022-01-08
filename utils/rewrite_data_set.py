from csv import DictReader, DictWriter
# from run_simulation import Quote
from datetime import datetime, timedelta
from tqdm import tqdm
from utils import parse_timestamp
from period_aggregator import PeriodAggregator
from pathlib import Path


class Quote:
    def __init__(self, t, ap, as_, bp, bs):
        self.t = t
        self.ap = ap
        self.as_ = as_
        self.bp = bp
        self.bs = bs
        self.min_bp = bp
        self.max_bp = bp
        self.min_ap = ap
        self.max_ap = ap
        self.num_quotes = 0


def get_timestamp(quote):
    return datetime.strptime(quote.t.split('.')[0].replace('Z', ''), '%Y-%m-%dT%H:%M:%S')


def quotes_from_file(filename):
    out = []
    with open(filename, newline='') as csvfile:
        reader = DictReader(csvfile, fieldnames=['t', 'ap', 'as', 'bp', 'bs'])
        for row in reader:
            dt = parse_timestamp(row['t'])
            q = Quote(dt, float(row['ap']), int(row['as']), float(row['bp']), int(row['bs']))
            out.append(q)

    return out


def write_csv_dict(csv_file_name, fieldnames, dict_rows):
    with open(csv_file_name, 'w', newline='') as csvfile:
        writer = DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dict_rows)


def format_datetime(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


def rewrite_into_periods(symbol, data_source, dates):
    period_sizes = [300, 240, 180, 120, 60, 30, 15, 10, 5]

    for date in dates:
        # input_file_name = f"data_sets/2021-12/{symbol}/{data_source}/AAPL_{date}T14:30:00_{date}T21:00:00.csv"
        input_file_name = f"../data_sets/2021-12/{symbol}/{data_source}/AAPL_{date}_with_premarket.csv"

        hist_quotes = quotes_from_file(input_file_name)
        period_aggs = {ps: PeriodAggregator(ps) for ps in period_sizes}

        for quote in tqdm(hist_quotes):
            for per_agg in period_aggs.values():
                per_agg.process_quote(quote)

        for size, per_agg in period_aggs.items():
            per_agg.cur_period.close_period()
            per_agg._periods.append(per_agg.cur_period)

            rows = []
            for period in per_agg._periods:
                rows.append({
                    "timeframe": size,
                    "start_time": format_datetime(period.start_time),
                    "end_time": format_datetime(period.end_time),
                    "open": period.open,
                    "close": period.close,
                    "high": period.high,
                    "low": period.low,
                    "volume": period.volume
                })

            Path.mkdir(Path.joinpath(Path.cwd(), '..', 'data_sets', '2021-12', symbol, 'periods', str(size)),
                       parents=True, exist_ok=True)
            file_name = f"../data_sets/2021-12/{symbol}/periods/{str(size)}/{date}_periods_{size}.csv"
            headers = rows[0].keys()
            write_csv_dict(file_name, headers, rows)


if __name__ == '__main__':
    dates = [
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
    SYMBOL = "AAPL"

    rewrite_into_periods(SYMBOL, "raw_w_pre", dates)
