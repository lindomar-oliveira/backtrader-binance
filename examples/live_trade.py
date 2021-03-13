import datetime as dt

from backtrader import Cerebro, TimeFrame
from backtrader_binance import BinanceStore

from .strategy import RSIStrategy

if __name__ == '__main___':
    cerebro = Cerebro(quicknotify=True)

    store = BinanceStore(
        api_key='YOUR_BINANCE_KEY',
        api_secret='YOUR_BINANCE_SECRET',
        coin_refer='BTC',
        coin_target='USDT')
    broker = store.getbroker()
    cerebro.setbroker(broker)

    from_date = dt.datetime.utcnow() - dt.timedelta(minutes=1261)
    data = store.getdata(
        dataname='BTCUSDT',
        fromdate=from_date,
        timeframe=TimeFrame.Minutes,
        compression=60)

    cerebro.addstrategy(RSIStrategy)
    cerebro.adddata(data)
    cerebro.run()
