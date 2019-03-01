import logging
import datetime
import os
import pickle
from collections import OrderedDict

import pandas as pd
import numpy as np
import requests

from backtrader.feed import DataBase
from backtrader import TimeFrame

logger = logging.getLogger(__name__)

def parse_date(s):
    """
    Try to parse a date like 2018-02-01
    :param s: a date string that looks like "YYYY-MM-DD"
    :return: the parsed date or NaT if we fail
    :type: datetime.date
    """
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return pd.NaT


def parse_numeric(s, how=pd.to_numeric):
    """
    Try to parse a numeric string
    :param s: a string that looks like a number
    :param how: how to parse the string
    :return: the parsed number or NaN if we fail
    """
    try:
        return how(s)
    except ValueError:
        return np.NaN

class IexData(DataBase):
    URL_CHART = "https://api.iextrading.com/1.0/stock/{symbol}/chart/{range}"
    HISTORICAL_DATE_COLUMNS = ["date"]
    RANGE_SELECTIONS = OrderedDict([
        (datetime.timedelta(days=30), "1m"),
        (datetime.timedelta(days=91), "3m"),
        (datetime.timedelta(days=182), "6m"),
        (datetime.timedelta(days=365), "1y"),
        (datetime.timedelta(days=365*2), "2y"),
        (datetime.timedelta(days=365*5), "5y"),
    ])

    # params = (
    #     ('dataname', None),
    #     ('name', ''),
    #     ('compression', 1),
    #     ('timeframe', TimeFrame.Days),
    #     ('fromdate', None),
    #     ('todate', None),
    #     ('sessionstart', None),
    #     ('sessionend', None),
    #     ('filters', []),
    #     ('tz', None),
    #     ('tzinput', None),
    #     ('qcheck', 0.0),  # timeout in seconds (float) to check for events
    #     ('calendar', None),
    # )

    params = (
        ("cache", False), # if True, data will be cached/reused in local storage
        ("cache_format", "collections/{today}-{symbol}-{lookback}.csv"),
    )

    # lines = (
    #     "open",
    #     "high",
    #     "low",
    #     "close",
    #     "volume",
    #     "openinterest",
    # )

    lines = (
        "vwap",
    )

    @staticmethod
    def load_historical(symbol, lookback="1m"):
        """
        Loads historical data from IEX Finance
        :param symbol: stock ticker to look up
        :type: str
        :param lookback: lookback period
        :type: int
        :return: loaded DataFrame
        :type: pd.DataFrame
        """
        url = IexData.URL_CHART.format(symbol=symbol, range=lookback)
        logger.info("Loading: '{}'".format(url))
        result = requests.get(url).json()
        try:
            df = pd.DataFrame(result)
        except KeyError:
            return pd.DataFrame()

        df[IexData.HISTORICAL_DATE_COLUMNS] = (
            df[IexData.HISTORICAL_DATE_COLUMNS].applymap(parse_date))
        return df

    def __init__(self):
        super(IexData, self).__init__()

        if self.p.timeframe < TimeFrame.Days:
            raise NotImplementedError("Intraday not supported")

        if self.p.fromdate:
            days_ago = datetime.date.today() - self.p.fromdate
            lks = [td for td in self.RANGE_SELECTIONS if td > self.p.fromdate]
            self.lookback = self.RANGE_SELECTIONS[lks[0]]
        else:
            self.lookback = list(self.RANGE_SELECTIONS.values())[-1]

        self.cache_fobj = None
        self.table = None
        self.index = 0

    def start(self):
        if self.p.cache:
            self.cache_fn = self.p.cache_format.format(
                today=datetime.date.today(),
                symbol=self.p.dataname,
                lookback=self.lookback)

            try:
                self.cache_fobj = open(self.cache_fn, "rb")
            except IOError:
                self.cache_fobj = None

        else:
            self.cache_fobj = None


    def _load(self):
        if self.table is None:
            if self.cache_fobj:
                try:
                    self.table = pickle.load(self.cache_fobj)

                except IOError:
                    logger.debug("Failed to load cache file, loading from web.")

                    self.table = IexData.load_historical(self.p.dataname,
                                                         lookback=self.lookback)


            else:
                self.table = IexData.load_historical(self.p.dataname,
                                                     lookback=self.lookback)

        for column in self.table.columns:
            getattr(self.lines, column)[0] = self.table[column].iloc[self.index]

        self.index += 1

    def stop(self):
        if self.p.cache:
            cdir, cfile = os.path.split(self.cache_fn)
            logger.info("Caching data to path: {}".format(self.cache_fn))
            os.makedirs(cdir, exist_ok=True)
            with open(self.cache_fn, "wb") as fobj:
                pickle.dump(fobj)

