import time

from functools import wraps
from math import floor

from backtrader.dataseries import TimeFrame
from backtrader.metabase import MetaParams
from backtrader.utils.py3 import with_metaclass
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException
from binance.websockets import BinanceSocketManager
from requests.exceptions import ConnectTimeout, ConnectionError
from twisted.internet import reactor


class MetaSingleton(MetaParams):
    """Metaclass to make a metaclassed class a singleton"""
    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = (
                super(MetaSingleton, cls).__call__(*args, **kwargs))

        return cls._singleton


class BinanceStore(with_metaclass(MetaSingleton, object)):
    _GRANULARITIES = {
        (TimeFrame.Minutes, 1): '1m',
        (TimeFrame.Minutes, 3): '3m',
        (TimeFrame.Minutes, 5): '5m',
        (TimeFrame.Minutes, 15): '15m',
        (TimeFrame.Minutes, 30): '30m',
        (TimeFrame.Minutes, 60): '1h',
        (TimeFrame.Minutes, 120): '2h',
        (TimeFrame.Minutes, 240): '4h',
        (TimeFrame.Minutes, 360): '6h',
        (TimeFrame.Minutes, 480): '8h',
        (TimeFrame.Minutes, 720): '12h',
        (TimeFrame.Days, 1): '1d',
        (TimeFrame.Days, 3): '3d',
        (TimeFrame.Weeks, 1): '1w',
        (TimeFrame.Months, 1): '1M'
    }

    BrokerCls = None  # Broker class will autoregister
    DataCls = None  # Data class will auto register

    @classmethod
    def getdata(cls, *args, **kwargs):
        """Returns ``DataCls`` with args, kwargs"""
        return cls.DataCls(*args, **kwargs)

    @classmethod
    def getbroker(cls, *args, **kwargs):
        """Returns broker with *args, **kwargs from registered ``BrokerCls``"""
        return cls.BrokerCls(*args, **kwargs)

    def __init__(self, api_key, api_secret, coin_refer, coin_target, retries=5):
        self.binance = Client(api_key, api_secret)
        self.binance_socket = BinanceSocketManager(self.binance)
        self.coin_refer = coin_refer
        self.coin_target = coin_target
        self.symbol = coin_refer + coin_target
        self.retries = retries

        self.step_size = None
        self.tick_size = None
        self.get_filters()

        self._cash = 0
        self._value = 0
        self.get_balance()
        
    def _format_value(self, value, step):
        precision = step.find('1') - 1
        if precision > 0:
            return '{:0.0{}f}'.format(value, precision)
        return floor(int(value))
        
    def retry(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(1, self.retries + 1):
                time.sleep(60 / 1200) # API Rate Limit
                try:
                    return func(self, *args, **kwargs)
                except (BinanceAPIException, ConnectTimeout, ConnectionError) as err:
                    if isinstance(err, BinanceAPIException) and err.code == -1021:
                        # Recalculate timestamp offset between local and Binance's server
                        res = self.binance.get_server_time()
                        self.binance.timestamp_offset = res['serverTime'] - int(time.time() * 1000)
                    
                    if attempt == self.retries:
                        raise
        return wrapper

    @retry
    def cancel_order(self, order_id):
        try:
            self.binance.cancel_order(symbol=self.symbol, orderId=order_id)
        except BinanceAPIException as api_err:
            if api_err.code == -2011:  # Order filled
                return
            else:
                raise api_err
        except Exception as err:
            raise err

    @retry
    def close_open_orders(self):
        orders = self.binance.get_open_orders(symbol=self.symbol)
        for o in orders:
            self.cancel_order(o['orderId'])
    
    @retry
    def create_order(self, side, type, size, price):
        params = dict()
        if type in [ORDER_TYPE_LIMIT, ORDER_TYPE_STOP_LOSS_LIMIT]:
            params.update({
                'timeInForce': TIME_IN_FORCE_GTC
            })
        if type != ORDER_TYPE_MARKET:
            params.update({
                'price': self.format_price(price)
            })

        return self.binance.create_order(
            symbol=self.symbol,
            side=side,
            type=type,
            quantity=self.format_quantity(size),
            **params)

    def format_price(self, price):
        return self._format_value(price, self.tick_size)
    
    def format_quantity(self, size):
        return self._format_value(size, self.step_size)

    @retry
    def get_asset_balance(self, asset):
        balance = self.binance.get_asset_balance(asset)
        return float(balance['free']), float(balance['locked'])

    def get_balance(self):
        free, locked = self.get_asset_balance(self.coin_target)
        self._cash = free
        self._value = free + locked
        
    def get_filters(self):
        symbol_info = self.get_symbol_info(self.symbol)
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                self.step_size = f['stepSize']
            elif f['filterType'] == 'PRICE_FILTER':
                self.tick_size = f['tickSize']

    def get_interval(self, timeframe, compression):
        return self._GRANULARITIES.get((timeframe, compression))

    @retry
    def get_symbol_info(self, symbol):
        return self.binance.get_symbol_info(symbol)

    def start_socket(self):
        if self.binance_socket.is_alive():
            return
        self.binance_socket.daemon = True
        self.binance_socket.start()

    def stop_socket(self):
        self.binance_socket.close()
        reactor.stop()
