import argparse
import logging
from collections import OrderedDict

import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go

from .util import get_latest_collection, load_collection

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

screener_column_map = OrderedDict([
    ("Ticker", "ticker"),
    ("Close", "latestbar_close"),
    ("Chg %", lambda r: ((r.latestbar_close - r.latestbar_prev_close)
                         / r.latestbar_close * 100)),
    ("Volume", "latestbar_volume"),
    ("SuperTrend Trend", get_trend_mapper('latestbar_s_trend')),
    ("SuperTrend Stop", "latestbar_s_stop"),
    ("ADBreakout Level", "latestbar_adb_level"),
    ("ADBreakout Events", get_adbreakout_events),
    ("TD Count", "latestbar_tds_value"),
    ("TD Events", get_tdcount_events),
])

def _apply_map(row, column_map):
    for column in column_map:
        mapper = column_map[column]
        try:
            if isinstance(mapper, str):
                yield (column, row[mapper])
            else:
                yield (column, mapper(row))
        except KeyError:
            pass

def create_evaluator(column_map=screener_column_map):

    def _eval_row(r):
        return pd.Series(OrderedDict(_apply_map(r, column_map)))

    return _eval_row

def make_screener_table(collection):
    summary = collection.apply(evaluator, axis=1)
    return summary.sort_values(by=["TD Count", "SuperTrend Trend", "Chg %"],
                               ascending=[False, False, False])

def plot_screener_table(nickname, title, summary):
    """
    Creates a giant table from the scan result

    Args:
        nickname (str): nickname to use for chart filename
        title (str): title to use for chart title
        summary (pd.DataFrame): collection to plot

    Returns:
        figure
    """
    trace = go.Table(
        header=dict(values=summary.columns,
                    # fill=dict(color=COLOR_NEUTRAL_MID),
                    align=['left'] * 5),
        cells=dict(values=[summary[col] for col in summary.columns],
                   # fill=dict(color=[bgcolor]),
                   align=['left'] * 5))
    layout = dict(title=title)
    data = [trace]
    figure = dict(data=data, layout=layout)
    logger.info("Creating plot '{}'".format(nickname))
    url = py.plot(figure, filename=nickname, auto_open=False)
    logger.info("Plot URL: {}".format(url))
    return url

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

    evaluator = create_evaluator()

    if args.collection is None:
        args.collection = get_latest_collection()

    collection = load_collection(args.collection)

    summary = make_screener_table(collection)

    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None):
        print(summary)

    last_datetime = collection.latestbar_datetime.dropna().iloc[-1].date()
    title = "{} ({})".format(args.nickname, last_datetime)
    url = plot_screener_table(args.nickname, title, summary)
    print(url)