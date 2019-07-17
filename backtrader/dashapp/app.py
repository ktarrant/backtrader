import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

import backtrader as bt

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

dataname = "snapshots/2019-06-25_SIN9.csv"

ibdata = bt.feeds.IBCSVData(dataname=dataname)

cerebro = bt.Cerebro()
cerebro.adddata(ibdata)

result_list = cerebro.run()

result = result_list[0]

app.layout = html.Div(children=[
    html.H1(children='Backtrader Run'),

    html.Div(id="dataname-field", children=f"{dataname}"),

    dcc.Graph(id='result-graph'),
])

@app.callback(
    Output("result-graph", 'figure'),
    [Input("dataname-field", 'children')])
def update_figure(dataname):
    arrays = {key: list(getattr(result.data.lines, key).array)
              for key in ["open", "high", "low", "close"]}
    arrays["x"] = [bt.num2date(d) for d in result.data.lines.datetime.array]

    trace = go.Candlestick(increasing={'line': {'color': '#00CC94'}},
                           decreasing={'line': {'color': '#F50030'}},
                           **arrays)
    return {'data': [trace],
            'layout': go.Layout(title=f"Backtest results",
                                xaxis={'rangeslider': {'visible': False}},
                                yaxis={"title": f'Stock Price (USD)'})}

if __name__ == '__main__':
    app.run_server(debug=True)