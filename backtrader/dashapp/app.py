import os

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

import backtrader as bt


# ------------------------------------------------------------------------------
# Static Configuration
# ------------------------------------------------------------------------------
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

local_dir = "snapshots"

strategy_optons = [
    {"label": "None", "value": "none"},
    {"label": "SMA Cross (Buy Only)", "value": "sma_cross"},
]

strategy_mapper = {
    "none": None,
    "sma_cross": bt.strategies.MA_CrossOver,
}

analyzer_mapper = {
    "trades": bt.analyzers.TradeAnalyzer,
}

# ------------------------------------------------------------------------------
# App Instantiation
# ------------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


# ------------------------------------------------------------------------------
# App Layout
# ------------------------------------------------------------------------------
app.layout = html.Div(children=[
    html.H1(children="Backtrader Run"),

    dcc.Dropdown(
        id="data-source-dropdown",
        options=[
            {"label": "Local Disk", "value": "local"},
        ],
        value="local"
    ),

    dcc.Dropdown(id="data-list-dropdown"),

    html.Div(id="dataname-field", children=""),

    dcc.Dropdown(id="strategy-dropdown", options=strategy_optons,
                 value=strategy_optons[0]["value"]),

    dcc.Store(id="backtest-store",
              data={
                  "datetime": [],
                  "ohlc": {},
                  "lines": [],
                  "analyzers": {},
              }),

    dcc.Graph(id="result-lines-graph"),

    dcc.Graph(id="result-trades-graph"),
])


# ------------------------------------------------------------------------------
# App Callbacks
# ------------------------------------------------------------------------------
@app.callback(
    Output("data-list-dropdown", "options"),
    [Input("data-source-dropdown", "value")])
def update_data_list(data_source_value):
    if data_source_value == "local":
        csv_files = [os.path.join(root, file)
                     for root, dirs, files in os.walk(local_dir)
                     for file in files
                     if file.endswith(".csv")]
        return [{"label": file, "value": file} for file in csv_files]

    else:
        raise NotImplementedError()


@app.callback(
    Output("dataname-field", "children"),
    [Input("data-list-dropdown", "value")])
def update_dataname(data_list_value):
    return data_list_value


def compute_traces(indicator, **kwargs):
    params = ",".join([str(v) for v in vars(indicator.params).values()])
    aliases = indicator.lines.getlinealiases()

    if not indicator.plotinfo.plot:
        return

    kwargs["plot_type"] = "Subplot" if indicator.plotinfo.subplot else "Scatter"

    if len(aliases) == 1:
        line = getattr(indicator.lines, aliases[0])
        name = "{alias}({params})".format(alias=aliases[0], params=params)
        yield dict(name=name, y=line.array, **kwargs)

    elif len(aliases) > 1:
        for alias in aliases:
            line = getattr(indicator.lines, alias)
            name = "{alias}({params})".format(alias=alias, params=params)
            yield dict(name=name, y=list(line.array), **kwargs)


@app.callback(
    Output("backtest-store", "data"),
    [Input("dataname-field", "children"),
     Input("strategy-dropdown", "value")])
def update_store(dataname, strategy_key):
    if not dataname:
        return {"datetime": [], "ohlc": {}, "lines": [], "analyzers": {}}

    cerebro = bt.Cerebro()
    # configure data using provided dataname
    # TODO: support non-local
    ibdata = bt.feeds.IBCSVData(dataname=dataname)
    cerebro.adddata(ibdata)
    # strategy is None if user picks "none"
    strategy = strategy_mapper[strategy_key]
    if strategy:
        cerebro.addstrategy(strategy)
    # add analyzers
    for name in analyzer_mapper:
        cerebro.addanalyzer(analyzer_mapper[name], _name=name)
    # run the backtest!
    result_list = cerebro.run()
    result = result_list[0]
    # extract ohlc data
    ohlc = {key: list(getattr(result.data.lines, key).array)
            for key in ["open", "high", "low", "close"]}
    dt = [bt.num2date(d) for d in result.data.lines.datetime.array]
    # extract indicator data
    indicators = [trace
                  for indicator in result.getindicators()
                  for trace in compute_traces(indicator)]
    observers = [trace
                 for observer in result.getobservers()
                 for trace in compute_traces(observer)]
    lines = indicators + observers
    analyzers = {name: getattr(result.analyzers, name).get_analysis()
                 for name in analyzer_mapper}
    return {
        "datetime": dt,
        "ohlc": ohlc,
        "lines": lines,
        "analyzers": analyzers,
    }


@app.callback(
    Output("result-lines-graph", "figure"),
    [Input("backtest-store", "data")])
def update_figure(store_data):
    layout = go.Layout(title=f"Backtest results",
                       xaxis={"rangeslider": {"visible": False}},
                       yaxis={"title": f"Stock Price (USD)"})
    dt = store_data["datetime"]

    if dt == {}:
        return {"data": [], "layout": layout}

    ohlc = store_data["ohlc"]

    data = []
    data += [go.Candlestick(name="ohlc",
                            x=dt,
                            increasing={"line": {"color": "#00CC94"}},
                            decreasing={"line": {"color": "#F50030"}},
                            **ohlc)]
    for line in store_data["lines"]:
        plot_type = line.pop("plot_type")
        if plot_type == "Subplot":
            pass
        else:
            data += [go.Scatter(x=dt, **line)]

    return {"data": data, "layout": layout}


@app.callback(
    Output("result-trades-graph", "figure"),
    [Input("backtest-store", "data")])
def update_figure(store_data):
    layout = go.Layout(title=f"Trades Summary",
                       margin={"l": 300, "r": 300, },
                       legend={"x": 1, "y": 0.7})
    labels = ["Winning Longs", "Losing Longs",
              "Winning Shorts", "Losing Shorts"]
    colors = ["#8FE388", "#DD614A",
              "#58BC82", "#DF2935"]
    try:
        trades = store_data["analyzers"]["trades"]
        values = [trades["long"]["won"], trades["long"]["lost"],
                  trades["short"]["won"], trades["short"]["lost"]]
    except KeyError:
        return {"data": [], "layout": layout}

    trace = go.Pie(labels=labels,
                   values=values,
                   marker=dict(colors=colors),
                   textinfo="label")
    return {"data": [trace], "layout": layout}


if __name__ == "__main__":
    app.run_server(debug=True)
