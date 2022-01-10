from datetime import datetime
from utils.constants import *
import os
from alpaca_trade_api.rest import REST
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
import logging
import sys
from datetime import datetime
from queue import Empty


def get_logger(name, log_file_name=f"logs/{datetime.now().isoformat()}.log"):
    log = logging.getLogger(name)
    if len(log.handlers) == 0:
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        fh = logging.FileHandler(log_file_name, "w")
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
