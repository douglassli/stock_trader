from brokerages.brokerage import AlpacaBrokerage
from live_trader.stream_listener import start_listener_process
from multiprocessing import Process, Queue
from time import sleep
from datetime import datetime, timedelta
from utils.utils import get_queue_items, get_logger
from exceptions import *


class LiveTradeManager:
    def __init__(self, account_type, strat_agg_gen_func, max_positions=1, dry_run=True, allow_margin=False, allow_shorting=False):
        self.account_type = account_type
        self.strat_agg_gen_func = strat_agg_gen_func
        self.max_positions = max_positions
        self.brokerage = AlpacaBrokerage(self.account_type, max_positions, dry_run)
        self.signal_queue = None
        self.trade_update_queue = None
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
        self.next_open_utc = None
        self.next_close_utc = None
        self.next_clean_up_utc = None
        self.market_open = False
        self.loop_time = 5
        self.logger = get_logger("live_trade_manager")

    def start_trading(self):
        self.update_times()
        self.logger.debug("Starting main loop")
        self.main_loop()

    def start_listener(self):
        self.logger.info("Starting listener process")
        self.trade_update_queue = Queue()
        self.signal_queue = Queue()
        strategies, period_aggregators = self.strat_agg_gen_func()
        p_args = (self.account_type, self.signal_queue, self.trade_update_queue, strategies, period_aggregators)
        self.listener_process = Process(target=start_listener_process, args=p_args)
        self.listener_process.start()

    def main_loop(self):
        while True:
            self.check_time()

            if self.trade_update_queue is not None:
                self.update_position_states()

            if self.signal_queue is not None:
                self.make_trade_decisions()

            sleep(self.loop_time)

    def check_time(self):
        cur_dt = datetime.utcnow()
        if cur_dt > self.next_open_utc or cur_dt > self.next_close_utc:
            self.update_times()

        if self.listener_process is not None and self.next_clean_up_utc < cur_dt < self.next_close_utc:
            self.stop_for_day()
        elif self.listener_process is None and (self.market_open or cur_dt > self.next_open_utc - timedelta(hours=4)):
            self.start_listener()

    def update_times(self):
        clock = self.brokerage.get_clock()
        self.next_open_utc = datetime.utcfromtimestamp(clock.next_open.timestamp())
        self.next_close_utc = datetime.utcfromtimestamp(clock.next_open.timestamp())
        self.next_clean_up_utc = self.next_close_utc - timedelta(minutes=5)
        self.market_open = clock.is_open
        self.logger.info(f"Market is now {'open' if self.market_open else 'closed'}")

    def stop_for_day(self):
        if self.listener_process is None or self.signal_queue is None or self.trade_update_queue is None:
            self.logger.error("Attempting to shut down process and queues that don't exist")
            self.shutdown()

        self.logger.info("Ending trading for the day")
        self.brokerage.liquidate_and_cancel_all()

        self.listener_process.terminate()
        self.listener_process.join()
        self.listener_process.close()
        self.listener_process = None

        self.trade_update_queue.close()
        self.signal_queue.close()
        self.trade_update_queue = None
        self.signal_queue = None

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

        if not self.market_open or \
                len(buy_signals) == 0 or \
                len(self.positions) >= self.max_positions:
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
        self.logger.warn("Shutting down system")
        if self.listener_process is not None:
            self.listener_process.terminate()
            self.listener_process.join()
            self.listener_process.close()

        if self.trade_update_queue is not None:
            self.trade_update_queue.close()

        if self.signal_queue is not None:
            self.signal_queue.close()

        exit(0)
