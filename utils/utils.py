from utils.constants import *
import os
from alpaca_trade_api.rest import REST
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
import logging
import sys
from datetime import datetime
from queue import Empty
from csv import DictReader
from utils.period_aggregator import Period
from utils.quote import Quote


def get_logger(name, log_file_name=f"logs/trade_manager.log"):
    log = logging.getLogger(name)
    if len(log.handlers) == 0:
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        fh = logging.FileHandler(log_file_name, "a")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        log.addHandler(ch)
        log.addHandler(fh)
    return log


def get_credentials(account_type):
    if account_type == PAPER:
        key = os.environ[PAPER_KEY_ENV_VAR]
        secret = os.environ[PAPER_SECRET_ENV_VAR]
        return key, secret, PAPER_ENDPOINT
    elif account_type == LIVE:
        key = os.environ[LIVE_KEY_ENV_VAR]
        secret = os.environ[LIVE_SECRET_ENV_VAR]
        return key, secret, LIVE_ENDPOINT
    else:
        raise ValueError(f"Invalid account type: {account_type}")


def get_alpaca_stream(account_type):
    key, secret, endpoint = get_credentials(account_type)
    return Stream(key, secret, base_url=URL(endpoint), data_feed=DATA_FEED)


def get_alpaca_rest_api(account_type):
    key, secret, endpoint = get_credentials(account_type)
    return REST(key_id=key, secret_key=secret, base_url=URL(endpoint))


def format_datetime(date_time):
    return date_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp(ts):
    try:
        pieces = ts.split('.')
        if len(pieces) > 1:
            pieces[1] = pieces[1][:6].replace('Z', '')
            dt = datetime.strptime('.'.join(pieces), '%Y-%m-%dT%H:%M:%S.%f')
        else:
            dt = datetime.strptime(pieces[0].replace('Z', ''), '%Y-%m-%dT%H:%M:%S')

        return dt
    except Exception as e:
        print(ts)
        raise e


def get_queue_items(queue):
    while True:
        try:
            item = queue.get_nowait()
            yield item
        except Empty:
            return


def quotes_from_file(filename):
    out = []
    with open(filename, newline='') as csvfile:
        reader = DictReader(csvfile, fieldnames=['t', 'ap', 'as', 'bp', 'bs'])
        for row in reader:
            dt = parse_timestamp(row['t'])
            q = Quote(dt, float(row['ap']), int(row['as']), float(row['bp']), int(row['bs']))
            out.append(q)

    return out


def periods_from_file(filename):
    out = []
    with open(filename, newline='') as csvfile:
        reader = DictReader(csvfile, fieldnames=['timeframe', 'start_time', 'end_time', 'open', 'close', 'high', 'low', 'volume'])
        next(reader)
        for row in reader:
            start_dt = parse_timestamp(row['start_time'])
            end_dt = parse_timestamp(row['end_time'])
            p = Period(int(row['timeframe']),
                       start_dt,
                       end_dt,
                       float(row['open']),
                       float(row['close']),
                       float(row['high']),
                       float(row['low']),
                       int(row['volume'])
                       )
            out.append(p)

    return out
