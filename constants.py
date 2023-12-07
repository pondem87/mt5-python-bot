symbols = {
    "Step Index": {
        "name": "Step Index",
        "type": "Synthetic",
        "trade_contract_size": 10,
        "volume_min": 0.1,
        "volume_max": 20.0,
        "currency_base": "USD",
        "description": "Equal probability of up/down with fixed step size of 0.1"
    },
    "Volatility 75 Index": {
        "name": "Volatility 75 Index",
        "type": "Synthetic",
        "trade_contract_size": 1.0,
        "volume_min": 0.001,
        "volume_max": 1.0,
        "currency_base": "USD",
        "description": "Constant Volatility of 75% with a tick every 2 seconds"
    },
    "Volatility 75 (1s) Index": {
        "name": "Volatility 75 (1s) Index",
        "type": "Synthetic",
        "trade_contract_size": 1.0,
        "volume_min": 0.05,
        "volume_max": 10.0,
        "currency_base": "USD",
        "description": "Constant Volatility of 75% with a tick every 1 seconds"
    }
}