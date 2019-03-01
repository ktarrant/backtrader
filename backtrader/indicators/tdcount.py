from backtrader.indicator import Indicator


class TDSequential(Indicator):

    nickname = "td"

    params = (
        ("period", 4),
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
        self.addminperiod(self.params.period)

    def td_base(self, bar):
        cbar = self.data.close[-bar]
        pbar = self.data.close[-bar-self.p.period]
        return 1 if cbar > pbar else (-1 if cbar < pbar else 0)

    def ta_base(self, bar):
        up = 1.0 if (self.td_base(bar) == 1.0 and (
                self.data.high[-bar] > self.data.high[-bar-2])) else 0
        dn = -1.0 if (self.td_base(bar) == -1.0 and (
                self.data.low[-bar] < self.data.low[-bar-2])) else 0
        return up + dn

    def nextstart(self):
        self.lines.value[0] = 0

    def next(self):
        tdf = self.td_base(0)
        tdc = tdf
        for i in range(8):
            if self.td_base(i+1) == tdf:
                tdc += tdf
            else:
                break
        self.lines.value[0] = tdc
        self.lines.reversal[0] = self.ta_base(0) if (abs(tdc) > 7) else 0
