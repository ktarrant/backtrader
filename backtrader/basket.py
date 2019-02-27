from collections import OrderedDict
import logging

from strategy import Strategy

logger = logging.getLogger(__name__)


class BasketStrategy(Strategy):

    def __init__(self):
        self.indicators = OrderedDict()

    def addindicator(self, indicator):
        super(BasketStrategy, self).addindicator(indicator)
        ti = type(indicator)
        try:
            label = ti.nickname
        except AttributeError:
            label = ti.__name__
        self.indicators[label] = indicator

    @property
    def minperiod(self):
        return self._minperiod

    def yield_summary(self):
        yield ("datetime", self.data.datetime.datetime())

        for field_name in self.data.lines.getlinealiases():
            if field_name is "datetime":
                continue
            line = getattr(self.data.lines, field_name)
            yield (field_name, line[0])
            yield ("prev_" + field_name, line[-1])

        for indicator_name, indicator in self.indicators.items():
            for line_name in indicator.lines.getlinealiases():
                field_name = "{}_{}".format(indicator_name, line_name)
                line = getattr(indicator.lines, line_name)
                yield (field_name, line[0])
                prev_name = "prev_" + field_name
                yield (prev_name, line[-1])
