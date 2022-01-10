from brokerages.brokerage import AlpacaBrokerage
from live_trader.stream_listener import start_listener_process
from multiprocessing import Process, Queue
from time import sleep
from utils.utils import get_queue_items, get_logger
from exceptions import *


class LiveTradeManager:
    def __init__(self, account_type, max_positions=1, dry_run=True, allow_margin=False, allow_shorting=False):
        self.account_type = account_type
        self.max_positions = max_positions
        self.brokerage = AlpacaBrokerage(self.account_type, max_positions, dry_run)
        self.signal_queue = Queue()
        self.trade_update_queue = Queue()
        self.listener_process = None

        # {
        #   symbol: {
        #       quantity: int,
        #       entrance_price: float
        #   }
        # }
        self.positions = {}
        # {
        #   symbol: {
        #       order_id: str,
        #       state: str,
        #       side: str,  # e.g. buy or sell
        #   }
        # }
        self.open_orders = {}
        self.buying_power = None
        self.allow_margin = allow_margin
        self.allow_shorting = allow_shorting
        self.loop_time = 10
        self.logger = get_logger("live_trade_manager")

    def start_trading(self, strategies, period_aggregators):
        p_args = (self.account_type, self.signal_queue, self.trade_update_queue, strategies, period_aggregators)
        self.listener_process = Process(target=start_listener_process, args=p_args)
        self.logger.debug("Listener process starting...")
        self.listener_process.start()
        self.logger.debug("Starting main loop...")
        self.main_loop()

    def main_loop(self):
        while True:
            self.update_position_states()
            self.make_trade_decisions()
            sleep(self.loop_time)

    def update_position_states(self):
        for trade_update in get_queue_items(self.trade_update_queue):
            do_nothing_events = ["new", "partial_fill", "pending_new", "stopped", "pending_cancel", "pending_replace",
                                 "calculated", "order_replace_rejected", "order_cancel_rejected", "done_for_day"]
            event = trade_update.event
            order = trade_update.order

            self.logger.info(f"Trade updated, symbol: {order.symbol}, event: {event}, order id: {order.id}")

            if event in do_nothing_events:
                pass
            elif event == "fill":
                self.fill_order(trade_update)
            elif event in ["cancelled", "rejected", "suspended", "replaced", "expired"]:
                # TODO should probably deal with this more gracefully
                self.logger.error(f"Order was killed with event: {event}, symbol: {order.symbol}, order id: {order.id}")
                self.shutdown()

    def fill_order(self, trade_update):
        order = trade_update.order
        self.logger.info(f"Filling {order.side} order for {order.symbol}")

        self.open_orders.pop(order.id, None)
        if order.side == "buy":
            self.positions[order.symbol]["entrance_price"] = float(trade_update.price)
        elif order.side == "sell":
            self.positions.pop(order.symbol, None)

    def make_trade_decisions(self):
        signals = {}
        for signal in get_queue_items(self.signal_queue):
            signals[signal['symbol']] = signal

        buy_signals = []
        for symbol, signal in signals.items():
            if symbol in self.positions and signal["type"] == "sell":
                self.exit_position(signal)
            elif signal["type"] == "buy" and symbol not in self.positions:
                buy_signals.append(signal)

        if len(buy_signals) == 0 or len(self.positions) >= self.max_positions:
            return

        best_signal = self.get_best_signal(buy_signals)
        self.enter_position(best_signal)

    def enter_position(self, signal):
        symbol = signal['symbol']
        if symbol in self.positions or len(self.positions) >= self.max_positions:
            return

        self.logger.info(f"Entering {symbol} position")

        try:
            order = self.brokerage.buy_stock(symbol)
            self.positions[symbol] = {
                "quantity": order.qty,
                "entrance_price": None
            }
            self.open_orders[symbol] = {
                "order_id": order.id,
                "state": order.status,
                "side": "buy"
            }
        except (PositionAlreadyExistsError, TooManyPositionsError):
            self.synchronize_account()
        except NotEnoughCashError:
            pass

    def exit_position(self, signal):
        symbol = signal['symbol']
        if symbol not in self.positions:
            return
        elif symbol in self.open_orders:
            # TODO this is unlikely, but should probably be handled more gracefully
            self.logger.error(f"Attempted to sell position before buy order was filled symbol: {symbol}")
            self.shutdown()

        self.logger.info(f"Exiting {symbol} position")

        try:
            order = self.brokerage.sell_stock(symbol)
            self.open_orders[symbol] = {
                "order_id": order.id,
                "state": order.status,
                "side": "sell"
            }
        except MissingPositionError:
            self.synchronize_account()

    def get_best_signal(self, signals):
        # TODO implement signal strength and use that to decide
        return signals[0]

    def synchronize_account(self):
        # TODO
        self.logger.warn("Synchronizing account")
        pass

    def shutdown(self):
        self.listener_process.terminate()
        self.signal_queue.close()
        self.trade_update_queue.close()
        exit(0)
