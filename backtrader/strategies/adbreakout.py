import numpy as np

import backtrader as bt

class STADTDBreakoutStrategy(bt.Strategy):
    """
    ST = Supertrend, AD = ADBreakout, TD = TDSequential
    The strategy seeks to jump on a breakout away from a support/resistance
    level. The goal of the strategy is to jump on a strong move and then take
    profit when the move is extended.
    """

    params = (
        ("entry_td_max", -1),
        ("close_td_reversal", False),
    )

    lines = (
        "entry_signal",
        "protect_price",
        "close_signal",
    )


    def __init__(self):
        self.st = bt.indicators.Supertrend()
        self.wick = bt.indicators.WickReversalSignal()
        self.breakout = bt.indicators.ADBreakout(self.data,
                                                 self.st.lines.trend,
                                                 self.wick.lines.wick)
        self.td = bt.indicators.TDSequential()

        self.driver = bt.drivers.BreakoutDriver(self)

    def update_breakout(self):
        breakout = self.breakout.lines.breakout[0]
        td_count = self.td.value[0]

        if self.p.entry_td_max < 0:
            # a negative setting means we don't filter entry at all using TD
            self.lines.entry_signal[0] = breakout
        elif self.p.entry_td_max == 0:
            # a setting of zero means we simply require the td count to have the
            # same sign as the breakout
            if td_count > 0 and breakout > 0:
                self.lines.entry_signal[0] = breakout
            elif td_count < 0 and breakout < 0:
                self.lines.entry_signal[0] = breakout
            else:
                self.lines.entry_signal[0] = 0
        else:
            if 0 < td_count <= self.p.entry_td_max and breakout > 0:
                self.lines.entry_signal[0] = breakout
            elif 0 > td_count >= -self.p.entry_td_max and breakout < 0:
                self.lines.entry_signal[0] = breakout
            else:
                self.lines.entry_signal[0] = 0

        if self.p.close_td_reversal:
            self.lines.close_signal[0] = self.td.lines.reversal[0]
        else:
            self.lines.close_signal[0] = 0

        self.lines.protect_price[0] = self.st.lines.stop[0]

    def next(self):
        self.update_breakout()
        self.driver.next(entry_signal=self.lines.entry_signal[0],
                         protect_price=self.lines.protect_price[0],
                         close_signal=self.lines.close_signal[0])

    def notify_order(self, order):
        self.driver.notify_order(order)
