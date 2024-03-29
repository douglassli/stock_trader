from alpaca_trade_api.rest import APIError
from exceptions import MissingPositionError, PositionAlreadyExistsError, TooManyPositionsError, NotEnoughCashError
from utils.utils import get_logger, get_alpaca_rest_api


class AlpacaBrokerage:
    def __init__(self, account_type, num_stocks=1, dry_run=True):
        self.account_type = account_type
        self.num_stocks = num_stocks
        self.dry_run = dry_run
        self.api = get_alpaca_rest_api(self.account_type)
        self.logger = get_logger("broker")

    def get_position(self, symbol):
        """
        Returns None if it does not exist
        """
        try:
            return self.api.get_position(symbol)
        except APIError as e:
            if str(e) != 'position does not exist':
                raise e

    def sell_stock(self, symb):
        position = self.get_position(symb)

        if position is None:
            self.logger.error(f"Attempted to sell position which does not exist: {symb}")
            raise MissingPositionError(symb)

        self.logger.info(f"Selling quantity {position.qty} of position {symb}")
        if not self.dry_run:
            return self.api.close_position(symb, qty=position.qty)

    def buy_stock(self, symb):
        self.logger.debug(f"Starting stock buy for {symb}")
        open_positions = self.api.get("/positions")
        self.logger.debug(f"{len(open_positions)} positions open")

        if any([p["symbol"] == symb for p in open_positions]):
            self.logger.error(f"Attempted to buy position that was already open: {symb}")
            raise PositionAlreadyExistsError(symb)

        if len(open_positions) >= self.num_stocks:
            self.logger.error(f"Number of open positions ({len(open_positions)}) >= num stocks configured ({self.num_stocks})")
            raise TooManyPositionsError()

        acct = self.api.get_account()
        avail_cash = float(acct.cash) / (self.num_stocks - len(open_positions))
        self.logger.debug(f"Available cash for {symb} buy: {avail_cash}")
        latest_quote = self.api.get_latest_quote(symb)
        self.logger.debug(f"Latest bid price for {symb}: {latest_quote.bp}")
        quantity = int(avail_cash // latest_quote.bp)

        if quantity < 1:
            self.logger.error(f"Not enough cash to buy stock: {symb}")
            raise NotEnoughCashError()

        self.logger.info(f"Buying quantity {quantity} of stock {symb}")
        if not self.dry_run:
            # return self.api.submit_order(symb, qty=quantity, side="buy", type="market", time_in_force="day")
            return self.api.submit_order(
                symbol=symb,
                side="buy",
                qty=quantity,
                type="market",
                order_class="oto",
                time_in_force="day",
                stop_loss={
                    "stop_price": latest_quote.bp * 0.999
                }
            )

    def liquidate_and_cancel_all(self):
        self.logger.warn("Cancelling all open orders and liquidating all positions")
        return self.api.delete("/positions", data={"cancel_orders": True})

    def get_clock(self):
        return self.api.get_clock()
