import argparse
import logging
from collections import OrderedDict

import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go

from .util import get_latest_collection, load_collection
from .mapper import ReportMapper, ColumnMapper, ColorMapper

import backtrader as bt

logger = logging.getLogger(__name__)

pct_change = lambda actual, comp: (actual - comp) / comp

def ticker_mapper(r):
    return """
    <a href="https://finviz.com/quote.ashx?t={ticker}"><b>{ticker}</b></a>
    """.strip().format(ticker=r.ticker)

def close_mapper(r):
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

def adb_events_mapper(r):
    events = []
    if r.latestbar_wrs_wick == r.latestbar_high:
        events += ["WR-"]
    elif r.latestbar_wrs_wick == r.latestbar_low:
        events += ["WR+"]

    if r.latestbar_adb_breakout > 0:
        events += ["ADB+"]
    elif r.latestbar_adb_breakout < 0:
        events += ["ADB-"]

    return ",".join(events)

def adb_events_color_mapper(value, _):
    if "ADB" in value:
        if "ADB-" in value:
            return ColorMapper.pastels.red.dark
        else:
            return ColorMapper.pastels.green.dark

    elif "WR" in value:
        if "WR-" in value:
            return ColorMapper.pastels.red.light
        else:
            return ColorMapper.pastels.green.light
    else:
        return ColorMapper.pastels.yellow.light

def get_from_close_mapper(column):
    def _from_close_mapper(row):
        value = row[column]
        if pd.isnull(value):
            return ""
        else:
            return "{value:.02f} (C{chg:+.2%})".format(
                value=value, chg=pct_change(value, row.latestbar_close))

    return _from_close_mapper

def td_mapper(r):
    if r.latestbar_tds_reversal != 0:
        suffix = " (R)"

    elif (r.latestbar_prev_tds_reversal != 0 and r.latestbar_tds_value == 1):
        suffix = " (F)"

    else:
        suffix = ""

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


def cloud_mapper(r):
    close = r.latestbar_close
    span_a = r.latestbar_i_senkou_span_a
    span_b = r.latestbar_i_senkou_span_b
    c_top = max(span_a, span_b)
    c_bot = min(span_a, span_b)
    if close > c_top:
        value = c_top
    elif close < c_bot:
        value = c_bot
    else:
        return ""

    if pd.isnull(value):
        return ""
    else:
        return "{value:.02f} (C{chg:+.2%})".format(
            value=value, chg=pct_change(value, r.latestbar_close))

def tdr_mapper(r):
    state_id = r.latestbar_dso_state
    state = bt.drivers.ReversalDriver.states[int(state_id)]
    last_state_id = r.latestbar_prev_dso_state
    entry_price = r.latestbar_dpo_entry_price
    protect_price = r.latestbar_dpo_protect_price

    if r.latestbar_b_cash > r.latestbar_b_value:
        direction = "Short"
        exit_order = "Buy"
        if r.latestbar_close >= protect_price:
            state = "close"

    elif r.latestbar_b_cash < r.latestbar_b_value:
        direction = "Long"
        exit_order = "Sell"
        if r.latestbar_close <= protect_price:
            state = "close"

    if "entry" in state:
        if r.latestbar_tds_value > 0:
            direction = "Long"
            entry_order = "Buy"
        elif r.latestbar_tds_value < 0:
            direction = "Short"
            entry_order = "Sell"

        entry_order_str = f"{entry_order} Limit {entry_price:.02f}"
        return f"Entry {direction}; {entry_order_str}"

    elif "protect" in state:
        stop_order_str = f"{exit_order} Stop {protect_price:.02f}"
        return f"Protect {direction}; {stop_order_str}"

    else:
        return "Flat"

def winloss_mapper(r):
    try:
        total = int(r.trades_total_closed)
        won = int(r.trades_won_total)
    except ValueError:
        return "N/A"
    return "{}/{} ({.2%})".format(won, total, won/total)

screener_mapper = ReportMapper([
    ColumnMapper("Ticker", ticker_mapper),
    ColumnMapper("Close", close_mapper, close_color_mapper),
    ColumnMapper("Volume", volume_mapper, volume_color_mapper),
    ColumnMapper("Meme Count", td_mapper, td_color_mapper),
    ColumnMapper("Meme Level", get_from_close_mapper("latestbar_tds_level")),
    ColumnMapper("SuperTrend Trend", trend_mapper, trend_color_mapper),
    ColumnMapper("SuperTrend Stop", get_from_close_mapper("latestbar_s_stop")),
    ColumnMapper("ADBreakout Level",
                 get_from_close_mapper("latestbar_adb_level")),
    ColumnMapper("ADBreakout Events", adb_events_mapper,
                 adb_events_color_mapper),
    ColumnMapper("Ichi Cloud Stop", cloud_mapper),
    ColumnMapper("Ichi Conversion", get_from_close_mapper("latestbar_i_tenkan_sen")),
    ColumnMapper("Ichi Base", get_from_close_mapper("latestbar_i_kijun_sen")),
    ColumnMapper("TDR State", tdr_mapper),
    # ColumnMapper("Win/Loss", winloss_mapper),
], sort_order = [
    ("latestbar_tds_value", False),
    ("latestbar_s_trend", False),
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

    summary = screener_mapper.build_table(collection)

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