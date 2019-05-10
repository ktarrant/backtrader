import numpy as np

import backtrader as bt

class TDReversalStrategy(bt.Strategy):
    """
    TD = TDSequential
    The strategy enters
    """

    params = (
        ("period", 4),
        ("max_entry_count", 1),
        ("protect_entry_count", 4),
        ("cap_count", 9),
        ("min_atr_percent", 0.015),
    )

    lines = (
        "entry_signal",
        "entry_price",
        "protect_price",
        "close_signal",
    )

    def __init__(self):
        self.td = bt.indicators.TDSequential(period=self.p.period)
        self.atr = bt.indicators.AverageTrueRange()

        self.driver = bt.drivers.ReversalDriver(self)

    def get_entry_signal(self):
        # Require a minimum ATR to weed out low-probability trades
        atr_percent = self.atr.lines.atr[0] / self.data.close[0]
        if atr_percent < self.p.min_atr_percent:
            return 0

        for li in range(1, self.p.max_entry_count + 1):
            reversal = self.td.lines.reversal[-li]
            value = self.td.lines.value[0]
            if reversal > 0 and value == -li:
                return -1
            elif reversal < 0 and value == li:
                return 1
        return 0

    def next(self):
        self.lines.entry_signal[0] = self.get_entry_signal()
        # Currently this sets the limit buy to the hl/2 of the previous candle,
        # to retain some sort of conservatism
        # TODO: We need to make this configurable so we can optimize it!
        td_value = self.td.lines.value[0]
        if abs(td_value) == 1:
            self.lines.entry_price[0] = (self.data.high[0] + self.data.low[0]) / 2
        else:
            self.lines.entry_price[0] = self.lines.entry_price[-1]

        if abs(td_value) < self.p.protect_entry_count:
            self.lines.protect_price[0] = self.td.lines.level[0]
        elif abs(td_value) < self.p.cap_count:
            self.lines.protect_price[0] = self.lines.entry_price[0]
        else:
            self.lines.protect_price[0] = self.td.lines.level[0]

        self.driver.next(entry_signal=self.lines.entry_signal[0],
                         entry_price=self.lines.entry_price[0],
                         protect_price=self.lines.protect_price[0],
                         close_signal=0) # always go out with a stop babby

    def notify_order(self, order):
        self.driver.notify_order(order)

