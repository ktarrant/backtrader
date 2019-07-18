import os

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import jsonpickle

import backtrader as bt


# ------------------------------------------------------------------------------
# Static Configuration
# ------------------------------------------------------------------------------
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

local_dir = "snapshots"


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

    dcc.Store(id="backtest-store", data={"ohlc": ""}),

    dcc.Graph(id="result-graph"),
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

@app.callback(
    Output("backtest-store", "data"),
    [Input("dataname-field", "children")])
def update_store(dataname):
    if not dataname:
        return {"ohlc": ""}
    # Run the backtest!
    cerebro = bt.Cerebro()
    ibdata = bt.feeds.IBCSVData(dataname=dataname)
    cerebro.adddata(ibdata)
    result_list = cerebro.run()
    result = result_list[0]
    arrays = {key: list(getattr(result.data.lines, key).array)
              for key in ["open", "high", "low", "close"]}
    arrays["x"] = [bt.num2date(d) for d in result.data.lines.datetime.array]
    return {"ohlc": jsonpickle.encode(arrays)}

@app.callback(
    Output("result-graph", "figure"),
    [Input("backtest-store", "data")])
def update_figure(data):
    layout = go.Layout(title=f"Backtest results",
                       xaxis={"rangeslider": {"visible": False}},
                       yaxis={"title": f"Stock Price (USD)"})
    arrays_data = data["ohlc"]

    if arrays_data == "":
        return {"data": [], "layout": layout}

    arrays = jsonpickle.decode(arrays_data)

    trace = go.Candlestick(increasing={"line": {"color": "#00CC94"}},
                           decreasing={"line": {"color": "#F50030"}},
                           **arrays)
    return {"data": [trace], "layout": layout}

if __name__ == "__main__":
    app.run_server(debug=True)
