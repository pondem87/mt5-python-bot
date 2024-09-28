from dash import Dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import json
import pandas as pd
from datetime import datetime
import pika
from threading import Thread

dtfmt = "%Y-%m-%d %H:%M:%S"

sim_data = json.dumps({"bars": [], "annotation": {}})


# start dash app
app = Dash(__name__)

app.layout = html.Div(
    children=[
        html.H1(children='Kraken Strategy Simulation'),
        html.H3(id='account', children='Entry time frame'),
        html.P(id='levels'),
        html.H3(id='title', children='Entry time frame'),
        dcc.Interval(id='interval-comp', interval=1000, n_intervals=0),
        dcc.Graph(id="main-chart"),
        html.P(id='desc', children='Welcome to the Kraken visualization for testing')
    ]
)

# callback to update graph
@app.callback(
    [Output('main-chart', 'figure'),
     Output('title', 'children'),
     Output('desc', 'children'),
     Output('account', 'children'),
     Output('levels', 'children')],
    [Input("interval-comp", "n_intervals")]
)
def update_progress(n_intervals):
    # get the data

    data = json.loads(sim_data)

    pst_df = pd.DataFrame(data["bars"])
    pst_df.set_index("time", inplace=True)
    annotation = data["annotation"]
    trades = data["trades"]
    options = data["options"]

    # get start of data
    x_begin = datetime.strptime(pst_df.iloc[0].name, dtfmt)
    x_end = datetime.strptime(pst_df.iloc[-1].name, dtfmt)
    y_max = pst_df["high"].max()
    y_min = pst_df["low"].min()

    # creat figure1
    figure1 = go.Figure(data=[go.Candlestick(x=pst_df.index, open=pst_df['open'], high=pst_df['high'], low=pst_df['low'], close=pst_df['close'])])
    figure1.update_layout(height=700, xaxis_rangeslider_visible=False)

    # add structure annotation
    for position in annotation["pst_low"]["bos"]:
        if position is not None:
            position = datetime.strptime(position, dtfmt)
            if position > x_begin:
                figure1.add_vline(x=position, line_width=1, line_color="green")
    for position in annotation["pst_low"]["choc"]:
        if position is not None:
            position = datetime.strptime(position, dtfmt)
            if position > x_begin:
                figure1.add_vline(x=position, line_width=1, line_color="purple")
    for position in annotation["pst_low"]["choc_confirm"]:
        if position is not None:
            position = datetime.strptime(position, dtfmt)
            if position > x_begin:
                figure1.add_vline(x=position, line_width=1, line_color="red")

    # add trade annotation
    tpx = []
    tpy = []
    slx = []
    sly = []

    for trade in trades:
        # only trades that are not closed or fit in the current window will be plotted
        if trade["exit_time"] is None or datetime.strptime(trade["exit_time"], dtfmt) >= x_begin:

            if datetime.strptime(trade["entry_time"], dtfmt) > x_begin:
                # this case where trade starts within window thus the left border is determined by entry time
                farleft = trade["entry_time"]
            else:
                # entry is outside window
                farleft = x_begin

            # if not yet closed the box will extend to the end i.e x_end
            if trade["exit_time"] is None:
                farright = x_end
            else:
                farright = trade["exit_time"]

            # if tp is not set box tp box follows current price
            if trade["close"] is None and trade["tp"] is None:
                # now it depends on direction of trade vs current price
                if trade["type"] == "BUY" and trade["price"] < pst_df.iloc[-1]["close"]:
                    # a buy trade in profit will have tp box to current price
                    tpboxbound = pst_df.iloc[-1]["close"]
                elif trade["type"] == "SELL" and trade["price"] > pst_df.iloc[-1]["close"]:
                    # a sell trade in profit will have tp box to current price
                    tpboxbound = pst_df.iloc[-1]["close"]
                else:
                    tpboxbound = None
            elif trade["tp"] is None and trade["close"] is not None:
                # now it depends on direction of trade vs current price
                if trade["type"] == "BUY" and trade["price"] < trade["close"]:
                    # a closed buy trade in profit will have tp box to close price
                    tpboxbound = trade["close"]
                elif trade["type"] == "SELL" and trade["price"] > trade["close"]:
                    # a closed sell trade in profit will have tp box to close price
                    tpboxbound = trade["close"]
                else:
                    tpboxbound = None
            elif trade["tp"] is not None:
                tpboxbound = trade["tp"]
            else:
                tpboxbound = None



            # now lets build the boxes
            # if tpboxbound available build a tp box
            if tpboxbound is not None:
                _tpx = [farleft, farleft, farright, farright, farleft, None]
                _tpy = [trade["price"], tpboxbound, tpboxbound, trade["price"], trade["price"], None]
                tpx.extend(_tpx)
                tpy.extend(_tpy)

            # now lets draw the sl box
            _slx = [farleft, farleft, farright, farright, farleft, None]
            _sly = [trade["price"], trade["sl"], trade["sl"], trade["price"], trade["price"], None]
            slx.extend(_slx)
            sly.extend(_sly)

            # lets put the trailing stop loss
            figure1.add_shape(type="line",
              x0=farleft, 
              y0=trade["tsl"], 
              x1=farright, 
              y1=trade["tsl"],
              line=dict(color='purple', width=2))


    # add profit region
    figure1.add_trace(go.Scatter(x=tpx, y=tpy, fill="toself", line=dict(color='green', width=1)))
    # add loss region
    figure1.add_trace(go.Scatter(x=slx, y=sly, fill="toself", line=dict(color='red', width=1)))

    # print zones near price action
    x = []
    y = []
    lastx = x_end

    for zone in annotation["sr_zones"]:
        if zone['interval'][0] <= y_max + (y_max - y_min) * 0.1 and \
            zone['interval'][1] >= y_min - (y_max - y_min) * 0.1:
            # show zones that are within 10% of min and max price in window
            x_val = x_begin if datetime.strptime(zone['x'], dtfmt) < x_begin else zone['x']
            zx = [x_val, x_val, lastx, lastx, x_val, None]
            zy = [zone['interval'][0], zone['interval'][1], zone['interval'][1], zone['interval'][0], zone['interval'][0], None]
            x.extend(zx)
            y.extend(zy)

    figure1.add_trace(go.Scatter(x=x, y=y, fill="toself", line=dict(color='blue', width=1)))


    title = "{}: from {} to {}".format(
        options["instr"], options["start_date"], options["end_date"]
    )

    desc = "Options: {}".format(options)

    levels = "Timeframes: {} - trend {}, choc {};  {} - trend {}, choc {};  {} - trend {}, choc {};".format(
        annotation["pst_low"]["timeframe"],
        annotation["pst_low"]["dir"],
        annotation["pst_low"]["in_choc"],
        annotation["pst_mid"]["timeframe"],
        annotation["pst_mid"]["dir"],
        annotation["pst_mid"]["in_choc"],
        annotation["pst_high"]["timeframe"],
        annotation["pst_high"]["dir"],
        annotation["pst_high"]["in_choc"]
    )

    account = "INITIAL BALANCE: {}, CURRENT BALANCE: {}, EQUITY: {}".format(
        annotation["account"]["initial_balance"],
        annotation["account"]["balance"],
        annotation["account"]["equity"]
    )
        
    return figure1, title, desc, account, levels


def received_message(ch, method, properties, data):
    global sim_data
    sim_data = data

def run_pika():
    # establish pika connenction and queue
    conn_params = pika.ConnectionParameters("localhost")
    conn = pika.BlockingConnection(conn_params)
    channel = conn.channel()
    channel.queue_declare("mt5_sim_data")
    channel.basic_consume("mt5_sim_data", received_message, auto_ack=True)
    channel.start_consuming()

if __name__ == "__main__":

    Thread(target=run_pika, daemon=True).start()

    app.run_server(debug=True)