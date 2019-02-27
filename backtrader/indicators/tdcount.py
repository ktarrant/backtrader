from indicator import Indicator


class TDSequential(Indicator):

    nickname = "td"

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

    def td_base(self, bar):
        up = 1 if (self.data.close[-bar] > self.data.close[-bar-4]) else 0
        dn = -1 if (self.data.close[-bar] < self.data.close[-bar-4]) else 0
        return up + dn

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
