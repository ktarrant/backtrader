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

    @staticmethod
    def binary(value, column):
        if value == "Bullish":
            return ColorMapper.default_colors.binary.bullish
        elif value == "Bearish":
            return ColorMapper.default_colors.binary.bearish
        else:
            return ColorMapper.default_colors.binary.neutral

    @staticmethod
    def day_chg(value, column):
        if value > 10.0: return ColorMapper.pastels.green.dark
        elif value > 5.0: return ColorMapper.pastels.green.mid
        elif value > 0: return ColorMapper.pastels.green.light
        elif value > -5.0: return ColorMapper.pastels.red.light
        elif value > -10.0: return ColorMapper.pastels.red.mid
        else: return ColorMapper.pastels.red.dark


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

    def color(self, value, column):
        if isinstance(self.color_mapper, str):
            return self.color_mapper
        else:
            return self.color_mapper(value, column)


class ReportMapper(object):

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
            table[mapper.header].apply(mapper.color,
                                       column=table[mapper.header])
            for mapper in self.column_mappers
            if mapper.header in table.columns
        ], index=table.columns)
        trace = go.Table(
            header=dict(values=table.columns,
                        fill=dict(
                            color=ColorMapper.default_colors.generic.headers),
                        align=['left'] * 5),
            cells=dict(values=[table[col] for col in table.columns],
                       fill=dict(color=colors),
                       align=['left'] * 5))
        layout = dict(title=title)
        data = [trace]
        figure = dict(data=data, layout=layout)
        return figure