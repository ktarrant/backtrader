import argparse
import datetime
import logging

from backtrader.feeds.iex import IexData


def run():
    parser = argparse.ArgumentParser(
        description="Download IEX data suitable for use with a PandasData")

    parser.add_argument('ticker',
                        help='Ticker to be downloaded')

    parser.add_argument('--lookback', default='1y',
                        choices=list(IexData.RANGE_SELECTIONS.values()),
                        help='Lookback period, choices: {}'.format(
                            ", ".join(IexData.RANGE_SELECTIONS.values())))

    parser.add_argument("--outfile",
                        default="{today}-{ticker}-{lookback}.csv",
                        help="output file format")

    args = parser.parse_args()
    args.today = datetime.date.today()
    args.outfile = args.outfile.format(**vars(args))

    logging.basicConfig(level=logging.INFO)

    table = IexData.load_historical(args.ticker, lookback=args.lookback)

    table.to_csv(args.outfile)


if __name__ == "__main__":
    run()
