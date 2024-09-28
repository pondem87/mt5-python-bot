import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os

mt5.initialize()

fmt = "%Y-%m-%d %H:%M:%S"

instr = "Step Index"
_from = datetime.strptime("2023-09-01 00:00:00", fmt)
_to = datetime.strptime("2023-12-15 23:59:00", fmt)

timeframes = [
    {
        "k": mt5.TIMEFRAME_M5,
        "str": "M5"
    },
    {
        "k": mt5.TIMEFRAME_H1,
        "str": "H1"
    },
    {
        "k": mt5.TIMEFRAME_H6,
        "str": "H6"
    },
    {
        "k": mt5.TIMEFRAME_H12,
        "str": "H12"
    },
    {
        "k": mt5.TIMEFRAME_D1,
        "str": "D1"
    }
]

for tf in timeframes:
    candle_data = mt5.copy_rates_range(
        instr,
        tf["k"],
        _from,
        _to
    )

    # convert to dataframe
    dframe = pd.DataFrame(candle_data)

    # change timestamp to datetime
    dframe["time"] = dframe["time"].apply(datetime.utcfromtimestamp)

    print(dframe.head())

    instr1 = instr.replace(" ", "_").lower()

    filepath = "instr_data/{}/{}_{}_{}_to_{}.csv".format(instr1, instr1, tf["str"], _from.strftime('%Y-%m-%d'), _to.strftime('%Y-%m-%d'))

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # save to csv
    dframe.to_csv(filepath, index=False)
