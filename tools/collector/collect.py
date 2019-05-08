from collections import OrderedDict
import argparse
import datetime
import pickle
import os
from multiprocessing import Pool

import pandas as pd
import backtrader as bt

from .tickers import dji_components, default_faves, load_sp500_weights
from .optimizer import Optimizer

GROUP_CHOICES = OrderedDict([
    ("faves", lambda: default_faves),
    ("dji", lambda: dji_components),
    ("sp500", lambda: list(load_sp500_weights().index)),
])

DEFAULT_OUTPUT = (
    "collections/{today}_{group_label}_{compression}_{strategy}.{ext}")
MAX_GROUP_LABEL_LEN = 16

ANALYSIS_CHOICES = OrderedDict([
    ("latestbar", bt.analyzers.LatestBar),
    ("events", bt.analyzers.IexEvents),
    ("drawdown", bt.analyzers.DrawDown),
    ("trades", bt.analyzers.TradeAnalyzer),
    ("sharpe", bt.analyzers.SharpeRatio),
])
ANALYSIS_NAMES = OrderedDict([(ANALYSIS_CHOICES[name], name)
                              for name in ANALYSIS_CHOICES])
param_abbv = lambda a: str(a).replace("True", "T").replace("False","F")

def get_strategy_class_label(strategyClass):
    name = strategyClass.__name__
    prefix = name.replace("Strategy", "")
    return "".join([c for c in prefix if c.upper() == c])

STRATEGIES = OrderedDict([(get_strategy_class_label(c), c) for c in [
    bt.strategies.STADTDBreakoutStrategy,
    bt.strategies.IADTDBreakoutStrategy,
    bt.strategies.TDReversalStrategy,
]])

def get_strategy_instance_label(strategy):
    prefix = get_strategy_class_label(type(strategy))
    param_values = list(vars(strategy.params).values())
    param_label = ",".join([param_abbv(p) for p in param_values])
    return "{}({})".format(prefix, param_label) if param_label else prefix

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

def create_row(ticker, strategy, params, analyzers, args):
    """
    Runs strategy against historical data and collect the results of all
    analyzers into a data row to be added to a summary table

    Args:
        ticker (str): name of the ticker to backtest
        strategy (Strategy): strategy to use in backtest
        params (dict): params to pass to Strategy initialization
        analyzers (list): list of analyzers to add to the backtest
        args: args object with extra options

    Returns:
        pd.Series: the result of yield_summary
    """
    cerebro = bt.Cerebro()

    # Use a sizer that will work independent of share price
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)

    # Add an indicator that we can extract afterwards
    cerebro.addstrategy(strategy, **params)

    # Set up the data source
    data = bt.feeds.IexData(dataname=ticker, cache=args.cache_data)
    if args.compression == "Daily":
        cerebro.adddata(data)
    elif args.compression == "Weekly":
        cerebro.resampledata(data, timeframe=bt.TimeFrame.Weeks)

    # Add analyzers
    for analyzer in analyzers:
        cerebro.addanalyzer(analyzer)

    # Run over everything
    result_list = cerebro.run()
    result = result_list[0]

    if args.plot:
        cerebro.plot(style="candle")

    row = pd.Series()
    row["ticker"] = ticker
    row["strategy"] = get_strategy_instance_label(result)

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

if __name__ == "__main__":
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
    parser.add_argument("--compression", "-c",
                        default="Daily",
                        choices=["Daily", "Weekly"],
                        help="Bar compression")
    parser.add_argument("--analysis", "-a",
                        action="append",
                        choices=list(ANALYSIS_CHOICES.keys()) + ["all"],
                        help="Add an analyzer which will be included in table")
    parser.add_argument("--strategy", "-s",
                        default="STADTDB",
                        choices=list(STRATEGIES.keys()),
                        help="Strategy to backtest")
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
    parser.add_argument("--csv",
                        action="store_true",
                        help="Generate CSV output")
    parser.add_argument("--bin",
                        action="store_true",
                        help="Generate pickled binary output")
    parser.add_argument("--plot",
                        action="store_true",
                        help="""Plot backtests in GUI.
                        Disabled with pool-size>1 to avoid stressing system""")
    parser.add_argument("--cache-data",
                        action="store_true",
                        help="""Cache the collected historical data""")
    args = parser.parse_args()
    args.today = datetime.date.today()

    if args.pool_size > 1 and args.plot:
        raise Exception("Cannot use --pool-size > 1 with the --plot option")

    if args.analysis is not None and "all" in args.analysis:
        args.analysis = list(ANALYSIS_CHOICES.keys())

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

    optimizer = Optimizer()

    args_list = [(ticker,
                  STRATEGIES[args.strategy],
                  params,
                  analyzers,
                  args)
                 for ticker in tickers
                 for params in optimizer.generate_strategy_params(
                    STRATEGIES[args.strategy],
                    optimize=args.optimize)
                 ]

    if args.pool_size > 1:
        p = Pool(args.pool_size)
        table = pd.DataFrame(p.starmap(create_row, args_list))
    else:
        values = [create_row(*args) for args in args_list]
        table = pd.DataFrame(values)

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
