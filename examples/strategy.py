import backtrader as bt


class RSIStrategy(bt.Strategy):
    def __init__(self):
        self.rsi = bt.indicators.RSI_SMA(self.data.close, period=21)  # RSI indicator

    def next(self):
        if not self.position:
            if self.rsi < 30:  # Enter long
                self.buy()
        else:
            if self.rsi > 70:
                self.close()  # Close long position
