from config import strategy, options, extras
from animus import Animus
from datetime import datetime

animus = Animus()

animus.run_backtest(
    options["start_date"],
    options["end_date"],
    strategy,
    options,
    "instr_data\crash_1000_index_H1_2020-09-18_to_2023-11-30.csv",
    None,
    None
)