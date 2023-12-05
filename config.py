from datetime import datetime

strategy = "SIMPLE_TREND"

options = {
    "entry": "CHOC",          # e.g "CHOC", "CHOC_CONFIRMED,
    "exit": "CHOC_CONFIRMED",
    "sl_level": "SEGMENT_RANGE",   # e.g "KEY_LEVEL", "SEGMENT_RANGE",
    "sl_level_margin": 0.2,             # e.g 0.1, 0.2,
    "reward_ratio": 1.5,               # e.g 1.5, 2, 3, None,
    "pst_lookback_window": 350,         # e.g 200, 250, 300,
    "sr_lookback_window": 300,          # e.g 200, 250, 300,
    "init_account_balance": 100,        # e.g 100,
    "risk_per_trade": 0.1,              # e.g 0.1, 0.4,
    "compound_risk": False,             # e.g True, False,
    "max_concurrent_trades": 5,         # e.g 5, 10
    "instr": "Step Index",
    "trade_contract_size": 10,
    "start_date": "2023-11-01 00:00:00",
    "end_date": "2023-11-15 00:00:00"
}

extras = {
    "pst_data_timeframe": "M15",
    # "sr_data_timeframe": "H6",
}