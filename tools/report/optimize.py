import argparse
import os
import pickle

def find_default_collection():
    rootdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    collections_dir = os.path.join(rootdir, "collections")
    # TODO: Write this to actually find the file in the collections folder
    file_path = os.path.join(collections_dir, "2019-03-20_dji_collection.pickle")
    return os.path.abspath(file_path)

def load_collection(path):
    with open(path, "rb") as fobj:
        return pickle.load(fobj)

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

    if args.collection is None:
        args.collection = find_default_collection()

    table = load_collection(args.collection)

    # interesting params would be
    # trades_pnl_net_average
    # trades_won_pnl_max, trades_won_pnl_average
    # trades_won_total / trades_total_total
    # trades_short_pnl_average

    strategy_pivot = table.pivot_table(index="strategy")
    pos_sharpe = strategy_pivot[strategy_pivot.sharpe_sharperatio > 0]
    annotated_pivot = pos_sharpe[
        ["sharpe_sharperatio", "trades_pnl_net_average", "trades_won_total",
         "trades_total_total"
         ]]
    annotated_pivot.loc[:, "trades_won_percent"] = (
            annotated_pivot.trades_won_total
            / annotated_pivot.trades_total_total)
    candidates = annotated_pivot.loc[[
        annotated_pivot.sharpe_sharperatio.idxmax(),
        annotated_pivot.trades_won_percent.idxmax(),
        annotated_pivot.trades_pnl_net_average.idxmax()]]

    print(candidates)
    candidates.to_csv("summary.csv")