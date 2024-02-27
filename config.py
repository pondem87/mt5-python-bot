from constants import symbols
from kraken import Constants

strategy = "PRICE_ACTION"

symbol = symbols["Step Index"]

options = {
    "entry": "CHOC",                    # e.g "CHOC", "CHOC_CONFIRMED,
    "exit": "CHOC_CONFIRMED",
    "sl_level": "KEY_LEVEL",            # e.g "KEY_LEVEL", "SEGMENT_RANGE",
    "sl_level_margin": 0.1,             # e.g 0.1, 0.2,
    "reward_ratio": None,               # e.g 1.5, 2, 3, None,
    "pst_lookback_window": 1000,        # e.g 200, 250, 300,
    "sr_lookback_window": 2400,         # e.g 200, 250, 300,
    "sr_refresh_window": 250,
    "init_account_balance": 200,        # e.g 100,
    "risk_per_trade": 0.2,              # e.g 0.1, 0.4,
    "compound_risk": False,             # e.g True, False,
    "max_concurrent_trades": 2,         # e.g 5, 10
    "instr": symbol["name"],
    "symbol": symbol,
    "start_date": "2023-11-01 00:00:00",
    "end_date": "2023-11-30 00:00:00",
    "raw_pst_data": {
        Constants.PST_DATA_LEVEL.LOW.value: "instr_data/step_index/step_index_M5_2023-09-01_to_2023-12-15.csv",
        Constants.PST_DATA_LEVEL.MID.value: "instr_data/step_index/step_index_H1_2023-09-01_to_2023-12-15.csv",
        Constants.PST_DATA_LEVEL.HIGH.value: "instr_data/step_index/step_index_H6_2023-09-01_to_2023-12-15.csv"
    },
    "raw_sr_data": {
        Constants.SR_DATA_LEVEL.LOW.value: "instr_data/step_index/step_index_H6_2023-09-01_to_2023-12-15.csv",
        Constants.SR_DATA_LEVEL.HIGH.value: "instr_data/step_index/step_index_H12_2023-09-01_to_2023-12-15.csv",
    },
    "move_sl": {
        "allow": True,
        "to_break_even_at_r": 0.5,
        "trailing_at_r": 1.0
    },
    "exclude_high_trend": False,
    "sr_zone_interaction": "PROXIMITY", # e.g "PROXIMITY"
    "sr_zone_entry_margin": 0.3,
    "sr_zone_proximity_margin": 0.3,
    "sr_zone_clearence_factor": 2.0
}

extras = {
    "pst_data_timeframes": "M15, H1, H6",
    "sr_data_timeframes": "H6, H12"
}

"""
settings used during simulation

    "sim_speed": number of seconds to pause between processing each candle
    "publish_cycle": number of cycles or candles processed before simulation state is published
    "publish_live_data": True or False, if true data will be sent to dashboard during siulation
    "annotation_candle_length": The number of candles that will be displayed from the the last processed candle

"""
simulation = {
    "sim_speed": 0.5,
    "publish_cycle":2,
    "publish_live_data": True,
    "annotation_candle_length": 200
}