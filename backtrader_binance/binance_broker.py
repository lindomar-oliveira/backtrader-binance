from collections import defaultdict, deque
import datetime as dt

from backtrader.broker import BrokerBase
from backtrader.utils.py3 import with_metaclass
from backtrader.order import Order, OrderBase
from backtrader.position import Position
from binance.enums import *

from .binance_store import BinanceStore


class BinanceOrder(OrderBase):
    def __init__(self, owner, data, exectype, binance_order):
        self.owner = owner
        self.data = data
        self.size = float(binance_order['origQty'])
        self.price = float(binance_order['price'])
        self.exectype = exectype
        self.ordtype = self.Buy if binance_order['side'] == SIDE_BUY else self.Sell
        self.binance_order = binance_order

        super(BinanceOrder, self).__init__()


class MetaBinanceBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        """Class has already been created ... register"""
        # Initialize the class
        super(MetaBinanceBroker, cls).__init__(name, bases, dct)
        BinanceStore.BrokerCls = cls


class BinanceBroker(with_metaclass(MetaBinanceBroker, BrokerBase)):
    _ORDER_TYPES = {
        Order.Limit: ORDER_TYPE_LIMIT,
        Order.Market: ORDER_TYPE_MARKET,
        Order.Stop: ORDER_TYPE_STOP_LOSS,
        Order.StopLimit: ORDER_TYPE_STOP_LOSS_LIMIT,
    }

    def __init__(self, **kwargs):
        super(BinanceBroker, self).__init__()

        self.notifs = deque()
        self.positions = defaultdict(Position)

        self.store = BinanceStore(**kwargs)
        self.store.binance_socket.start_user_socket(self._process_user_socket_msg)
        self.store.start_socket()

        self.open_orders = list()

    def _process_user_socket_msg(self, msg):
        """https://binance-docs.github.io/apidocs/spot/en/#payload-order-update"""
        if msg['e'] == 'executionReport':
            if msg['s'] == self.store.symbol:
                for o in self.open_orders:
                    if o.binance_order['orderId'] == msg['i']:
                        if msg['X'] == ORDER_STATUS_CANCELED:
                            o.cancel()
                        elif msg['X'] == ORDER_STATUS_EXPIRED:
                            o.expire()
                        elif msg['X'] in [ORDER_STATUS_FILLED, ORDER_STATUS_PARTIALLY_FILLED]:
                            executed_size = float(msg['l'])
                            executed_price = float(msg['L'])
                            o.execute(
                                dt.datetime.fromtimestamp(msg['T'] / 1000.0),
                                executed_size,
                                executed_price,
                                0, 0.0, 0.0,
                                0, 0.0, 0.0,
                                0.0, 0.0,
                                0, 0.0)
                            pos = self.getposition(o.data, clone=False)
                            pos.update(executed_size, executed_price)
                            o.completed() if msg['X'] == ORDER_STATUS_FILLED else o.partial()
                        elif msg['X'] == ORDER_STATUS_REJECTED:
                            o.reject()

                        if msg['X'] not in [ORDER_STATUS_NEW, ORDER_STATUS_PARTIALLY_FILLED]:
                            self.open_orders.remove(o)
                        self.notify(o)
        elif msg['e'] == 'error':
            raise msg

    def _submit(self, owner, data, side, exectype, size, price):
        order_type = self._ORDER_TYPES.get(exectype, ORDER_TYPE_MARKET)

        binance_order = self.store.create_order(side, order_type, size, price)
        order = BinanceOrder(owner, data, exectype, binance_order)
        self.open_orders.append(order)
        self.notify(order)
        return order

    def buy(self, owner, data, size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0, oco=None,
            trailamount=None, trailpercent=None,
            **kwargs):
        return self._submit(owner, data, SIDE_BUY, exectype, size, price)

    def cancel(self, order):
        order_id = order.binance_order['orderId']
        self.store.cancel_order(order_id)

    def get_asset_balance(self, asset):
        return self.store.get_asset_balance(asset)

    def getcash(self):
        self.cash = self.store._cash
        return self.cash

    def get_notification(self):
        if not self.notifs:
            return None

        return self.notifs.popleft()

    def getposition(self, data, clone=True):
        pos = self.positions[data._dataname]
        if clone:
            pos = pos.clone()
        return pos

    def getvalue(self, datas=None):
        self.value = self.store._value
        return self.value

    def notify(self, order):
        self.notifs.append(order)

    def sell(self, owner, data, size, price=None, plimit=None,
             exectype=None, valid=None, tradeid=0, oco=None,
             trailamount=None, trailpercent=None,
             **kwargs):
        return self._submit(owner, data, SIDE_SELL, exectype, size, price)

    def strprecision(self, value):
        return self.store.strprecision(value)
