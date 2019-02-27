import numpy as np

from basket import BasketStrategy
from drivers import BreakoutDriver
from indicators import ADBreakout, TDSequential


class ADBreakoutStrategy(BasketStrategy):
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

    def __init__(self):
        super(ADBreakoutStrategy, self).__init__()

        self.breakout = ADBreakout()
        self.td = TDSequential()

        self.driver = BreakoutDriver(self)

    def next(self):
        self.driver.next()

    def notify_order(self, order):
        self.driver.notify_order(order)

    @property
    def entry_signal(self):
        try:
            breakout = self.breakout.lines.breakout[0]
            td_count = self.td.count[0]
        except IndexError:
            return 0
        if self.p.max_entry_td < 0:
            # a negative setting means we don't filter entry at all using TD
            return breakout
        elif self.p.max_entry_td == 0:
            # a setting of zero means we simply require the td count to have the
            # same sign as the breakout
            if td_count > 0 and breakout > 0:
                return breakout
            elif td_count < 0 and breakout < 0:
                return breakout
            else:
                return 0
        else:
            if 0 < td_count <= self.p.max_entry_td and breakout > 0:
                return breakout
            elif 0 > td_count >= -self.p.max_entry_td and breakout < 0:
                return breakout
            else:
                return 0

    @property
    def protect_price(self):
        try:
            return self.breakout.lines.stop[0]
        except IndexError:
            return np.NaN

    @property
    def close_signal(self):
        try:
            return self.td.lines.reversal[0]
        except IndexError:
            return 0
