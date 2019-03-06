#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2019 Kevin Tarrant
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


import backtrader as bt


class LatestBar(bt.Analyzer):
    '''This analyzer reports the latest value of datas lines and indicator lines
    used in a Strategy.

    Params:

      - timeframe (default: ``None``)
        If ``None`` then the timeframe of the 1st data of the system will be
        used

      - compression (default: ``None``)

        Only used for sub-day timeframes to for example work on an hourly
        timeframe by specifying "TimeFrame.Minutes" and 60 as compression

        If ``None`` then the compression of the 1st data of the system will be
        used

    Methods:

      - get_analysis

        Returns a dictionary with returns as values and the datetime points for
        each return as keys
    '''
    params = (
        ('prev', True), # include previous bar as well as latest bar
    )

    @staticmethod
    def yield_latest_bar(data, prev=True):
        yield ("datetime", data.datetime.datetime())
        for field_name in data.lines.getlinealiases():
            if field_name is "datetime":
                continue
            line = getattr(data.lines, field_name)
            yield (field_name, line[0])
            if prev:
                yield ("prev_" + field_name, line[-1])

    @staticmethod
    def nickname(typename):
        return "".join([c for c in typename if c.upper() == c]).lower()

    def next(self):
        for fn, fv in LatestBar.yield_latest_bar(self.data0, self.p.prev):
            self.rets[fn] = fv

        for li_i in self.strategy._lineiterators:
            for obj in self.strategy._lineiterators[li_i]:
                obj_name = LatestBar.nickname(type(obj).__name__)
                if obj_name.startswith("_"):
                    continue
                for field_name in obj.lines.getlinealiases():
                    full_name = "_".join([obj_name, field_name])
                    line = getattr(obj.lines, field_name)
                    try:
                        self.rets[full_name] = line[0]
                    except IndexError:
                        pass
                    prev_name = "prev_" + full_name
                    try:
                        self.rets[prev_name] = line[-1]
                    except IndexError:
                        pass