from enum import Enum

class DATA_TYPE:
    PST_DATA = 1
    SR_DATA = 2

class POSITION_TYPE(Enum):
    BUY = "BUY"
    SELL = "SELL"

class POSITION_STATE(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"