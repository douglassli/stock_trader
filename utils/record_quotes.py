from datetime import datetime
from csv import DictWriter
from time import time
from utils.constants import PAPER
from utils.utils import get_alpaca_rest_api

FMT_STR = '%Y-%m-%dT%H:%M:%S'


def format_datetime(date_time):
    return date_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def record_quotes(symbol, start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, FMT_STR)
    end = datetime.strptime(end_date_str, FMT_STR)
    hist_quotes = rest_api.get_quotes(symbol, format_datetime(start), format_datetime(end))

    rows = []
    for q in hist_quotes:
        rows.append({
            't': str(q.t),
            'ap': str(q.ap),
            'as': str(q._raw['as']),
            'bp': str(q.bp),
            'bs': str(q.bs)
        })

    filename = f"data_sets/{symbol}_{start_date_str}_{end_date_str}.csv"
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['t', 'ap', 'as', 'bp', 'bs']
        writer = DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerows(rows)


def get_entire_month(symbol, api):
    start = datetime.strptime("2021-11-30T21:00:00", FMT_STR)
    end = datetime.strptime("2021-12-31T21:00:00", FMT_STR)

    print("Retreiving quotes from API...")
    start_time = time()
    hist_quotes = api.get_quotes(symbol, format_datetime(start), format_datetime(end))
    api_time = time() - start_time
    print(f"Found {len(hist_quotes)} quotes in {api_time:.2f} seconds")

    rows = []
    for q in hist_quotes:
        rows.append({
            't': str(q.t),
            'ap': str(q.ap),
            'as': str(q._raw['as']),
            'bp': str(q.bp),
            'bs': str(q.bs)
        })

    print("Writing rows...")

    start_time = time()
    filename = f"data_sets/2021-12/AAPL/entire_raw/AAPL_2021-11-31T21:00:00_2021-12-31T21:00:00.csv"
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['t', 'ap', 'as', 'bp', 'bs']
        writer = DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerows(rows)

    write_time = time() - start_time
    print(f"Found {len(hist_quotes)} quotes in {write_time:.2f} seconds")


if __name__ == '__main__':
    rest_api = get_alpaca_rest_api(PAPER)

    get_entire_month("AAPL", rest_api)



