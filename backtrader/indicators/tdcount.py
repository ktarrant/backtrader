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
        "reversal",
        "toe",
        "shoulder",
    )

    plotinfo = dict(
        plothlines=[-9, 9],
        plotymargin=0.15,
        # subplot=False,
    )

    plotlines = dict(
        value=dict(_method='bar', alpha=0.50, width=1.0),
        reversal=dict(_method='bar', alpha=1.00, width=1.0),
        toe=dict(_plotskip=True),
        shoulder=dict(_plotskip=True),
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
        self.lines.toe[0] = np.NaN
        self.lines.shoulder[0] = np.NaN

    def next(self):
        self._update_count()

        value = self.lines.value[0]

        if value == 1:
            self.lines.toe[0] = self.data.low[0]
        elif value == -1:
            self.lines.toe[0] = self.data.high[0]
        else:
            self.lines.toe[0] = self.lines.toe[-1]

        if value > self.p.shoulder_count:

            if value >= self.p.cap_count:
                ei = int(self.p.shoulder_count - self.p.cap_count) + 1
                si = ei - self.p.shoulder_period
                self.lines.shoulder[0] = max([self.data.high[i]
                                              for i in range(si, ei)])
            else:
                ei = int(self.p.shoulder_count - value) + 1
                si = ei - self.p.shoulder_period
                self.lines.shoulder[0] = max([self.data.high[i]
                                              for i in range(si, ei)]
                                             + [self.lines.shoulder[-1]])

            self.lines.reversal[0] = (1 if self.lines.reversal[-1] == 1 else (
                1 if (self.data.close[0] > self.lines.shoulder[0]) else 0))

        elif value < -self.p.shoulder_count:

            if value <= -self.p.cap_count:
                ei = int(self.p.shoulder_count - self.p.cap_count) + 1
                si = ei - self.p.shoulder_period
                self.lines.shoulder[0] = max([self.data.low[i]
                                              for i in range(si, ei)])
            else:
                ei = int(self.p.shoulder_count + value) + 1
                si = ei - self.p.shoulder_period
                self.lines.shoulder[0] = max([self.data.low[i]
                                              for i in range(si, ei)]
                                             + [self.lines.shoulder[-1]])

            self.lines.reversal[0] = (-1 if self.lines.reversal[-1] == -1 else (
                -1 if (self.data.close[0] < self.lines.shoulder[0]) else 0))

        else:
            self.lines.shoulder[0] = self.lines.shoulder[-1]
            self.lines.reversal[0] = 0
