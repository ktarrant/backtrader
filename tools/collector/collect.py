from collections import OrderedDict
import argparse
import datetime
import pickle
from multiprocessing import Pool

import pandas as pd
import backtrader as bt

from .tickers import dji_components, default_faves, load_sp500_weights
# from tools.iexdownload import load_earnings, load_dividends

# TODO: Populate this with callables that return a set of tickers
GROUP_CHOICES = OrderedDict([
    ("faves", lambda: default_faves),
    ("dji", lambda: dji_components),
    ("sp500", lambda: list(load_sp500_weights().index)),
])

DEFAULT_OUTPUT = "{today}_{group_label}_collection.{ext}"
MAX_GROUP_LABEL_LEN = 16

def yield_summary(strategy):
    od = OrderedDict()
    for analyzer in strategy.analyzers:
        od.update(analyzer.get_analysis())
    return od

def run_backtest(symbol, strategy):
    """
    Runs strategy against historical data

    Args:
        symbol (str): name of the symbol to backtest
        strategy (Strategy): strategy to use in backtest

    Returns:
        pd.Series: the result of Basket.yield_summary
    """

    cerebro = bt.Cerebro()

    # Add an indicator that we can extract afterwards
    cerebro.addstrategy(strategy)

    # Set up the data source
    data = bt.feeds.IexData(dataname=symbol, cache=True)
    cerebro.adddata(data)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.LatestBar)

    # Run over everything
    result = cerebro.run()

    result_strategy = result[0]
    return pd.Series(yield_summary(result_strategy))


def get_row_func(strategy, add_events=False):

    def _create_row(symbol):
        row_chunks = [run_backtest(symbol, strategy)]
        # if add_events:
        #     dividend_history = load_dividends(symbol)
        #     if dividend_history is not None:
        #         row_chunks += [make_dividend_summary(dividend_history)]
        #     earnings_history = load_earnings(symbol)
        #     if earnings_history is not None:
        #         row_chunks += [make_earnings_summary(earnings_history)]
        combined = pd.concat(row_chunks)
        return combined

    return _create_row

def run_collection(symbols, pool_size=0):
    row_func = get_row_func(bt.strategies.ADBreakoutStrategy)
    if pool_size > 1:
        p = Pool(pool_size)
        table = pd.DataFrame(p.map(row_func, symbols), index=symbols)
        return table
    else:
        values = [row_func(symbol) for symbol in symbols]
        table = pd.DataFrame(values, index=symbols)
        return table

def parse_args():
    parser = argparse.ArgumentParser(description="""
    Runs backtests on a bunch of tickers and/or strategies
    """)
    parser.add_argument("--symbol", "-s",
                        action="append",
                        help="Add a single symbol to the collection")
    parser.add_argument("--group", "-g",
                        action="append",
                        choices=list(GROUP_CHOICES.keys()),
                        help="Add a group of symbols from an preset index")
    parser.add_argument("--pool-size", "-p",
                        default=0,
                        type=int,
                        help="Pool size for collection multiprocessing")
    parser.add_argument("--output", "-o",
                        default=DEFAULT_OUTPUT,
                        help="Output file format, default: " + DEFAULT_OUTPUT)
    parser.add_argument("--csv", "-c",
                        action="store_true",
                        help="Generate CSV output")
    parser.add_argument("--bin", "-b",
                        action="store_true",
                        help="Generate pickled binary output")

    args = parser.parse_args()
    args.today = datetime.date.today()
    args.pool_size = args.pool_size if args.pool_size > 0 else 0

    return args

if __name__ == "__main__":
    args = parse_args()

    if args.group:
        args.group_label = ",".join(args.group)

        symbols = {s for group in args.group for s in GROUP_CHOICES[group]()}

        if args.symbol:
            symbols += set(args.symbol)

    elif args.symbol:
        symbols = set(args.symbol)

        args.group_label = ",".join(symbols)
        if len(args.group_label) > MAX_GROUP_LABEL_LEN:
            args.group_label = "{}symbols".format(len(symbols))

    else:
        raise NotImplementedError("User must provide either group or symbol!")

    table = run_collection(symbols)

    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None):
        print(table)

    if args.csv:
        csv_fn = args.output.format(ext="csv", **vars(args))
        print("Saving csv: {}".format(csv_fn))
        table.to_csv(csv_fn)

    if args.bin:
        bin_fn = args.output.format(ext="pickle", **vars(args))
        print("Saving pickle: {}".format(bin_fn))
        with open(bin_fn, mode="wb") as cobj:
            pickle.dump(table, cobj)
