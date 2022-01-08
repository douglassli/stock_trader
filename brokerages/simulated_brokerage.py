from utils.utils import get_logger
from exceptions import MissingPositionError, PositionAlreadyExistsError, TooManyPositionsError, NotEnoughCashError


class SimulatedBrokerage:
    def __init__(self, initial_cash, num_stocks=1):
        self.cash = initial_cash
        # {
        #   "symbol": { "quantity": int, "type": str, "enter_value": str, "enter_time": str }
        # }
        self.positions = {}

        # {
        #   "symbol": { "value": str, "timestamp": str }
        # }
        self.stock_values = {}
        self.logger = get_logger("sim_broker")
        self.num_stocks = num_stocks
        self.num_buys = 0
        self.num_sells = 0
        self.trades = []

    def get_position(self, symbol):
        return self.positions[symbol]

    # def close_broker(self):
    #     for symb, position in self.positions.items():
    #         if position["type"] == "short":
    #             self.exit_short(symb)
    #         elif position["type"] == "long":
    #             self.exit_long()

    def sell_stock(self, symb):
        if symb not in self.positions:
            self.logger.error(f"Attempted to sell position which does not exist: {symb}")
            raise MissingPositionError(symb)

        position = self.get_position(symb)

        self.logger.info(f"Selling quantity {position['quantity']} of position {symb}")

        last_quote = self.stock_values[symb]
        cur_val = last_quote["value"]
        last_quote_timestamp = last_quote["timestamp"]

        prof_value = (float(cur_val) * position["quantity"]) - (float(position["enter_value"]) * position["quantity"])
        prof_percent = (float(cur_val) - float(position["enter_value"])) / float(position["enter_value"]) * 100
        self.logger.info(f"Profit value: {prof_value:.2f}, Profit percent: {prof_percent:.2f}%")

        del self.positions[symb]
        self.cash = str(float(self.cash) + (float(cur_val) * position["quantity"]))
        self.num_sells += 1
        trade = {
            "symbol": symb,
            "quantity": position["quantity"],
            "enter_value": position["enter_value"],
            "enter_time": position["enter_time"],
            "sell_value": cur_val,
            "sell_time": last_quote_timestamp,
            "pct_profit": f"{prof_percent:.3f}"
        }
        self.trades.append(trade)

    def buy_stock(self, symb):
        self.logger.debug(f"Starting stock buy for {symb}")
        self.logger.debug(f"{len(self.positions)} positions open")

        if symb in self.positions:
            self.logger.error(f"Attempted to buy position that was already open: {symb}")
            raise PositionAlreadyExistsError(symb)

        if len(self.positions) >= self.num_stocks:
            self.logger.error(f"Number of open positions ({len(self.positions)}) >= num stocks configured ({self.num_stocks})")
            raise TooManyPositionsError()

        avail_cash = float(self.cash) / (self.num_stocks - len(self.positions))
        self.logger.debug(f"Available cash for {symb} buy: {avail_cash}")

        last_quote = self.stock_values[symb]
        cur_val = last_quote["value"]
        last_quote_timestamp = last_quote["timestamp"]
        self.logger.debug(f"Latest bid price for {symb}: {cur_val} at {last_quote_timestamp}")
        quantity = int(avail_cash // float(cur_val))

        if quantity < 1:
            self.logger.error(f"Not enough cash to buy stock: {symb}")
            raise NotEnoughCashError()

        self.logger.info(f"Buying quantity {quantity} of stock {symb}")
        self.positions[symb] = {"quantity": quantity, "enter_value": cur_val, "enter_time": last_quote_timestamp}
        self.cash = str(float(self.cash) - (quantity * float(cur_val)))
        self.num_buys += 1

    def get_equity(self):
        equity = sum([pos["quantity"] * float(self.stock_values[sym]["value"]) for sym, pos in self.positions.items()]) + float(self.cash)
        return f"{equity:.2f}"

    def update_value(self, symb, value, timestamp):
        self.stock_values[symb] = {"value": value, "timestamp": timestamp}


if __name__ == '__main__':
    sim_brokerage = SimulatedBrokerage("30000.00")

