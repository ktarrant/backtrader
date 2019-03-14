import logging
import datetime
import os
import pickle
import threading
from collections import OrderedDict

import pandas as pd
import numpy as np

from backtrader.feed import DataBase
from backtrader import TimeFrame
from backtrader.utils import date2num
from backtrader.stores import iexstore
from backtrader.utils.py3 import with_metaclass

logger = logging.getLogger(__name__)


class MetaIexData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaIexData, cls).__init__(name, bases, dct)

        # Register with the store
        iexstore.IexStore.DataCls = cls

class IexData(with_metaclass(MetaIexData, DataBase)):

    lines = (
        "vwap",
    )


    RANGE_SELECTIONS = OrderedDict([
        (datetime.timedelta(days=30), "1m"),
        (datetime.timedelta(days=91), "3m"),
        (datetime.timedelta(days=182), "6m"),
        (datetime.timedelta(days=365), "1y"),
        (datetime.timedelta(days=365 * 2), "2y"),
        (datetime.timedelta(days=365 * 5), "5y"),
    ])

    _store = iexstore.IexStore

    def __init__(self, **kwargs):
        super(IexData, self).__init__()
        self.o = self._store(**kwargs)

        if self.p.timeframe < TimeFrame.Days:
            raise NotImplementedError("Intraday not supported")

        if self.p.fromdate:
            days_ago = datetime.date.today() - self.p.fromdate
            lks = [td for td in self.RANGE_SELECTIONS if td > self.p.fromdate]
            self.lookback = self.RANGE_SELECTIONS[lks[0]]
        else:
            self.lookback = list(self.RANGE_SELECTIONS.values())[-1]

        self.table = None
        self.index = 0

    def start(self):
        self.table = self.o.get_table(self.p.dataname, self.lookback)
        self.index = 0

    def _load(self):
        for column in self.table.columns:
            if column == "date":
                label = "datetime"
                value = date2num(self.table[column].iloc[self.index])
            else:
                label = column
                value = self.table[column].iloc[self.index]

            try:
                line = getattr(self.lines, label)
            except AttributeError:
                continue # don't worry about lines that are not used

            line[0] = value

        self.index += 1

        if self.index == len(self.table.index):
            return False
        else:
            return True
