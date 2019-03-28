import argparse
from collections import OrderedDict

import pandas as pd

from .util import get_latest_collection, load_collection

def get_trend_mapper(column):
    def trend_map(r):
        if r[column] > 0:
            return "Bullish"
        elif r[column] < 0:
            return "Bearish"
        else:
            return "Neutral"

    return trend_map

def get_events(r):
    events = []

    if not pd.isnull(r.latestbar_wrs_wick):
        events += ["WR"]

    if r.latestbar_adb_breakout != 0:
        events += ["ADB"]

    if r.latestbar_tds_reversal != 0:
        events += ["TDR"]

    if (r.latestbar_prev_tds_reversal != 0 and
        r.latestbar_tds_reversal == 0 and
        r.latestbar_tds_value == 1):
        events += ["TDF"]

    return ",".join(events)

screener_column_map = OrderedDict([
    ("Ticker", "ticker"),
    ("Events", get_events),
    ("Close", "latestbar_close"),
    ("Chg %", lambda r: ((r.latestbar_close - r.latestbar_prev_close)
                         / r.latestbar_close * 100)),
    ("Volume", "latestbar_volume"),
    ("SuperTrend Trend", get_trend_mapper('latestbar_s_trend')),
    ("SuperTrend Stop", "latestbar_s_stop"),
    ("ADBreakout Level", "latestbar_adb_level"),
    ("TD Count", "latestbar_tds_value"),
])

def create_evaluator(column_map=screener_column_map):

    def _eval_row(r):
        return pd.Series([r[column_map[column]]
                          if isinstance(column_map[column], str)
                          else column_map[column](r)
                          for column in column_map],
                         index=list(column_map.keys()))

    return _eval_row

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    Visualizes the best strategies from a large dataset of strategy backtests
    """)

    parser.add_argument("--collection",
                        default=None,
                        help="""Collection pickle file to use.
                        If none is provided then the latest in the default
                        collections path is used.""")


    args = parser.parse_args()

    evaluator = create_evaluator()

    if args.collection is None:
        args.collection = get_latest_collection()

    table = load_collection(args.collection)

    results = table.apply(evaluator, axis=1)

    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None):
        print(results)
