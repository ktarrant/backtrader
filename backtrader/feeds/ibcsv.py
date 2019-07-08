from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import date, datetime, time

from .. import feed
from ..utils import date2num


class IBCSVData(feed.CSVDataBase):
    '''
    Parses a self-defined CSV Data used for testing.

    Specific parameters:

      - ``dataname``: The filename to parse or a file-like object
    '''

    def _loadline(self, linetokens):
        itoken = iter(linetokens)

        dttxt = next(itoken)  # Format is 'YYYYMMDD HH:MM:SS'
        try:
            dt = datetime.strptime(dttxt, "%Y%m%d %H:%M:%S")
        except ValueError:
            d = datetime.strptime(dttxt, "%Y%m%d").date()
            dt = datetime.combine(d, self.p.sessionend)

        self.lines.datetime[0] = date2num(dt)
        self.lines.open[0] = float(next(itoken))
        self.lines.high[0] = float(next(itoken))
        self.lines.low[0] = float(next(itoken))
        self.lines.close[0] = float(next(itoken))
        self.lines.volume[0] = float(next(itoken))

        return True


class IBCSV(feed.CSVFeedBase):
    DataCls = IBCSVData
