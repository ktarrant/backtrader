import backtrader as bt
from backtrader.utils import AutoOrderedDict

class Optimizer(object):

    @staticmethod
    def pack(strategy, **kwargs):
        return AutoOrderedDict(strategy=strategy,
                               params=AutoOrderedDict(**kwargs))

    def _generate_STADTDB(self, optimize=False):
        if optimize:
            yield AutoOrderedDict(entry_td_max=-1,
                                  close_td_reversal=False)

            for factor in [2.0, 3.0, 4.0]:
                for st_period in [3, 7, 21, 50]:
                    for use_wick in [True, False]:
                        for entry_td_max in [2, 4, 7]:
                            for close_td_reversal in [True, False]:
                                # 3 * 4 * 2 * 3 * 2 = 144
                                yield AutoOrderedDict(
                                    entry_td_max=entry_td_max,
                                    close_td_reversal=close_td_reversal,
                                    st_factor=factor,
                                    st_period=st_period,
                                    st_use_wick=use_wick,
                                    )

        else:
            yield AutoOrderedDict(entry_td_max=4,
                                  close_td_reversal=True)

    def generate_strategy_params(self, strategy, optimize=False):
        if strategy == bt.strategies.STADTDBreakoutStrategy:
            for args in self._generate_STADTDB(optimize=optimize):
                yield args

        else:
            yield AutoOrderedDict()