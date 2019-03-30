import argparse
import logging
from collections import OrderedDict

import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go

from .util import get_latest_collection, load_collection
from .mapper import ReportMapper, ColumnMapper, ColorMapper

logger = logging.getLogger(__name__)

def get_trend_mapper(column):
    def trend_map(r):
        if r[column] > 0:
            return "Bullish"
        elif r[column] < 0:
            return "Bearish"
        else:
            return "Neutral"

    return trend_map

def get_adbreakout_events(r):
    events = []

    if not pd.isnull(r.latestbar_wrs_wick):
        events += ["WR"]

    if r.latestbar_adb_breakout != 0:
        events += ["ADB"]

    return ",".join(events)


def get_tdcount_events(r):
    events = []

    if r.latestbar_tds_reversal != 0:
        events += ["TDR"]

    if (r.latestbar_prev_tds_reversal != 0 and
        r.latestbar_tds_reversal == 0 and
        r.latestbar_tds_value == 1):
        events += ["TDF"]

    return ",".join(events)

screener_mapper = ReportMapper([
    ColumnMapper("Ticker", "ticker"),
    ColumnMapper("Close", "latestbar_close"),
    ColumnMapper("Chg %", lambda r: (
                        int((r.latestbar_close - r.latestbar_prev_close)
                        / r.latestbar_close * 10000) / 100.0)),
    ColumnMapper("Volume", "latestbar_volume"),
    ColumnMapper("SuperTrend Trend", get_trend_mapper('latestbar_s_trend'),
                 ColorMapper.binary),
    ColumnMapper("SuperTrend Stop", "latestbar_s_stop"),
    ColumnMapper("ADBreakout Level", "latestbar_adb_level"),
    ColumnMapper("ADBreakout Events", get_adbreakout_events),
    ColumnMapper("TD Count", "latestbar_tds_value"),
    ColumnMapper("TD Events", get_tdcount_events),
])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Visualizes the best strategies from a large dataset of strategy backtests
    """)

    parser.add_argument("--nickname",
                        default="test",
                        help="File nickname to use for chart")
    parser.add_argument("--collection",
                        default=None,
                        help="""Collection pickle file to use.
                        If none is provided then the latest in the default
                        collections path is used.""")


    args = parser.parse_args()

    if args.collection is None:
        args.collection = get_latest_collection()

    collection = load_collection(args.collection)

    summary = screener_mapper.get_table(collection)
    summary = summary.sort_values(by=["TD Count", "SuperTrend Trend", "Chg %"],
                                  ascending=[False, False, False])

    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None):
        print(summary)

    last_datetime = collection.latestbar_datetime.dropna().iloc[-1].date()
    title = "{} ({})".format(args.nickname, last_datetime)
    figure = screener_mapper.build_figure(title, collection, summary)
    logger.info("Creating plot '{}'".format(args.nickname))
    url = py.plot(figure, filename=args.nickname, auto_open=False)
    logger.info("Plot URL: {}".format(url))
    print(url)