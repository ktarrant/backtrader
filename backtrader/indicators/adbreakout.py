import numpy as np
import pandas as pd

from indicator import Indicator
from indicators import If, Supertrend, WickReversalSignal


class ADBreakout(Indicator):

    nickname = "stad"

    params = (
        ("trend_src", Supertrend),
        ("ad_src", WickReversalSignal),
    )

    lines = (
        "trend",
        "stop",
        "ad",
        "resistance",
        "support",
        "breakout",
    )

    plotinfo = dict(plot=True, subplot=False)

    def __init__(self):
        """
        Creates a breakout alert indicator using trend and wick source
        indicators
        """
        self.trendSrc = self.p.trend_src(self.data)
        self.adSrc = self.p.ad_src(self.data)
        self.distribution = If(
            self.trendSrc.lines.trend > 0, self.adSrc.lines.wick < 0, np.NaN)
        self.accumulation = If(
            self.trendSrc.lines.trend < 0, self.adSrc.lines.wick > 0, np.NaN)

        # pass thru the relevant lines from the sources
        self.lines.trend = self.trendSrc.lines.trend
        self.lines.stop = self.trendSrc.lines.stop
        self.lines.ad = self.adSrc.lines.wick

    def next(self):
        if self.trendSrc.lines.trend[0] > 0:
            self.lines.support[0] = self.trendSrc.lines.stop[0]

            if not pd.isnull(self.distribution[0]):
                if pd.isnull(self.lines.resistance[-1]):
                    self.lines.resistance[0] = self.data.high[0]
                else:
                    self.lines.resistance[0] = max(
                        self.data.high[0], self.lines.resistance[-1])

            elif self.trendSrc.lines.trend[-1] <= 0:
                # we just flipped trends, we don't know resistance yet
                self.lines.resistance[0] = np.NaN

            else:
                self.lines.resistance[0] = self.lines.resistance[-1]

        elif self.trendSrc.lines.trend[0] < 0:
            self.lines.resistance[0] = self.trendSrc.lines.stop[0]

            if not pd.isnull(self.accumulation[0]):
                if pd.isnull(self.lines.support[-1]):
                    self.lines.support[0] = self.data.low[0]
                else:
                    self.lines.support[0] = min(
                        self.data.low[0], self.lines.support[-1])

            elif self.trendSrc.lines.trend[-1] >= 0:
                # we just flipped trends, we don't know resistance yet
                self.lines.support[0] = np.NaN

            else:
                self.lines.support[0] = self.lines.support[-1]

        was_below_resistance = self.data0.close[-1] < self.lines.resistance[-1]
        was_above_support = self.data0.close[-1] > self.lines.support[-1]
        is_above_resistance = self.data0.close[0] > self.lines.resistance[-1]
        is_below_support = self.data0.close[0] < self.lines.support[-1]
        was_in_zone = was_below_resistance and was_above_support
        is_long = is_above_resistance and was_in_zone
        is_short = is_below_support and was_in_zone
        self.lines.breakout[0] = 1 if is_long else (-1 if is_short else 0)
