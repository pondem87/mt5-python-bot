from constants import symbols
from kraken import Constants

strategy = "SIMPLE_TREND"

symbol = symbols["Step Index"]

options = {
    "entry": "CHOC",                    # e.g "CHOC", "CHOC_CONFIRMED,
    "exit": "CHOC_CONFIRMED",
    "sl_level": "SEGMENT_RANGE",        # e.g "KEY_LEVEL", "SEGMENT_RANGE",
    "sl_level_margin": 0.2,             # e.g 0.1, 0.2,
    "reward_ratio": None,               # e.g 1.5, 2, 3, None,
    "pst_lookback_window": 350,         # e.g 200, 250, 300,
    "sr_lookback_window": 300,          # e.g 200, 250, 300,
    "init_account_balance": 100,        # e.g 100,
    "risk_per_trade": 0.2,              # e.g 0.1, 0.4,
    "compound_risk": False,             # e.g True, False,
    "max_concurrent_trades": 5,         # e.g 5, 10
    "instr": symbol["name"],
    "symbol": symbol,
    "start_date": "2023-11-01 00:00:00",
    "end_date": "2023-11-15 00:00:00",
    "raw_pst_data": {
        Constants.PST_DATA_LEVEL.LOW.value: "instr_data\step_index\step_index_M15_2023-10-01_to_2023-11-30.csv",
        Constants.PST_DATA_LEVEL.MID.value: "instr_data\step_index\step_index_H1_2023-10-01_to_2023-11-30.csv",
        Constants.PST_DATA_LEVEL.HIGH.value: "instr_data\step_index\step_index_H4_2023-10-01_to_2023-11-30.csv"
    },
    "raw_sr_data": {
        Constants.SR_DATA_LEVEL.LOW.value: "instr_data\step_index\step_index_H4_2023-10-01_to_2023-11-30.csv",
        Constants.SR_DATA_LEVEL.HIGH.value: "instr_data\step_index\step_index_M12_2023-10-01_to_2023-11-30.csv",
    },
    "move_sl": {
        "allow": True,
        "to_break_even_at_r": 1.0,
        "trailing_at_r": 1.2
    }
}

extras = {
    "pst_data_timeframes": "M15, H1, H4",
    "sr_data_timeframes": "H4, H12"
}