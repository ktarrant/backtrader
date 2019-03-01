import numpy as np

from backtrader.indicator import Indicator
from backtrader.indicators import If, And, Min, Max


class WickReversalSignal(Indicator):
    """
    Pattern Summary
    1. The body is used to determine the size of the reversal wick. A wick that
        is between 2.5 to 3.5 times larger than
    the size of the body is ideal.
    2. For a bullish reversal wick to exist, the close of the bar should fall
        within the top 35 percent of the overall range of the candle.
    3. For a bearish reversal wick to exist, the close of the bar should fall
        within the bottom 35 percent of the overall range of the candle.
    """

    nickname = "wick"

    lines = (
        "wick",
    )

    params = (
        ("wick_multiplier_min", 2.5),
        ("close_percent_max", 0.35)
    )

    plotinfo = dict(
        plot=True, subplot=False, plotlinelabels=True
    )

    plotline_base = dict()
    plotlines = dict(
        wick=dict(marker='o',
                  color='black',
                  # fillstyle='bottom',
                  markersize=8.0,
                  ls="",
                  )
    )

    def __init__(self):
        wick_range = self.data.high - self.data.low
        body_high = Max(self.data.close, self.data.open)
        body_low = Min(self.data.close, self.data.open)
        body_range = body_high - body_low
        wick_buy = (body_low - self.data.low) >= (
                self.p.wick_multiplier_min * body_range)
        wick_sell = (self.data.high - body_high) >= (
                self.p.wick_multiplier_min * body_range)
        # be careful, if wick range = 0 then close-low = 0 ; so avoiding divide
        # by zero list this is correct
        close_percent = (self.data.close - self.data.low) / If(
            wick_range == 0.0, 0.1, wick_range)
        close_buy = (close_percent >= (1 - self.p.close_percent_max))
        close_sell = (close_percent <= self.p.close_percent_max)
        self.lines.wick = If(And(wick_buy, close_buy),
                             self.data.low,
                             If(And(wick_sell, close_sell),
                                self.data.high,
                                np.NaN))
