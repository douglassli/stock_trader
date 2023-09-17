# Auto Stock Trader

This is a stock trading bot that will place trades using the Alpaca brokerage API.

It accepts custom strategies (found in `/strategies` directory) based on one or more metrics (found in `/analyzers` directory)

Accepts paper account credentials or live account credentials, see `get_credentials` function in `utils/utils.py`.

DISCLAIMER: This is a side project, I accept no responsibility if you use this to make trades in a live brokerage account and you lose all of your money. None of the implemented strategies made any money when I tested them in a paper account. USE AT YOUR OWN RISK! I highly recommend just playing with it in a paper account.
