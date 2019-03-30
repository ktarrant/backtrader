import argparse
import logging
from collections import OrderedDict

import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go

from .util import get_latest_collection, load_collection
from .mapper import ReportMapper, ColumnMapper, ColorMapper

logger = logging.getLogger(__name__)

pct_change = lambda actual, comp: (actual - comp) / comp

def close_mapper(r):
    chg = (int((r.latestbar_close - r.latestbar_prev_close)
           / r.latestbar_close * 10000) / 100)
    return "{close} ({chg:+.2%})".format(close=r.latestbar_close,
                                    chg=pct_change(r.latestbar_close,
                                                   r.latestbar_prev_close))

def close_color_mapper(_, r):
    value = pct_change(r.latestbar_close, r.latestbar_prev_close)
    if value > .10: return ColorMapper.pastels.green.dark
    elif value > .05: return ColorMapper.pastels.green.mid
    elif value > 0: return ColorMapper.pastels.green.light
    elif value > -.05: return ColorMapper.pastels.red.light
    elif value > -.10: return ColorMapper.pastels.red.mid
    else: return ColorMapper.pastels.red.dark

def trend_mapper(r):
    if r.latestbar_s_trend > 0:
        return "Bullish"
    elif r.latestbar_s_trend < 0:
        return "Bearish"
    else:
        return "Neutral"

def trend_color_mapper(value, _):
    if value == "Bullish":
        return ColorMapper.default_colors.binary.bullish
    elif value == "Bearish":
        return ColorMapper.default_colors.binary.bearish
    else:
        return ColorMapper.default_colors.binary.neutral

def volume_mapper(r):
    chg = pct_change(r.latestbar_volume, r.latestbar_prev_volume)
    for suffix, thresh in [("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if r.latestbar_volume > thresh:
            return "{value}{suffix} ({chg:+.2%})".format(
                value=int(r.latestbar_volume / thresh), suffix=suffix, chg=chg)
    return str(r.latestbar_volume)

def volume_color_mapper(value, _):
    if "+" in value:
        return ColorMapper.pastels.yellow.mid
    else:
        return ColorMapper.pastels.yellow.light

def get_adbreakout_events(r):
    events = []

    if not pd.isnull(r.latestbar_wrs_wick):
        events += ["WR"]

    if r.latestbar_adb_breakout != 0:
        events += ["ADB"]

    return ",".join(events)


def td_mapper(r):
    suffix = ""

    if r.latestbar_tds_reversal != 0:
        suffix = " (R)"

    elif (r.latestbar_prev_tds_reversal != 0 and r.latestbar_tds_value == 1):
        suffix = " (F)"

    else:
        suffic = ""

    return "{}{}".format(int(r.latestbar_tds_value), suffix)

def td_color_mapper(value, r):
    count = r.latestbar_tds_value
    if count >= 6:
        if r.latestbar_tds_reversal != 0:
            return ColorMapper.pastels.blue.dark
        else:
            return ColorMapper.pastels.green.mid
    elif count > 0:
        if "F" in value:
            return ColorMapper.pastels.green.dark
        else:
            return ColorMapper.pastels.green.light
    elif count == 0:
        return ColorMapper.pastels.yellow.dark
    elif count > -6:
        if "F" in value:
            return ColorMapper.pastels.red.dark
        else:
            return ColorMapper.pastels.red.light
    else:
        if r.latestbar_tds_reversal != 0:
            return ColorMapper.pastels.blue.dark
        else:
            return ColorMapper.pastels.red.mid

screener_mapper = ReportMapper([
    ColumnMapper("Ticker", "ticker"),
    ColumnMapper("Close", close_mapper, close_color_mapper),
    ColumnMapper("Volume", volume_mapper, volume_color_mapper),
    ColumnMapper("SuperTrend Trend", trend_mapper, trend_color_mapper),
    ColumnMapper("SuperTrend Stop", "latestbar_s_stop"),
    ColumnMapper("ADBreakout Level", "latestbar_adb_level"),
    ColumnMapper("ADBreakout Events", get_adbreakout_events),
    ColumnMapper("TD Count", td_mapper, td_color_mapper),
])

# TODO: Make Ticker column bolded, and add link to Finviz
# TODO: Add (-%) down for the Stop
# TODO: Add (+/-%) up/down for the Breakout level
# TODO: Combine ADB level and events and dd +/- direction markers for ADB events
# TODO: Add colors for ADB/WR events
# TODO: Combine TD count and events and add +/ direction markers for TD events
# TODO: Add colors for TD events

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

    summary = screener_mapper.build_table(collection)
    summary = summary.sort_values(by=["TD Count", "SuperTrend Trend"],
                                  ascending=[False, False])

    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None):
        print(summary)

    last_datetime = collection.latestbar_datetime.dropna().iloc[-1].date()
    title = "{} ({})".format(args.nickname, last_datetime)
    figure = screener_mapper.build_figure(title)
    logger.info("Creating plot '{}'".format(args.nickname))
    url = py.plot(figure, filename=args.nickname, auto_open=False)
    logger.info("Plot URL: {}".format(url))
    print(url)