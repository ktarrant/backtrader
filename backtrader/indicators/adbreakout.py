import numpy as np
import pandas as pd

from backtrader.indicator import Indicator
from backtrader.indicators import If, Supertrend, WickReversalSignal


class ADBreakout(Indicator):
    # data - OHLC
    # data1 - trend - lines.trend
    # data2 - wick - lines.wick
    _mindatas = 3

    lines = (
        "level",
        "breakout",
    )

    plotinfo = dict(plot=True, subplot=False)

    def __init__(self):
        """
        Creates a breakout alert indicator using trend and wick source
        indicators
        """
        self.trend = self.data1
        self.ad = self.data2

    def next(self):
        if self.trend[0] > 0:
            if self.ad[0] >= self.data.high[0]:
                if pd.isnull(self.lines.level[-1]):
                    self.lines.level[0] = self.ad[0]
                else:
                    self.lines.level[0] = max(self.ad[0], self.lines.level[-1])

            elif self.trend[-1] <= 0:
                # we just flipped trends, we don't know resistance yet
                self.lines.level[0] = np.NaN

            else:
                self.lines.level[0] = self.lines.level[-1]

            was_below_resistance = self.data0.close[-1] < self.lines.level[-1]
            is_above_resistance = self.data0.close[0] > self.lines.level[-1]
            self.lines.breakout[0] = 1 if (
                    was_below_resistance and is_above_resistance) else 0

        elif self.trend[0] < 0:
            if self.ad[0] <= self.data.low[0]:
                if pd.isnull(self.lines.level[-1]):
                    self.lines.level[0] = self.ad[0]
                else:
                    self.lines.level[0] = min(self.ad[0], self.lines.level[-1])

            elif self.trend[-1] >= 0:
                # we just flipped trends, we don't know support yet
                self.lines.level[0] = np.NaN

            else:
                self.lines.level[0] = self.lines.level[-1]

            was_above_support = self.data0.close[-1] > self.lines.level[-1]
            is_below_support = self.data0.close[0] < self.lines.level[-1]
            self.lines.breakout[0] = -1 if (
                    was_above_support and is_below_support) else 0
