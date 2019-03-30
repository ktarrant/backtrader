import logging

from backtrader.utils import AutoDict
import pandas as pd
import plotly.plotly as py
import plotly.graph_objs as go

logger = logging.getLogger(__name__)

class ColumnMapper(object):
    default_colors = AutoDict({
        "neutral": AutoDict({
            "dark": '#FFF301',
            "mid": '#FFF5BA',
            "light": '#FFFFD1',
        }),
        "bullish": AutoDict({
            "dark": '#BFFCC6',
            "mid": "#E7FFAC",
            "light": '#F3FFE3',
        }),
        "bearish": AutoDict({
            "dark": '#FFABAB',
            "mid": "#FFBEBC",
            "light": '#FFCBC1',
        }),
        "reversal": AutoDict({
            "dark": "#6EB5FF",
            "mid": "#85E3FF",
            "light": "#ACE7FF",
        }),
        "misc": AutoDict({
            "dark": "#FF9CEE",
            "mid": "#F6A6FF",
            "light": "#FFCCF9",
        })
    })

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
            self.color_mapper = ColumnMapper.default_colors.neutral.light

    def apply(self, row):
        if isinstance(self.column_mapper, str):
            try:
                return int(row[self.column_mapper] * 100) / 100.0
            except ValueError:
                return row[self.column_mapper]
        else:
            return self.column_mapper(row)

    def color(self, row):
        if isinstance(self.color_mapper, str):
            return self.color_mapper
        else:
            return self.color_mapper(row)


class ReportMapper(object):
    default_colors = AutoDict({
        "header": ColumnMapper.default_colors.neutral.mid
    })

    def __init__(self, column_mappers):
        """

        :param column_mappers: list of ColumnMapper instances, each one
            representing a column in the final report
        """
        self.column_mappers = column_mappers

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

    def get_table(self, collection):
        """

        :param collection: A collection table to summarize
        :return: pd.DataFrame
        """
        return collection.apply(self.apply_row, axis=1)

    def build_figure(self, title, collection, table):
        """
        Build a figure from a collection and summary
        :param title: title to use for this figure
        :param collection: source collection data
        :param table: data to display, built from the collection table
        :return: figure for use with plotly
        """
        colors = pd.DataFrame([
            collection.apply(mapper.color, axis=1)
            for mapper in self.column_mappers
            if mapper.header in table.columns
        ], index=table.columns).transpose()
        trace = go.Table(
            header=dict(values=table.columns,
                        fill=dict(
                            color=ReportMapper.default_colors.header),
                        align=['left'] * 5),
            cells=dict(values=[table[col] for col in table.columns],
                       fill=dict(color=colors),
                       align=['left'] * 5))
        layout = dict(title=title)
        data = [trace]
        figure = dict(data=data, layout=layout)
        return figure