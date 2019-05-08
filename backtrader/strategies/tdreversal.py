import numpy as np

import backtrader as bt

class TDReversalStrategy(bt.Strategy):
    """
    TD = TDSequential
    The strategy enters
    """

    params = (
        ("period", 4),
        ("entry_count", 2),
    )

    lines = (
        "entry_signal",
        "entry_price",
        "protect_price",
        # "close_signal",
    )

    def __init__(self):
        self.td = bt.indicators.TDSequential(period=self.p.period)

        self.driver = bt.drivers.ReversalDriver(self)

    def next(self):
        long_signal = (self.td.lines.value[0] == self.p.entry_count) and (
                    self.td.lines.reversal[-self.p.entry_count] < 0)
        short_signal = (self.td.lines.value[0] == -self.p.entry_count) and (
                    self.td.lines.reversal[-self.p.entry_count] > 0)
        self.lines.entry_signal[0] = 1 if long_signal else (
            -1 if short_signal else 0)
        # Currently this sets the limit buy to the hl/2 of the previous candle,
        # to retain some sort of conservatism
        # TODO: We need to make this configurable so we can optimize it!
        self.lines.entry_price[0] = (self.data.high[0] + self.data.low[0]) / 2
        self.lines.protect_price[0] = self.td.lines.level[0]
        self.driver.next(entry_signal=self.lines.entry_signal[0],
                         entry_price=self.lines.entry_price[0],
                         protect_price=self.lines.protect_price[0],
                         close_signal=0) # always go out with a stop babby

    def notify_order(self, order):
        self.driver.notify_order(order)

