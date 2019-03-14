import datetime
import threading
import logging
import pickle
import os
from collections import OrderedDict

import requests
import pandas as pd
import numpy as np

from backtrader.metabase import MetaParams
from backtrader.utils.py3 import with_metaclass

logger = logging.getLogger(__name__)

class MetaSingleton(MetaParams):
    '''Metaclass to make a metaclassed class a singleton'''
    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = (
                super(MetaSingleton, cls).__call__(*args, **kwargs))

        return cls._singleton

class IexStore(with_metaclass(MetaSingleton, object)):
    '''Singleton class wrapping an ibpy ibConnection instance.

    The parameters can also be specified in the classes which use this store,
    like ``VCData`` and ``VCBroker``

    '''
    URL_CHART = "https://api.iextrading.com/1.0/stock/{symbol}/chart/{range}"
    HISTORICAL_DATE_COLUMNS = ["date"]

    params = (
        ("cache", False),
        # if True, data will be cached/reused in local storage
        ("cache_format", "cache/{today}-{symbol}-{lookback}.pickle"),
    )

    @staticmethod
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

    @staticmethod
    def parse_numeric(s):
        """
        Try to parse a numeric string
        :param s: a string that looks like a number
        :param how: how to parse the string
        :return: the parsed number or NaN if we fail
        """
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return np.NaN

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
        url = IexStore.URL_CHART.format(symbol=symbol, range=lookback)
        logger.info("Loading: '{}'".format(url))
        result = requests.get(url).json()
        try:
            df = pd.DataFrame(result)
        except KeyError:
            return pd.DataFrame()

        df[IexStore.HISTORICAL_DATE_COLUMNS] = (
            df[IexStore.HISTORICAL_DATE_COLUMNS].applymap(IexStore.parse_date))
        return df

    def __init__(self):
        super(IexStore, self).__init__()

        self.cache_lock = threading.Lock()
        self.cache_files = {}


    def get_table(self, symbol, lookback):
        if self.p.cache:
            today = datetime.date.today()
            with self.cache_lock:
                if (symbol, lookback) not in self.cache_files:
                    table = IexStore.load_historical(symbol, lookback)

                    cache_path = self.p.cache_format.format(
                        today=today, symbol=symbol, lookback=lookback)
                    cdir, cfile = os.path.split(cache_path)
                    logger.info(
                        "Caching data to path: {}".format(cache_path))
                    os.makedirs(cdir, exist_ok=True)
                    with open(cache_path, "wb") as fobj:
                        pickle.dump(table, fobj)
                    self.cache_files[(symbol, lookback)] = cache_path
                    return table

            # else ... we don't need the lock to read!
            cache_path = self.cache_files[(symbol, lookback)]
            with open(cache_path, 'rb') as file:
                return pickle.load(file)

        else:
            return IexStore.load_historical(symbol, lookback)