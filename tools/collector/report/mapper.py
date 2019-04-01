import logging

from backtrader.utils import AutoDict
import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go

logger = logging.getLogger(__name__)

class ColorMapper(object):
    pastels = AutoDict({
        "yellow": AutoDict({
            "dark": '#FFF301',
            "mid": '#FFF5BA',
            "light": '#FFFFD1',
        }),
        "green": AutoDict({
            "dark": '#BFFCC6',
            "mid": "#E7FFAC",
            "light": '#F3FFE3',
        }),
        "red": AutoDict({
            "dark": '#FFABAB',
            "mid": "#FFBEBC",
            "light": '#FFCBC1',
        }),
        "blue": AutoDict({
            "dark": "#6EB5FF",
            "mid": "#85E3FF",
            "light": "#ACE7FF",
        }),
        "pink": AutoDict({
            "dark": "#FF9CEE",
            "mid": "#F6A6FF",
            "light": "#FFCCF9",
        })
    })

    default_colors = AutoDict({
        "generic": AutoDict({
            "headers": pastels.pink.mid,
            "neutral": pastels.yellow.light,
        }),
        "binary": AutoDict({
            "bullish": pastels.green.mid,
            "bearish": pastels.red.mid,
            "neutral": pastels.yellow.mid,
        }),
    })


class ColumnMapper(object):
    def __init__(self, header, column_mapper=None, color_mapper=None):
        self.header = header

        if column_mapper:
            self.column_mapper = column_mapper
        else:
            # by default assume the header is also the column name in the source
            self.column_mapper = header

        if color_mapper:
            self.color_mapper = color_mapper
        else:
            # use a neutral color by default
            self.color_mapper = ColorMapper.default_colors.generic.neutral

    def apply(self, row):
        if isinstance(self.column_mapper, str):
            try:
                return int(row[self.column_mapper] * 100) / 100.0
            except ValueError:
                return row[self.column_mapper]
        else:
            return self.column_mapper(row)

    def color(self, value, row):
        if isinstance(self.color_mapper, str):
            return self.color_mapper
        else:
            return self.color_mapper(value, row)


class ReportMapper(object):

    def __init__(self, column_mappers, sort_order=[]):
        """

        :param column_mappers: list of ColumnMapper instances, each one
            representing a column in the final report
        """
        self.column_mappers = column_mappers
        self.sort_columns = [c for c, _ in sort_order]
        self.sort_ascending = [a for _, a in sort_order]

    def apply_row(self, row):
        """

        :param row: A row from the collection table
        :return: pd.Series
        """
        values = pd.Series()

        for mapper in self.column_mappers:
            header = mapper.header
            try:
                value = mapper.apply(row)
            except KeyError:
                continue

            values.loc[header] = value

        return values

    def build_table(self, collection):
        """

        :param collection: A collection table to summarize
        :return: pd.DataFrame
        """
        self.table = pd.DataFrame()
        self.colors = pd.DataFrame()
        sorted_table = collection.sort_values(self.sort_columns,
                                              ascending=self.sort_ascending)
        for i in sorted_table.index:
            for mapper in self.column_mappers:
                row = collection.loc[i]
                try:
                    value = mapper.apply(row)
                except KeyError:
                    continue

                self.table.loc[i, mapper.header] = value
                self.colors.loc[i, mapper.header] = mapper.color(value, row)
        return self.table

    def build_figure(self, title):
        """
        Build a figure from a collection and summary
        :param title: title to use for this figure
        :param collection: source collection data
        :param table: data to display, built from the collection table
        :return: figure for use with plotly
        """
        trace = go.Table(
            header=dict(values=self.table.columns,
                        fill=dict(
                            color=ColorMapper.default_colors.generic.headers),
                        align=['left'] * 5),
            cells=dict(values=[self.table[col] for col in self.table.columns],
                       fill=dict(color=[self.colors[col]
                                        for col in self.colors.columns]),
                       align=['left'] * 5))
        layout = dict(title=title)
        data = [trace]
        figure = dict(data=data, layout=layout)
        return figure