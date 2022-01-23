from brokerages.brokerage import AlpacaBrokerage
from live_trader.stream_listener import start_listener_process
from multiprocessing import Process, Queue
from time import sleep
from datetime import datetime, timedelta
from utils.utils import get_queue_items, get_logger
from exceptions import *
from dash_server.webserver import start_webserver_process
from utils.constants import COST_TRACE


class LiveTradeManager:
    def __init__(self, account_type, symbols, strat_agg_gen_func, max_positions=1,
                 dry_run=True, allow_margin=False, allow_shorting=False):
        self.account_type = account_type
        self.symbols = symbols
        self.strat_agg_gen_func = strat_agg_gen_func
        self.max_positions = max_positions
        self.brokerage = AlpacaBrokerage(self.account_type, max_positions, dry_run)
        self.period_queue = None
        self.trade_update_queue = None
        self.webserver_queue = None
        self.listener_process = None
        self.webserver_process = None
        self.period_aggregators = None
        self.strategies = None

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
        self.start_webserver()
        self.main_loop()

    def start_listener(self):
        self.logger.info("Starting listener process")
        self.trade_update_queue = Queue()
        self.period_queue = Queue()
        strategies, per_aggs = self.strat_agg_gen_func(self.symbols)
        timeframe = list(per_aggs.values())[0].timeframe
        self.strategies = strategies
        self.period_aggregators = per_aggs
        p_args = (self.account_type, self.period_queue, self.trade_update_queue, self.symbols, timeframe)
        self.listener_process = Process(target=start_listener_process, args=p_args)
        self.listener_process.start()

    def start_webserver(self):
        self.logger.info("Starting webserver process")
        self.webserver_queue = Queue()
        p_args = (self.webserver_queue,)
        self.webserver_process = Process(target=start_webserver_process, args=p_args)
        self.webserver_process.start()

    def main_loop(self):
        while True:
            self.check_time()

            if self.trade_update_queue is not None:
                self.update_position_states()

            if self.period_queue is not None:
                self.process_periods()

            sleep(self.loop_time)

    def check_time(self):
        cur_dt = datetime.utcnow()
        if cur_dt > self.next_open_utc or cur_dt > self.next_close_utc:
            self.update_times()

        if self.listener_process is not None and self.next_clean_up_utc < cur_dt < self.next_close_utc:
            self.stop_for_day()
        elif self.listener_process is None and ((self.market_open and cur_dt < self.next_clean_up_utc) or cur_dt > self.next_open_utc - timedelta(hours=4)):
            self.start_listener()

    def update_times(self):
        clock = self.brokerage.get_clock()
        self.next_open_utc = datetime.utcfromtimestamp(clock.next_open.timestamp())
        self.next_close_utc = datetime.utcfromtimestamp(clock.next_close.timestamp())
        self.next_clean_up_utc = self.next_close_utc - timedelta(minutes=5)
        self.market_open = clock.is_open
        self.logger.info(f"Market is {'open' if self.market_open else 'closed'}")

    def stop_for_day(self):
        self.logger.info("Ending trading for the day")
        self.brokerage.liquidate_and_cancel_all()

        if self.listener_process is None or self.period_queue is None or self.trade_update_queue is None:
            self.logger.error("Attempting to shut down process and queues that don't exist")
            self.shutdown()

        self.listener_process.terminate()
        self.listener_process.join()
        self.listener_process.close()
        self.listener_process = None

        self.trade_update_queue.close()
        self.period_queue.close()
        self.trade_update_queue = None
        self.period_queue = None

        self.strategies = None

    def update_position_states(self):
        for trade_update in get_queue_items(self.trade_update_queue):
            do_nothing_events = ["new", "partial_fill", "pending_new", "stopped", "pending_cancel", "pending_replace",
                                 "calculated", "order_replace_rejected", "order_cancel_rejected", "done_for_day"]
            event = trade_update['event']
            order = trade_update['order']

            self.logger.info(f"Trade updated, symbol: {order['symbol']}, event: {event}, order id: {order['id']}")
            self.logger.debug(order)

            if event in do_nothing_events:
                pass
            elif event == "fill":
                self.fill_order(trade_update)
            elif event in ["cancelled", "rejected", "suspended", "replaced", "expired"]:
                # TODO should probably deal with this more gracefully
                self.logger.error(f"Order was killed with event: {event}, symbol: {order['symbol']}, order id: {order['id']}")
                self.shutdown()

    def fill_order(self, trade_update):
        order = trade_update['order']
        symbol = order["symbol"]
        side = order["side"]
        self.logger.info(f"Filling {order['side']} order for {symbol} of class {order['order_class']} and type {order['order_type']}")

        # TODO shouldn't happen if I dont manually place any orders
        # open_order = self.open_orders[symbol]
        # if symbol not in self.open_orders or open_order['order_id'] != order['id']:
        #     self.logger.error(f"Received update for non-tracked order: {symbol}, {order['id']}")
        #     self.shutdown()

        self.open_orders.pop(symbol, None)
        if side == "buy":
            self.positions[symbol]["entrance_price"] = float(trade_update['price'])
        elif side == "sell":
            self.positions.pop(order['symbol'], None)

    def process_periods(self):
        updated_symbols = set()
        for per_msg in get_queue_items(self.period_queue):
            symbol = per_msg["symbol"]
            period = per_msg["period"]
            updated_symbols.add(symbol)
            self.period_aggregators[symbol].process_period(period)
            strategy = self.strategies[symbol]
            strategy.update_analyzer_vals(self.period_aggregators[symbol])

            trace_points = strategy.get_last_trace_points()
            trace_points['cost'] = {
                'point': period.close,
                'trace_type': COST_TRACE
            }

            self.webserver_queue.put({
                'symbol': symbol,
                'timestamp': period.end_time,
                'trace_points': trace_points
            })

        buys = []
        for symbol in updated_symbols:
            signal = self.strategies[symbol].generate_signal()
            if signal == "buy" and symbol not in self.positions:
                buys.append(symbol)
            elif signal == "sell" and symbol in self.positions:
                self.exit_position(symbol)

        if not self.market_open or \
                len(buys) == 0 or \
                len(self.positions) >= self.max_positions:
            return

        best_buy_symbol = self.get_best_signal(buys)
        self.enter_position(best_buy_symbol)

    def enter_position(self, symbol):
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

    def exit_position(self, symbol):
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
        # self.logger.warn("Synchronizing account")
        self.logger.error("Synchronize not implemented")
        self.shutdown()
        pass

    def shutdown(self):
        self.logger.warn("Shutting down system")
        if self.listener_process is not None:
            self.listener_process.terminate()
            self.listener_process.join()
            self.listener_process.close()

        if self.trade_update_queue is not None:
            self.trade_update_queue.close()

        if self.period_queue is not None:
            self.period_queue.close()

        exit(0)
