import logging
import datetime
import argparse

import pandas as pd
import numpy as np
import requests

from backtrader.feeds.iex import IexData

URL_EARNINGS = "https://api.iextrading.com/1.0/stock/{symbol}/earnings"
URL_DIVIDENDS = (
    "https://api.iextrading.com/1.0/stock/{symbol}/dividends/{range}"
)
DIVIDEND_DATE_COLUMNS = ["declaredDate", "exDate", "paymentDate", "recordDate"]
EARNINGS_DATE_COLUMNS = ["EPSReportDate", "fiscalEndDate"]

logger = logging.getLogger(__name__)


class RequestException(Exception):
    """
    Exception for when we fail to complete a data query
    """
    pass


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


def load_earnings(symbol):
    """
    Loads earnings data from IEX Finance
    :param symbol: stock ticker to look up
    :type: str
    :return: loaded table
    :type: pd.DataFrame
    """
    url = URL_EARNINGS.format(symbol=symbol)
    logger.info("Loading: '{}'".format(url))
    result = requests.get(url).json()
    try:
        df = pd.DataFrame(result["earnings"])
    except KeyError:
        return pd.DataFrame()
    df[EARNINGS_DATE_COLUMNS] = df[EARNINGS_DATE_COLUMNS].applymap(parse_date)
    return df


def load_dividends(symbol, lookback="5y"):
    """
    Loads dividends data from IEX Finance
    :param symbol: stock ticker to look up
    :type: str
    :param lookback: lookback period
    :type: int
    :return: loaded DataFrame
    :type: pd.DataFrame
    """
    url = URL_DIVIDENDS.format(symbol=symbol, range=lookback)
    logger.info("Loading: '{}'".format(url))
    data = requests.get(url).json()
    try:
        df = pd.DataFrame(data)
    except ValueError:
        return pd.DataFrame()

    df[DIVIDEND_DATE_COLUMNS] = df[DIVIDEND_DATE_COLUMNS].applymap(parse_date)
    return df


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download IEX data suitable for use with a PandasData")

    parser.add_argument('ticker',
                        help='Ticker to be downloaded')

    parser.add_argument('--lookback', default='1y',
                        choices=list(IexData.RANGE_SELECTIONS.values()),
                        help='Lookback period, choices: {}'.format(
                            ", ".join(IexData.RANGE_SELECTIONS.values())))

    parser.add_argument("--outfile",
                        default="{today}-{ticker}-{lookback}.csv",
                        help="output file format")

    args = parser.parse_args()
    args.today = datetime.date.today()
    args.outfile = args.outfile.format(**vars(args))
    return args

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    args = parse_args()

    table = IexData.load_historical(args.ticker, lookback=args.lookback)

    table.to_csv(args.outfile)