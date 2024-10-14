from enum import Enum

# direction of trend
class DIRECTION(Enum):
    UP = "UP"
    DOWN = "DOWN"
    UNDETERMINED = "?"

# used to identify price action support and resistance
class ZONE_TYPE(Enum):
    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"

# which part of candle is used as level of interest
class ZONING_MODE(Enum):
    CANDLE = "CANDLE"
    BODY = "BODY"
    WICK = "WICK"

# when looking at candlestick data for price action, we look at three diffent timeframes
# low is the smallest timeframe candlestick data, while high is the largest timeframe
class PST_DATA_LEVEL(Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"

# when looking at candlestick data for support and resistane levels, we look at two diffent timeframes
# low is the smallest timeframe candlestick data, while high is the largest timeframe
class SR_DATA_LEVEL(Enum):
    LOW = "low"
    HIGH = "high"