from collections import OrderedDict
import argparse
import datetime
import pickle

import pandas as pd
import backtrader as bt

from .tickers import dji_components, default_faves, load_sp500_weights

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

def run_backtest(table, strategy):
    """
    Runs strategy against historical data

    Args:
        table (pd.DataFrame): table of historical data to backtest
        strategy (Strategy): strategy to use in backtest

    Returns:
        pd.Series: the result of Basket.yield_summary
    """

    cerebro = bt.Cerebro()

    # Add an indicator that we can extract afterwards
    cerebro.addstrategy(strategy)

    # Set up the data source
    data = bt.feeds.PandasData(dataname=table.set_index("date"))
    cerebro.adddata(data)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.LatestBar)

    # Run over everything
    result = cerebro.run()

    result_strategy = result[0]
    return pd.Series(yield_summary(result_strategy))

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

def run_collection(symbols):

    return pd.DataFrame()


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
