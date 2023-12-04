import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

mt5.initialize()

fmt = "%Y-%m-%d %H:%M:%S"

candle_data = mt5.copy_rates_from(
    "Step Index",
    mt5.TIMEFRAME_M15,
    datetime.strptime("2023-11-30 00:00:00", fmt),
    4032    # 72 days
)

# convert to dataframe
dframe = pd.DataFrame(candle_data)

# change timestamp to datetime
dframe["time"] = dframe["time"].apply(datetime.utcfromtimestamp)

print(dframe.head())

# save to csv
dframe.to_csv("instr_data/step_index_M15_2020-10-18_to_2023-11-30.csv", index=False)
