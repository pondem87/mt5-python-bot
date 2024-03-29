﻿## Python MT5 Bot

This program is meant to connect with the MT5 trading platforming and implement algorithmic trading strategies.
It allows backtesting of strategies on historic data and ultmately place trades on the live platform.
During backtesting one can visualise in a candlestick chart how the trades are being made as the simulation progresses at various configurable speeds.
Dash and plotly graphs are used to display simulation status.

Strategies implemented are price action, ICT, trends

## Implementation

### Modules
#### kraken.py
Takes in a dataframe of candlestick data and parses it and applies ICT principles to mark structure, break of structure, change of character etc.
The different timeframes are parsed simultaneously and annotated.
Also parses two other timeframes to mark support and resistance zones.
Returns annotated data to another module which implements strategies.

#### animus.py
Implements strategies using data from kraken.py
Many different strategies are available and this module contains the algorithms necessary.
It can go through historic and live candldes, passing them on to kraken and receiving annotation data which it uses to make trade decisions.
During simulation it returns data necessary for visualisation.

#### generate_data.py
Generates data for simulation. Uses mt5-python extension to obtain required data from the broker.

#### app.py
Put everything together and initiates the simulation

#### config.py
Sets options for simuation and strategy implementation

#### dashboard.py
Sets up a dash server to display simulation progress an visualisation of trades, profit and loss.

### screenshots
![kraken1](https://github.com/pondem87/mt5-python-bot/assets/65922214/5b3be92e-030e-4659-b05d-7fd25a999c92)
![kraken2](https://github.com/pondem87/mt5-python-bot/assets/65922214/6b68cf73-030d-483f-a871-6ade8aff4353)
![kraken4](https://github.com/pondem87/mt5-python-bot/assets/65922214/9832b26e-f355-4167-8a75-4e576a5b8e92)
![kraken5](https://github.com/pondem87/mt5-python-bot/assets/65922214/690283b9-4038-41b5-843f-0ef501580ae9)
