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
        ('st_factor', 3.0),
        ('st_period', 7),
        ('st_use_wick', True),
        ("wick_multiplier_min", 2.5),
        ("wick_close_percent_max", 0.35),
        ("td_period", 4),
    )

    lines = (
        "entry_signal",
        "protect_price",
        "close_signal",
    )


    def __init__(self):
        self.st = bt.indicators.Supertrend(factor=self.p.st_factor,
                                           period=self.p.st_period,
                                           use_wick=self.p.st_use_wick)
        self.wick = bt.indicators.WickReversalSignal(
            wick_multiplier_min=self.p.wick_multiplier_min,
            close_percent_max=self.p.wick_close_percent_max)
        self.breakout = bt.indicators.ADBreakout(self.data,
                                                 self.st.lines.trend,
                                                 self.wick.lines.wick)
        self.td = bt.indicators.TDSequential(period=self.p.td_period)

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


class IADTDBreakoutStrategy(bt.Strategy):
    """
    I = Ichimoku, AD = ADBreakout, TD = TDSequential
    The strategy seeks to jump on a breakout away from a support/resistance
    level. The goal of the strategy is to jump on a strong move and then take
    profit when the move is extended.
    """
    params = (
        ("entry_td_max", -1),
        ("close_td_reversal", False),
        ('i_fast_period', 9),
        ('i_base_period', 26),
        ('i_long_period', 52),
    )

    lines = (
        "entry_signal",
        "protect_price",
        "close_signal",
    )

    def __init__(self):
        self.ichi = bt.indicators.Ichimoku(
            tenkan=self.p.i_fast_period,
            kijun=self.p.i_base_period,
            senkou=self.p.i_long_period,
            senkou_lead=self.p.i_base_period,
            chikou=self.p.i_base_period)


        # self.cloud_top = bt.Max(self.ichi.lines.senkou_span_a, self.ichi.lines.senkou_span_b)
        # self.cloud_bot = bt.Min(self.ichi.lines.senkou_span_a, self.ichi.lines.senkou_span_b)
        # self.trend = bt.If(self.data.close > self.cloud_top,
        #                    1.0,
        #                    bt.If(self.data.close < self.cloud_bot,
        #                          -1.0,
        #                          0.0)
        #                    )
        # self.lines.protect_price = bt.If(self.trend > 0, self.cloud_top, self.cloud_bot)

        self.trend = self.data.close - self.ichi.lines.senkou_span_a
        self.lines.protect_price = self.ichi.lines.senkou_span_a

        self.wick = bt.indicators.WickReversalSignal()
        self.breakout = bt.indicators.ADBreakout(self.data,
                                                 self.trend,
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

    def next(self):
        self.update_breakout()
        self.driver.next(entry_signal=self.lines.entry_signal[0],
                         protect_price=self.lines.protect_price[0],
                         close_signal=self.lines.close_signal[0])

    def notify_order(self, order):
        self.driver.notify_order(order)


