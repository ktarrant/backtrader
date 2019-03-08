from collections import OrderedDict
import argparse
import datetime
import pickle
import os
from multiprocessing import Pool

import pandas as pd
import backtrader as bt

from .tickers import dji_components, default_faves, load_sp500_weights

GROUP_CHOICES = OrderedDict([
    ("faves", lambda: default_faves),
    ("dji", lambda: dji_components),
    ("sp500", lambda: list(load_sp500_weights().index)),
])

DEFAULT_OUTPUT = "collections/{today}_{group_label}_collection.{ext}"
MAX_GROUP_LABEL_LEN = 16

ANALYSIS_CHOICES = OrderedDict([
    ("latestbar", bt.analyzers.LatestBar),
    ("events", bt.analyzers.IexEvents),
])

def get_label(strategy):
    name = type(strategy).__name__
    prefix = name.replace("Strategy", "")
    abbv = "".join([c for c in prefix if c.upper() == c])
    param_values = list(vars(strategy.params).values())
    param_label = ",".join([str(p) for p in param_values])
    return "{}({})".format(abbv, param_label) if param_label else abbv

def get_row_func(strategy, analyzers, plot=False):
    def _create_row(symbol):
        """
        Runs strategy against historical data and collect the results of all
        analyzers into a data row to be added to a summary table

        Args:
            symbol (str): name of the symbol to backtest
            strategy (Strategy): strategy to use in backtest

        Returns:
            pd.Series: the result of yield_summary
        """
        cerebro = bt.Cerebro()

        # Use a sizer that will work independent of share price
        cerebro.addsizer(bt.sizers.PercentSizer, percents=20)

        # Add an indicator that we can extract afterwards
        cerebro.addstrategy(strategy)

        # Set up the data source
        data = bt.feeds.IexData(dataname=symbol, cache=True)
        cerebro.adddata(data)

        # Add analyzers
        for analyzer in analyzers:
            cerebro.addanalyzer(analyzer)

        # Run over everything
        result_list = cerebro.run()
        result = result_list[0]

        if plot:
            cerebro.plot()

        row = pd.Series()
        row["symbol"] = symbol
        row["strategy"] = get_label(result)
        for analyzer in result.analyzers:
            analysis = pd.Series(analyzer.get_analysis())
            row = row.append(analysis)
        return row

    return _create_row

def run_collection(symbols, strategy, analyzers, pool_size=0, plot=False):
    # TODO: Support multiple strategies
    row_func = get_row_func(strategy, analyzers, plot=plot)
    if pool_size > 1:
        p = Pool(pool_size)
        table = pd.DataFrame(p.map(row_func, symbols))
        return table
    else:
        values = [row_func(symbol) for symbol in symbols]
        table = pd.DataFrame(values)
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
                        help="Add a group of symbols from n preset index")
    parser.add_argument("--analysis", "-a",
                        action="append",
                        choices=list(ANALYSIS_CHOICES.keys()),
                        help="Add an analyzer which will be included in table")
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
    parser.add_argument("--plot",
                        action="store_true",
                        help="""Plot backtests in GUI.
                        Disabled with pool-size>1 to avoid stressing system""")
    args = parser.parse_args()
    args.today = datetime.date.today()
    args.pool_size = args.pool_size if args.pool_size > 0 else 0

    if args.pool_size > 1 and args.plot:
        raise Exception("Cannot use --pool-size > 1 with the --plot option")

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

    if args.analysis is None:
        analyzers = []
    else:
        analyzers = [ANALYSIS_CHOICES[name] for name in args.analysis]

    # TODO: Make the strategy choice configurable
    table = run_collection(symbols,
                           strategy=bt.strategies.STADTDBreakoutStrategy,
                           analyzers=analyzers,
                           plot=args.plot)

    with pd.option_context('display.max_rows', None,
                           'display.max_columns', None):
        print(table)

    # make sure collections dir exists
    collections_dir, output_format = os.path.split(args.output)
    os.makedirs(collections_dir, exist_ok=True)

    if args.csv:
        csv_fn = args.output.format(ext="csv", **vars(args))
        print("Saving csv: {}".format(csv_fn))
        table.to_csv(csv_fn)

    if args.bin:
        bin_fn = args.output.format(ext="pickle", **vars(args))
        print("Saving pickle: {}".format(bin_fn))
        with open(bin_fn, mode="wb") as cobj:
            pickle.dump(table, cobj)
