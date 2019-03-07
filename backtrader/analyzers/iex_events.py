import logging
import datetime

import pandas as pd
import numpy as np
import requests

import backtrader as bt


logger = logging.getLogger(__name__)

class IexEvents(bt.Analyzer):
    URL_EARNINGS = "https://api.iextrading.com/1.0/stock/{symbol}/earnings"
    URL_DIVIDENDS = (
        "https://api.iextrading.com/1.0/stock/{symbol}/dividends/{range}"
    )
    DIVIDEND_DATE_COLUMNS = [
        "declaredDate",
        "exDate",
        "paymentDate",
        "recordDate",
    ]
    EARNINGS_DATE_COLUMNS = [
        "EPSReportDate",
        "fiscalEndDate",
    ]

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
    def load_earnings_history(symbol):
        """
        Loads earnings history from IEX Finance
        :param symbol: stock ticker to look up
        :type: str
        :return: loaded table
        :type: pd.DataFrame
        """
        url = IexEvents.URL_EARNINGS.format(symbol=symbol)
        logger.info("Loading: '{}'".format(url))
        result = requests.get(url).json()
        try:
            df = pd.DataFrame(result["earnings"])
        except KeyError:
            return pd.DataFrame()
        df[IexEvents.EARNINGS_DATE_COLUMNS] = (
            df[IexEvents.EARNINGS_DATE_COLUMNS].applymap(IexEvents.parse_date))
        return df

    @staticmethod
    def load_dividends_history(symbol, lookback="5y"):
        """
        Loads dividends data from IEX Finance
        :param symbol: stock ticker to look up
        :type: str
        :param lookback: lookback period
        :type: int
        :return: loaded DataFrame
        :type: pd.DataFrame
        """
        url = IexEvents.URL_DIVIDENDS.format(symbol=symbol, range=lookback)
        logger.info("Loading: '{}'".format(url))
        data = requests.get(url).json()
        try:
            df = pd.DataFrame(data)
        except ValueError:
            return pd.DataFrame()

        df[IexEvents.DIVIDEND_DATE_COLUMNS] = (
            df[IexEvents.DIVIDEND_DATE_COLUMNS].applymap(IexEvents.parse_date))
        return df

    @staticmethod
    def yield_period_ydays(dates, after=datetime.date.today(), period=91):
        """
        Used to guess the day of year (yday) for an event based on the dates of
        past events. The year is divided into windows of length 'period', and
        for each window a best guess of the day of year (yday) that corresponds
        to that window is yielded
        :param dates: dates corresponding to past events
        :type: list of datetime.date
        :param after: the years of the generated dates will be adjusted to make
            them less than this date, defaults to today
        :type: datetime.date
        :param period: # of days to divide the year into, defaults to quarterly
        :type: int
        :returns: dates corresponding to when the events are likely to happen in
            the next year
        :type: datetime.date
        """
        ydays = [dt.timetuple().tm_yday for dt in dates]
        last_yday = 31  # prime this with a guess based on earnings season
        freq = int(365 / period)
        after_yday = after.timetuple().tm_yday
        for i in range(freq):
            yday_min = i * period
            yday_max = (yday_min + period) if (i < (freq - 1)) else 366
            matches = [yday for yday in ydays
                       if ((yday >= yday_min) and (yday < yday_max))]
            if len(matches) == 0:
                # yield a guess based on the previous periods result (or if we
                # haven't processed any results yet, use the existing guess)
                # TODO: if we have no data for Q1 but we do for later quarters,
                # we will make a 'wild' guess for Q1. this is a bug because we
                # could use later quarter data to make a much better guess!
                yday = last_yday + period
            else:
                # yield the first match since we think it's the most recent
                yday = matches[0]

            year = after.year if (after_yday < yday) else (after.year + 1)
            yield (datetime.date(year, 1, 1) + datetime.timedelta(yday - 1))

    def start(self):
        symbol = str(self.data.p.dataname)
        earnings_history = IexEvents.load_earnings_history(symbol)
        dividends_history = IexEvents.load_dividends_history(symbol)

        if earnings_history.empty:
            self.rets["last_report_date"] = pd.NaT
            self.rets["next_report_date"] = pd.NaT
        else:
            # TODO: Make the 'after' configurable instead of using default today
            last_report_dates = earnings_history["EPSReportDate"]
            next_report_dates = list(
                IexEvents.yield_period_ydays(last_report_dates))
            # we use this somewhat odd init pattern to do a key-value view
            self.rets["last_report_date"] = max(last_report_dates)
            self.rets["next_report_date"] = min(next_report_dates)

        if earnings_history.empty:
            self.rets["last_ex_date"] = pd.NaT
            self.rets["last_dividend_amount"] = np.NaN
            self.rets["dividend_period"] = np.NaN
            self.rets["next_ex_date"] = np.NaT
        else:
            # TODO: Make the 'after' configurable instead of using default today
            last_ex_dates = dividends_history["exDate"]
            next_ex_dates = list(IexEvents.yield_period_ydays(last_ex_dates))
            next_ex_date = min(next_ex_dates)
            # we use this somewhat odd init pattern to do a key-value view
            self.rets["last_ex_date"] = max(last_ex_dates)
            self.rets["last_dividend_amount"] = (
                dividends_history.iloc[0].loc["amount"])
            # TODO: Compute the dividend period from previous dates
            self.rets["dividend_period"] = 91
            self.rets["next_ex_date"] = next_ex_date
