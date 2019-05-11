import backtrader as bt
import numpy as np


class DriverStateObserver(bt.Observer):
    alias = ("DriverState",)
    lines = ("state",)

    plotinfo = dict(plot=True, subplot=True)
    plotlines = dict(
        state = dict(_method="bar"),
    )

    def get_driver_state(self):
        owner = self._owner

        try:
            driver = owner.driver
        except AttributeError:
            return np.NaN

        return driver.states.index(driver.state)

    def get_owner_value(self, line):
        owner = self._owner

        try:
            return getattr(owner.lines, line)[0]
        except AttributeError:
            return np.NaN

    def next(self):
        self.lines.state[0] = self.get_driver_state()


class DriverPriceObserver(bt.Observer):
    alias = ("DriverPrice",)
    lines = ("entry_price", "protect_price")

    plotinfo = dict(plot=True, subplot=False)
    plotlines = dict(
        entry_price = dict(marker='+', markersize=3.0, color='black', fillstyle='full'),
        protect_price = dict(marker='x', markersize=3.0, color='pink', fillstyle='full'),
    )

    def get_owner_value(self, line):
        owner = self._owner

        try:
            return getattr(owner.lines, line)[0]
        except AttributeError:
            return np.NaN

    def next(self):
        self.lines.entry_price[0] = (
            np.NaN if self.get_owner_value("entry_signal") == 0 else
            self.get_owner_value("entry_price"))
        self.lines.protect_price[0] = self.get_owner_value("protect_price")
