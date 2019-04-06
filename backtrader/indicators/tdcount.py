import backtrader as bt

class TDSequential(bt.Indicator):

    nickname = "td"

    params = (
        ("period", 4),
        ("reversal_count", 7),
        ("shoulder_period", 2),
    )

    lines = (
        "value",
        "reversal",
    )

    plotinfo = dict(
        plothlines=[-9, 9],  # max values
        plotymargin=0.15,
    )

    plotlines = dict(
        value=dict(_method='bar', alpha=0.50, width=1.0),
        reversal=dict(_method='bar', alpha=1.00, width=1.0),
    )

    def __init__(self):
        cbar = self.data.close
        pbar = self.data.close(-self.p.period)
        self.td_base = bt.If(cbar > pbar, 1, bt.If(cbar < pbar, -1, 0))

    def ta_base(self, bar):
        sp = self.p.shoulder_period
        up = 1.0 if (self.td_base[-bar] == 1.0 and (
                self.data.high[-bar] > self.data.high[-bar-sp])) else 0
        dn = -1.0 if (self.td_base[-bar] == -1.0 and (
                self.data.low[-bar] < self.data.low[-bar-sp])) else 0
        return up + dn

    def nextstart(self):
        self.lines.value[0] = 0

    def next(self):
        tdf = self.td_base[0]
        tdc = 1
        try:
            while self.td_base[-tdc] == tdf:
                tdc += 1
        except IndexError:
            # expected at the start of the backtest
            pass
        self.lines.value[0] = tdc
        rc = self.p.reversal_count
        self.lines.reversal[0] = self.ta_base(0) if (tdc > rc) else 0
