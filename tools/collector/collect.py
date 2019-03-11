from collections import OrderedDict
import argparse
import datetime
import pickle
import os
from multiprocessing import Pool

import pandas as pd
import backtrader as bt
from backtrader.utils import AutoOrderedDict

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
    ("drawdown", bt.analyzers.DrawDown),
    ("trades", bt.analyzers.TradeAnalyzer),
])
ANALYSIS_NAMES = OrderedDict([(ANALYSIS_CHOICES[name], name)
                              for name in ANALYSIS_CHOICES])

def get_label(strategy):
    name = type(strategy).__name__
    prefix = name.replace("Strategy", "")
    abbv = "".join([c for c in prefix if c.upper() == c])
    param_values = list(vars(strategy.params).values())
    param_label = ",".join([str(p) for p in param_values])
    return "{}({})".format(abbv, param_label) if param_label else abbv

def yield_analysis(analysis, prefix=None):
    for column in analysis:
        value = analysis[column]
        if isinstance(value, dict):
            for subcolumn, subvalue in yield_analysis(value):
                if prefix:
                    yield ("_".join([prefix, column, subcolumn]), subvalue)
                else:
                    yield ("_".join([column, subcolumn]), subvalue)
        else:
            if prefix:
                yield (prefix+"_"+column, value)
            else:
                yield (column, value)

def get_row_func(analyzers, plot=False):
    def _create_row(ticker, strategy, params):
        """
        Runs strategy against historical data and collect the results of all
        analyzers into a data row to be added to a summary table

        Args:
            ticker (str): name of the ticker to backtest
            strategy (Strategy): strategy to use in backtest
            params (dict): params to pass to Strategy initialization

        Returns:
            pd.Series: the result of yield_summary
        """
        cerebro = bt.Cerebro()

        # Use a sizer that will work independent of share price
        cerebro.addsizer(bt.sizers.PercentSizer, percents=90)

        # Add an indicator that we can extract afterwards
        cerebro.addstrategy(strategy, **params)

        # Set up the data source
        data = bt.feeds.IexData(dataname=ticker, cache=True)
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
        row["ticker"] = ticker
        row["strategy"] = get_label(result)

        for analyzer in result.analyzers:
            analyzer_type = type(analyzer)
            try:
                analysis_name = ANALYSIS_NAMES[analyzer_type]
            except KeyError:
                print("Unexpected analyzer: {}".format(analyzer))
                continue
            analysis = analyzer.get_analysis()
            analysis = pd.Series(OrderedDict(list(yield_analysis(analysis, prefix=analysis_name))))
            row = row.append(analysis)
        return row

    return _create_row

def run_collection(tickers, strategies, analyzers, pool_size=0, plot=False):
    row_func = get_row_func(analyzers, plot=plot)
    args_list = [(ticker, strategy.strategy, strategy.params)
                for ticker in tickers
                for strategy in strategies]
    if pool_size > 1:
        p = Pool(pool_size)
        table = pd.DataFrame(p.starmap(row_func, args_list))
        return table
    else:
        values = [row_func(*args) for args in args_list]
        table = pd.DataFrame(values)
        return table

def parse_args():
    toupper = lambda s: str(s).upper()
    parser = argparse.ArgumentParser(description="""
    Runs backtests on a bunch of tickers and/or strategies
    """)
    parser.add_argument("--ticker", "-t",
                        action="append",
                        type=toupper,
                        help="Add a single ticker to the collection")
    parser.add_argument("--group", "-g",
                        action="append",
                        choices=list(GROUP_CHOICES.keys()),
                        help="Add a group of tickers from n preset index")
    parser.add_argument("--analysis", "-a",
                        action="append",
                        choices=list(ANALYSIS_CHOICES.keys()),
                        help="Add an analyzer which will be included in table")
    parser.add_argument("--optimize",
                        action="store_true",
                        help="Add all variants of the strategy to compare")
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

def pack(strategy, **kwargs):
    return AutoOrderedDict(strategy=strategy,
                           params=AutoOrderedDict(**kwargs))


if __name__ == "__main__":
    args = parse_args()

    if args.group:
        args.group_label = ",".join(args.group)

        tickers = {s for group in args.group for s in GROUP_CHOICES[group]()}

        if args.ticker:
            tickers += set(args.ticker)

    elif args.ticker:
        tickers = set(args.ticker)

        args.group_label = ",".join(tickers)
        if len(args.group_label) > MAX_GROUP_LABEL_LEN:
            args.group_label = "{}tickers".format(len(tickers))

    else:
        raise NotImplementedError("User must provide either group or ticker!")

    if args.analysis is None:
        analyzers = []
    else:
        analyzers = [ANALYSIS_CHOICES[name] for name in args.analysis]

    if args.optimize:
        strategies = [
            pack(bt.strategies.STADTDBreakoutStrategy,
                 entry_td_max=-1,
                 close_td_reversal=False),
        ]

        for entry_td_max in range(1, 7):
            strategies += [
                pack(bt.strategies.STADTDBreakoutStrategy,
                     entry_td_max=entry_td_max,
                     close_td_reversal=True)
            ]

    else:
        strategies = [pack(bt.strategies.STADTDBreakoutStrategy,
                           entry_td_max=4,
                           close_td_reversal=True)]


    table = run_collection(tickers, strategies, analyzers,
                           pool_size=args.pool_size,
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
