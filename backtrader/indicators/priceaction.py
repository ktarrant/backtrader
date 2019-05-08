import numpy as np

import backtrader as bt


class WickReversalSignal(bt.Indicator):
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
        body_high = bt.indicators.Max(self.data.close, self.data.open)
        body_low = bt.indicators.Min(self.data.close, self.data.open)
        body_range = body_high - body_low
        wick_buy = (body_low - self.data.low) >= (
                self.p.wick_multiplier_min * body_range)
        wick_sell = (self.data.high - body_high) >= (
                self.p.wick_multiplier_min * body_range)
        # be careful, if wick range = 0 then close-low = 0 ; so avoiding divide
        # by zero list this is correct
        close_percent = (self.data.close - self.data.low) / bt.If(
            wick_range == 0.0, 0.1, wick_range)
        close_buy = (close_percent >= (1 - self.p.close_percent_max))
        close_sell = (close_percent <= self.p.close_percent_max)
        self.lines.wick = bt.indicators.If(
                             bt.indicators.And(wick_buy, close_buy),
                             self.data.low,
                             bt.indicators.If(
                                 bt.indicators.And(wick_sell, close_sell),
                                 self.data.high,
                                 np.NaN))


class FadeReversalSignal(bt.Indicator):
    """
    1. The first bar of the pattern is about two times larger than the average
        size of the candles in the lookback period.
    2. The body of the first bar of the pattern should encompass more than 50
        percent of the bar's total range, but usually not more than 85 percent.
    3. The second bar of the pattern opposes the first. If the first bar of the
        pattern is bullish (C > 0), then the second bar must be bearish (C < 0).
        If the first bar is bearish (C < 0), then the second bar must be
        bullish (C > 0).
    """
    lines = (
        "fade",
    )

    params = (
        ("lookback_period", 20),
        ("body_multiplier_min", 2.0),
        ("body_percent_min", 50.0),
        ("body_percent_max", 85.0),
    )

    plotinfo = dict(
        plot=True, subplot=False, plotlinelabels=True
    )

    plotline_base = dict()
    plotlines = dict(
        fade=dict(marker='x',
                  color='black',
                  # fillstyle='bottom',
                  markersize=8.0,
                  ls="",
                  ),
    )

    def __init__(self):
        atr = bt.indicators.AverageTrueRange(period=self.p.lookback_period)
        change = self.data.close - self.data.open
        body_multiplier = (change / atr)
        body_up_trig = body_multiplier(-1) > self.p.body_multiplier_min
        body_dn_trig = body_multiplier(-1) < -self.p.body_multiplier_min
        body_size = abs(change) / (self.data.high - self.data.low) * 100.0
        fits_min = body_size > self.p.body_percent_min
        fits_max = body_size < self.p.body_percent_max
        fits = bt.And(fits_min, fits_max)
        precheck_dn = bt.And(body_up_trig, fits)
        precheck_up = bt.And(body_dn_trig, fits)
        r_dn = bt.And(precheck_dn, self.data.close < self.data.close(-1))
        r_up = bt.And(precheck_up, self.data.close > self.data.close(-1))
        self.lines.fade = bt.If(r_dn,
                                self.data.high,
                                bt.If(r_up, self.data.low, np.NaN))


class ReversalSignal(bt.Indicator):
    lines = (
        "wick",
        "fade",
        "any",
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
                  ),
        fade=dict(marker='x',
                  color='black',
                  # fillstyle='bottom',
                  markersize=8.0,
                  ls="",
                  ),
        any=dict(_plotskip=True),
    )

    def __init__(self):
        self.wrs = WickReversalSignal()
        self.frs = FadeReversalSignal()
        self.lines.wick = self.wrs.lines.wick
        self.lines.fade = self.frs.lines.fade
        self.lines.any = bt.If(abs(self.lines.wick) > 0,
                               self.lines.wick,
                               bt.If(abs(self.lines.fade) > 0,
                                     self.lines.fade,
                                     np.NaN))
