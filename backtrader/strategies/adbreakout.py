import numpy as np

import backtrader as bt

class ADBreakoutStrategy(bt.Strategy):
    """
    Strategy which seeks to jump on a breakout away from a support/resistance
    level. The goal of the strategy is to jump on a strong move and then take
    profit when the move is extended.

    The default implementation uses the default ADBreakout indicator (which is
    the Super-Trend variety) for establishing breakout and stop and the TD count
    indicator for establishing take-profit scenarios
    """

    params = (
        ("max_entry_td", -1),
    )

    lines = (
        "entry_signal",
        "protect_price",
        "close_signal",
    )


    def __init__(self):
        super(ADBreakoutStrategy, self).__init__()

        self.breakout = bt.indicators.ADBreakout()
        self.td = bt.indicators.TDSequential()
        self.driver = bt.drivers.BreakoutDriver(self)

        self.lines.protect_price = self.breakout.lines.stop
        self.lines.close_signal = self.td.lines.reversal

    def update_breakout(self):
        breakout = self.breakout.lines.breakout[0]
        td_count = self.td.value[0]

        if self.p.max_entry_td < 0:
            # a negative setting means we don't filter entry at all using TD
            self.lines.entry_signal[0] = breakout
        elif self.p.max_entry_td == 0:
            # a setting of zero means we simply require the td count to have the
            # same sign as the breakout
            if td_count > 0 and breakout > 0:
                self.lines.entry_signal[0] = breakout
            elif td_count < 0 and breakout < 0:
                self.lines.entry_signal[0] = breakout
            else:
                self.lines.entry_signal[0] = 0
        else:
            if 0 < td_count <= self.p.max_entry_td and breakout > 0:
                self.lines.entry_signal[0] = breakout
            elif 0 > td_count >= -self.p.max_entry_td and breakout < 0:
                self.lines.entry_signal[0] = breakout
            else:
                self.lines.entry_signal[0] = 0

    def next(self):
        self.update_breakout()
        self.driver.next()

    def notify_order(self, order):
        self.driver.notify_order(order)
