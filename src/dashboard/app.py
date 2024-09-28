import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from kraken import Kraken
from dash import Dash
from dash import dcc
from dash import html
import plotly.graph_objects as go


mt5.initialize()

instr = "Step Index"

pst_rates = mt5.copy_rates_from_pos(instr, mt5.TIMEFRAME_H1, 0, 200)
sr_rates = mt5.copy_rates_from_pos(instr, mt5.TIMEFRAME_H6, 0, 250)

mt5.shutdown()

pst_df = pd.DataFrame(pst_rates)
sr_df = pd.DataFrame(sr_rates)

pst_df['time'] = pst_df['time'].apply(datetime.fromtimestamp)
pst_df.set_index('time', inplace=True)

sr_df['time'] = sr_df['time'].apply(datetime.fromtimestamp)
sr_df.set_index('time', inplace=True)

kraken = Kraken()

kraken.initialize(pst_data=pst_df, sr_data=sr_df)

annotation = kraken.get_annotation(prim_segments=10)

print(annotation['sr_zones'])

# creat figure1
figure1 = go.Figure(data=[go.Candlestick(x=pst_df.index, open=pst_df['open'], high=pst_df['high'], low=pst_df['low'], close=pst_df['close'])])
figure1.update_layout(height=800, xaxis_rangeslider_visible=False)
for position in annotation["primary"]["bos"]:
    if isinstance(position, datetime):
        figure1.add_vline(x=position, line_with=2, line_color="green")
# for position in annotation["primary"]["choc"]:
#     if isinstance(position, datetime):
#         figure1.add_shape(type="line", x0=position, x1=position, y0=annotation["primary"]["min"], y1=annotation["primary"]["max"], line=dict(color='purple', width=1))
# for position in annotation["primary"]["choc_confirm"]:
#     if isinstance(position, datetime):
#         figure1.add_shape(type="line", x0=position, x1=position, y0=annotation["primary"]["min"], y1=annotation["primary"]["max"], line=dict(color='red', width=1))

x = []
y = []
lastx = pst_df.index[-1]
print(lastx)

for zone in annotation["sr_zones"]:
    x_val = pst_df.index[0] if zone['x'] < pst_df.index[0] else zone['x']
    zx = [x_val, x_val, lastx, lastx, x_val, None]
    zy = [zone['interval'][0], zone['interval'][1], zone['interval'][1], zone['interval'][0], zone['interval'][0], None]
    x.extend(zx)
    y.extend(zy)

figure1.add_trace(go.Scatter(x=x, y=y, fill="toself"))

# creat figure2
figure2 = go.Figure(data=[go.Candlestick(x=sr_df.index, open=sr_df['open'], high=sr_df['high'], low=sr_df['low'], close=sr_df['close'])])
figure2.update_layout(height=800)

x = []
y = []
lastx = sr_df.index[-1]
print(lastx)

for zone in annotation["sr_zones"]:
    zx = [zone['x'], zone['x'], lastx, lastx, zone['x'], None]
    zy = [zone['interval'][0], zone['interval'][1], zone['interval'][1], zone['interval'][0], zone['interval'][0], None]
    x.extend(zx)
    y.extend(zy)

figure2.add_trace(go.Scatter(x=x, y=y, fill="toself"))

# start dash app
app = Dash(__name__)

app.layout = html.Div(
    children=[
        html.H1(children='Kraken Development'),
        html.P(children='Welcome to the Kraken visualization for testing'),
        html.H3(children='Entry time frame'),
        dcc.Graph(
            figure=figure1
        ),
        dcc.Graph(
            figure=figure2
        )
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)