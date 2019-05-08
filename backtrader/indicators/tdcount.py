import backtrader as bt
import numpy as np

class TDSequential(bt.Indicator):

    nickname = "td"

    params = (
        ("period", 4),
        ("shoulder_count", 7),
        ("cap_count", 9),
        ("shoulder_period", 2),
    )

    lines = (
        "value",
        "level",
        "reversal",
    )

    plotinfo = dict(
        plothlines=[-9, 9],
        plotymargin=0.15,
        # subplot=False,
    )

    plotlines = dict(
        value=dict(_method='bar', alpha=0.50, width=1.0),
        level=dict(_plotskip=True),
        reversal=dict(_method='bar', alpha=1.00, width=1.0),
    )

    def __init__(self):
        cbar = self.data.close
        pbar = self.data.close(-self.p.period)
        self.td_base = bt.If(cbar > pbar, 1, bt.If(cbar < pbar, -1, 0))

    def _update_count(self):
        tdf = self.td_base[0]
        tdc = tdf
        i = 1
        try:
            while self.td_base[-i] == tdf:
                i += 1
                tdc += tdf
        except IndexError:
            # expected at the start of the backtest
            pass
        self.lines.value[0] = tdc

    def ta_base(self, bar):
        sp = self.p.shoulder_period
        up = 1.0 if (self.td_base[-bar] == 1.0 and (
                self.data.high[-bar] > self.data.high[-bar-sp])) else 0
        dn = -1.0 if (self.td_base[-bar] == -1.0 and (
                self.data.low[-bar] < self.data.low[-bar-sp])) else 0
        return up + dn

    def nextstart(self):
        self.lines.value[0] = 0
        self.lines.level[0] = np.NaN

    def next(self):
        self._update_count()

        if self.lines.value[0] > self.p.shoulder_count:
            capped = (self.p.cap_count
                      if self.lines.value[0] > self.p.cap_count
                      else self.lines.value[0])
            si = int(self.p.shoulder_count - capped)
            self.lines.level[0] = max([self.data.high[i] for i in range(si, 0)])
            self.lines.reversal[0] = (1 if self.lines.reversal[-1] == 1 else (
                1 if (self.data.close[0] > self.lines.level[0]) else 0))

        elif self.lines.value[0] < -self.p.shoulder_count:
            capped = (self.p.cap_count
                      if self.lines.value[0] < -self.p.cap_count
                      else -self.lines.value[0])
            si = int(self.p.shoulder_count - capped)
            self.lines.level[0] = min([self.data.low[i] for i in range(si, 0)])
            self.lines.reversal[0] = (-1 if self.lines.reversal[-1] == -1 else (
                -1 if (self.data.close[0] < self.lines.level[0]) else 0))
        else:
            self.lines.level[0] = self.lines.level[-1]
            self.lines.reversal[0] = 0
