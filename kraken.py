"""
Developed by Tendai Pfidze
Start 21 November 2023

Kraken is a price structure detection engine which classifies candle patterns based on ICT principles.
The algo will create an object based representation of price structure and generate signals.
The working principle is that price has internal and external structures. The representation will be based
on three levels named primary, secondary and tertiary structures

"""

from typing import List, Tuple
from datetime import datetime
import pandas as pd
from uuid import uuid4
from enum import Enum
import logging

# set up logging
logger = logging.getLogger(__name__)
# set general log level
logger.setLevel("DEBUG")
# shared log formatter
formatter = logging.Formatter("%(asctime)s : %(name)s [%(funcName)s] : %(levelname)s -> %(message)s")

# create log handlers
# general, contains all logs
general_file_handler = logging.FileHandler("log/kraken.log")
general_file_handler.setFormatter(formatter)
# warning, contains warn and higher level logs
warn_file_handler = logging.FileHandler("log/kraken.warn.log")
warn_file_handler.setFormatter(formatter)
warn_file_handler.setLevel("WARN")

# add handlers to logger
logger.addHandler(general_file_handler)
logger.addHandler(warn_file_handler)


"""
Define some enums to avoid using string literals for common options
"""
class Constants:
    class DIRECTION(Enum):
        UP = "UP"
        DOWN = "DOWN"
        UNDETERMINED = "?"

    class ZONE_TYPE(Enum):
        SUPPORT = "SUPPORT"
        RESISTANCE = "RESISTANCE"

    class ZONING_MODE(Enum):
        CANDLE = "CANDLE"
        BODY = "BODY"
        WICK = "WICK"

    class PST_DATA_LEVEL(Enum):
        LOW = "low"
        MID = "mid"
        HIGH = "high"

    class SR_DATA_LEVEL(Enum):
        LOW = "low"
        HIGH = "high"

"""
Class for working on candles. Provides access to candle properties and useful operations on candle data
"""
class Candle:
    def __init__(self, timestamp:datetime, open:float, high:float, low:float, close:float) -> None:
        self._timestamp: datetime = timestamp
        self._open: float = open
        self._high: float = high
        self._low: float = low
        self._close: float = close

    # basic candle properties
    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def open(self) -> float:
        return self._open
    
    @property
    def high(self) -> float:
        return self._high
    
    @property
    def low(self) -> float:
        return self._low
    
    @property
    def close(self) -> float:
        return self._close
    

    # determine wether bearish or bullish
    @property
    def dir(self) -> str:
        if self._close > self._open:
            return Constants.DIRECTION.UP
        else:
            return Constants.DIRECTION.DOWN


"""
Class for common segment features. Shared by all segment levels.
"""
class BaseSegment:
    def __init__(self,
                 time_frame: str,
                 dir: Constants.DIRECTION = Constants.DIRECTION.UNDETERMINED,
                 key_low: float = None,
                 key_high: float = None,
                 last_low: float = None,
                 last_high: float = None,
                 key_low_candle: float = None,
                 key_high_candle: float = None,
                 last_low_candle: float = None,
                 last_high_candle: float = None) -> None:
        self._time_frame: str = time_frame
        self._dir: str = dir                 # direction of market "UP" or "DOWN" or "?"
        self._key_high: float = key_high     # in UP segment = BOS level, in DOWN segment = ChOC level
        self._key_low: float = key_low       # in DOWN segment = BOS level, in UP segment = ChOC level
        self._last_high: float = last_high   # tracks the highest high before BOS in a downtrend
        self._last_low: float = last_low     # tracks the lowest low before BOS in a uptrend

        self._key_high_candle: datetime = key_high_candle
        self._key_low_candle: datetime = key_low_candle
        self._last_high_candle: datetime = last_high_candle
        self._last_low_candle: datetime = last_low_candle

        # uninitialized instances variables
        self._choc: bool = False                # True if in unconfirmed ChOC
        self._choc_confirmed: bool = False      # True marks end of segment
        self._segment_high: float = None        # Highest price in segment
        self._segment_low: float = None         # Lowest price in segment
        self._bos_num: int = 0                  # Number of structure breaks (BOS)
        self._in_bos: bool = True
        self._in_pull_back: bool = False        # Price must pull back to be legible for new BOS
        self._in_choc_pull_back: bool = False   # Price must pull back to be legible for new BOS and ChOC confirm


    # access instance variables as properties
    @property
    def time_frame(self) -> str:
        return self._time_frame

    @property
    def choc(self) -> bool:
        return self._choc
    
    @property
    def choc_confirmed(self) -> bool:
        return self._choc_confirmed
    
    @property
    def segment_high(self) -> float:
        return self._segment_high
    
    @property
    def segment_low(self) -> float:
        return self._segment_low
    
    @property
    def dir(self) -> Constants.DIRECTION:
        return self._dir
    
    @property
    def key_high(self) -> float:
        return self._key_high
    
    @property
    def key_low(self) -> float:
        return self._key_low
    
    @property
    def last_high(self) -> float:
        return self._last_high
    
    @property
    def last_low(self) -> float:
        return self._last_low
    
    @property
    def bos_num(self) -> int:
        return self._bos_num
    
    @property
    def in_bos(self):
        return self._in_bos
    
    @property
    def in_pull_back(self):
        return self._in_pull_back

    # maximum price range of segment
    @property
    def segment_range(self) -> float:
        if self.segment_high is not None and self.segment_low is not None:
            return self.segment_high - self.segment_low
        else:
            return None
        
    @property
    def opp_dir(self) -> Constants.DIRECTION:
        return Constants.DIRECTION.DOWN if self._dir == Constants.DIRECTION.UP else Constants.DIRECTION.UP    

"""
A primary segment contains a set of candles that are part of a structure an 'uptrend' or 'downtrend'
A new segment starts after a confirmed ChOC
"""
class PrimarySegment(BaseSegment):
    def __init__(self,
                 seg_id: str,
                 time_frame: str,
                 dir: Constants.DIRECTION = Constants.DIRECTION.UNDETERMINED,
                 key_low: float = None,
                 key_high: float = None,
                 last_low: float = None,
                 last_high: float = None,
                 key_low_candle: float = None,
                 key_high_candle: float = None,
                 last_low_candle: float = None,
                 last_high_candle: float = None) -> None:
        super().__init__(   time_frame=time_frame,
                            dir=dir,
                            key_low=key_low,
                            key_high=key_high,
                            last_low=last_low,
                            last_high=last_high,
                            key_low_candle=key_low_candle,
                            key_high_candle=key_high_candle,
                            last_low_candle=last_low_candle,
                            last_high_candle=last_high_candle)
        self._seg_id = seg_id
        logger.info("New primary structure segment: id= %s, timefame = %s, dir= %s", seg_id, self._time_frame,self._dir)

        # uninitialized instances variables
        self._candles: List[datetime] = []              # List of candles within segment identified by datetime
        self._bos_candles: List[datetime] = []          # List of candles within segment where there was BOS identified by datetime
        self._choc_candles: List[datetime] = []         # List of candles within segment where there was ChOC identified by datetime
        self._key_high_candles: List[datetime] = []     # List of higher or lower high candles
        self._key_low_candles: List[datetime] = []      # List of higher or lower low candles
        self._highest_candle: datetime = None
        self._lowest_candle: datetime = None
        self._choc_confirm_candle: datetime = None


    # access instance variables as properties
    @property
    def candles(self) -> List[datetime]:
        return self._candles
    
    @property
    def highest_candle(self) -> datetime:
        return self._highest_candle
    
    @property
    def lowest_candle(self) -> datetime:
        return self._lowest_candle
    
    @property
    def seg_id(self) -> str:
        return self._seg_id
    
    @property
    def bos_candles(self) -> List[datetime]:
        return self._bos_candles
    
    @property
    def choc_candles(self) -> List[datetime]:
        return self._choc_candles
    
    @property
    def choc_confirm_candle(self) -> datetime:
        return self._choc_confirm_candle
    
    @property
    def last_high_candle(self) -> datetime:
        return self._last_high_candle
    
    @property
    def last_low_candle(self) -> datetime:
        return self._last_low_candle
    
    @property
    def key_high_candle(self) -> datetime:
        return self._key_high_candle
    
    @property
    def key_low_candle(self) -> datetime:
        return self._key_low_candle
    
    @property
    def key_high_candles(self) -> List[datetime]:
        return self._key_high_candles
    
    @property
    def key_low_candles(self) -> List[datetime]:
        return self._key_low_candles

    # set last lows and highs
    def set_last_high_low(self, candle: Candle):
        if not (self._dir == Constants.DIRECTION.DOWN and self._in_bos):
            if self._last_high is None:
                self._last_high = candle.high
                self._last_high_candle = candle.timestamp
            elif self._last_high < candle.high:
                self._last_high = candle.high
                self._last_high_candle = candle.timestamp

        if not (self._dir == Constants.DIRECTION.UP and self._in_bos): 
            if self._last_low is None:
                self._last_low = candle.low
                self._last_low_candle = candle.timestamp
            elif self._last_low > candle.low:
                self._last_low = candle.low
                self._last_low_candle = candle.timestamp


    # set the lowest and highest points in the segment
    def update_segment_high_low(self, candle: Candle):
        if self._segment_high is None:
            self._segment_high = candle.high
            self._highest_candle = candle.timestamp
        elif self.segment_high < candle.high:
            self._segment_high = candle.high
            self._highest_candle = candle.timestamp

        if self._segment_low is None:
            self._segment_low = candle.low
            self._lowest_candle = candle.timestamp
        elif self._segment_low > candle.low:
            self._segment_low = candle.low
            self._lowest_candle = candle.timestamp


    # returns number of candles in the segment
    def candle_count(self) -> int:
        return len(self.candles)
    
    # adds new candle to structure and determines candle side effects
    def add_candle(self, candle: Candle) -> None:

        logger.debug("Primary Segment(%s) adding candle(%s, high: %s, low: %s)", self._time_frame, candle.timestamp, candle.high, candle.low)
        logger.debug("Primary Segment(%s) state: dir: %s key high: %s, key low: %s, last high: %s, last low: %s", self._time_frame, self._dir, self._key_high, self._key_low, self._last_high, self._last_low)
        
        # add candle to segment
        self._candles.append(candle.timestamp)
        # update highest and lowest candle
        self.update_segment_high_low(candle)

        match self._dir:
            case Constants.DIRECTION.UNDETERMINED:
                # if first segment and dir is not yet set - set all parameter according to first candle
                self._dir = candle.dir
                self._key_high = candle.high
                self._key_high_candle = candle.timestamp
                self._key_low = candle.low
                self._key_low_candle = candle.timestamp
                self._in_bos = True
                self.set_last_high_low(candle)
                return
            
            case Constants.DIRECTION.UP:
                logger.debug("case UP matched in add_candle function")
                # if price hasnt pulled back since last BOS, check for pull back
                if not self._in_pull_back and self._in_bos:
                    if candle.dir == Constants.DIRECTION.DOWN:
                        # if candle is bearish, set _in_pull_back to true
                        self._in_pull_back = True
                        self._in_bos = False
                        self._key_high = self._last_high
                        self._key_high_candle = self._last_high_candle
                        self._key_high_candles.append(self._last_high_candle)
                        logger.info("%s UPTREND: BOS pull back at %s, new key high at %s", self._time_frame, candle.timestamp, self._key_high)

                # if price hasnt pulled back since getting into ChOC, check for pull back
                if self.choc and not self._in_choc_pull_back:
                    if candle.dir == Constants.DIRECTION.UP:
                        # if candle is bearish, set _in_pull_back to true
                        self._in_choc_pull_back = True
                        self._key_low = self._last_low
                        self._key_low_candle = self._last_low_candle
                        self._key_low_candles.append(self._last_low_candle)
                        self._last_high = candle.high
                        self._last_high_candle = candle.timestamp
                        logger.info("%s UPTREND: ChOC pull back at %s, lower low = %s", self._time_frame, candle.timestamp, self._key_low)

                # check for BOS and ChOC in that order
                if candle.close > self._key_high and self._in_pull_back and candle.dir == Constants.DIRECTION.UP:
                    # BOS
                    self._bos_num = self._bos_num + 1
                    self._in_pull_back = False
                    self._in_choc_pull_back = False
                    self._choc = False
                    self._in_bos = True
                    self._bos_candles.append(candle.timestamp)

                    # update last low and set key low
                    if self._last_low is None or candle.low < self._last_low:
                        self._key_low = candle.low
                        self._key_low_candle = candle.timestamp
                        self._key_low_candles.append(candle.timestamp)
                    else:
                        self._key_low = self._last_low
                        self._key_low_candle = self._last_low_candle
                        self._key_low_candles.append(self._last_low_candle)

                    self._last_low = None
                    self._last_low_candle = None
                    logger.info("%s UPTREND: BOS at %s, higher low = %s", self._time_frame, candle.timestamp, self._key_low)
                    
                elif candle.close < self._key_low:
                    # ChOC or ChOC confirm
                    if not self._choc:
                        self._choc = True
                        self._last_low = candle.low
                        self._last_low_candle = candle.timestamp
                        self._choc_candles.append(candle.timestamp)
                        logger.info("%s UPTREND: ChOC at %s", self._time_frame, candle.timestamp)
                    elif self._choc and self._in_choc_pull_back:
                        # this condition satisfies choc confirmation
                        self._choc_confirmed = True
                        self._key_high = self._last_high
                        self._key_high_candle = self._last_high_candle
                        self._key_high_candles.append(self._last_high_candle)
                        self._last_low = candle.low
                        self._last_low_candle = candle.timestamp
                        self._choc_confirm_candle = candle.timestamp
                        logger.info("%s UPTREND: ChOC confirmation at %s", self._time_frame, candle.timestamp)

            case Constants.DIRECTION.DOWN:
                logger.debug("DOWN case match")
                # if price hasnt pulled back since last BOS, check for pull back
                if not self._in_pull_back and self._in_bos:
                    if candle.dir == Constants.DIRECTION.UP:
                        # if candle is bearish, set _in_pull_back to true
                        self._in_pull_back = True
                        self._in_bos = False
                        self._key_low = self._last_low
                        self._key_low_candle = self._last_low_candle
                        self._key_high_candles.append(self._last_high_candle)
                        logger.info("%s DOWNTREND: BOS pull back at %s, new key low at %s", self._time_frame, candle.timestamp, self._key_low)

                # if price hasnt pulled back since getting into ChOC, check for pull back
                if self.choc and not self._in_choc_pull_back:
                    if candle.dir == Constants.DIRECTION.DOWN:
                        # if candle is bearish, set _in_pull_back to true
                        self._in_choc_pull_back = True
                        self._key_high = self._last_high
                        self._key_high_candle = self._last_high_candle
                        self._key_high_candles.append(self._last_high_candle)
                        self._last_low = candle.low
                        self._last_low_candle = candle.timestamp
                        logger.info("%s DOWNTREND: ChOC pull back at %s, higher high = %s", self._time_frame, candle.timestamp, self._key_high)

                # check for BOS and ChOC in that order
                if candle.close < self._key_low and self._in_pull_back  and candle.dir == Constants.DIRECTION.DOWN:
                    # BOS
                    self._bos_num = self._bos_num + 1
                    self._in_pull_back = False
                    self._in_choc_pull_back = False
                    self._choc = False
                    self._in_bos = True
                    self._bos_candles.append(candle.timestamp)

                    # update last high and set key high
                    if self._last_high is None or candle.high > self._last_high:
                        self._key_high = candle.high
                        self._key_high_candle = candle.timestamp
                        self._key_high_candles.append(candle.timestamp)
                    else:
                        self._key_high = self._last_high
                        self._key_high_candle = self._last_high_candle
                        self._key_high_candles.append(self._last_high_candle)
                    
                    self._last_high = None
                    self._last_high_candle = None
                    logger.info("%s DOWNTREND: BOS at %s, lower high = %s", self._time_frame, candle.timestamp, self._key_high)

                elif candle.close > self._key_high:
                    # ChOC or ChOC confirm
                    if not self._choc:
                        self._choc = True
                        self._last_high = candle.high
                        self._last_high_candle = candle.timestamp
                        self._choc_candles.append(candle.timestamp)
                        logger.info("%s DOWNTREND: ChOC at %s", self._time_frame, candle.timestamp)
                    elif self._choc and self._in_choc_pull_back:
                        # this condition satisfies choc confirmation
                        self._choc_confirmed = True
                        self._key_low = self._last_low
                        self._key_low_candle = self._last_low_candle
                        self._key_low_candles.append(self._last_low_candle)
                        self._last_high = candle.high
                        self._last_high_candle = candle.timestamp
                        self._choc_confirm_candle = candle.timestamp
                        logger.info("%s DOWNTREND: ChOC confirmation at %s", self._time_frame, candle.timestamp)            

        self.set_last_high_low(candle)


"""
SR_Container
This class handles the higher timeframe structure and parses out the support and resistance regions.
We still use ICT concepts to monitor trends and inflexion points
"""
class SR_Structure:

    """
    RSR_Zone
    Class for handling support and resistance zone data
    """
    class RSR_Zone:
        def __init__(self,
                     type: Constants.ZONE_TYPE,
                     x: datetime, 
                     full_candle: Tuple[float, float],
                     body:Tuple[float, float],
                     wick: Tuple[float, float]) -> None:
            self._type = type
            self._full_candle = full_candle
            self._body = body
            self._wick = wick
            self._x = x

            logger.info("SR zone type %s identified at %s with range %s to %s", self._type, self._x, self._full_candle[0], self._full_candle[1])
        
        @property
        def x(self) -> datetime:
            return self._x
        
        @property
        def type(self) -> Constants.ZONE_TYPE:
            return self._type

        @property
        def full_candle(self) -> Tuple[float, float]:
            return self._full_candle
        
        @property
        def body(self) -> Tuple[float, float]:
            return self._body
        
        @property
        def wick(self) -> Tuple[float, float]:
            return self._wick
        

    """
    RSR_Zone
    Class for handling aggregated support and resistance zones
    """    
    class ASR_Zone:
        def __init__(self, type: Constants.ZONE_TYPE, x: datetime, interval: List[float]) -> None:
            self._type = type
            self._interval: List[float] = interval  # contains [lower_bound, upper_bound]
            self._retests: int = 0
            self._x: datetime = x
            self._id: str = str(uuid4())

            logger.info("Aggregated SR zone (id: %s) type %s created at %s with range %s to %s", self._id, self._type, self._x, self._interval[0], self._interval[1])

        
        @property
        def id(self) -> str:
            return self._id

        @property
        def interval(self) -> List[float]:
            return self._interval
        
        @interval.setter
        def interval(self, value) -> None:
            if value is not None and value[0] is not None and value[1] is not None:
                if value[0] < value[1]:
                    self._interval = value
                else:
                    raise ValueError("Interval must start with lower boundary.")
            else:
                raise ValueError("Interval must be list of type float")
            
        @property
        def type(self) -> Constants.ZONE_TYPE:
            return self._type
        
        @type.setter
        def type(self, value: Constants.ZONE_TYPE) -> None:
            self._type = value

        @property
        def x(self) -> datetime:
            return self._x
        
        @x.setter
        def x(self, value) -> None:
            self._x = value

        @property
        def retests(self) -> int:
            return self._retests

        def retested(self) -> None:
            self._retests += 1


    def __init__(self, sr_data, mode: str) -> None:
        self._segments = {
            Constants.SR_DATA_LEVEL.LOW.value: [PrimarySegment(str(uuid4()), "T1")],
            Constants.SR_DATA_LEVEL.HIGH.value: [PrimarySegment(str(uuid4()), "T2")]
        }
        self._raw_sr_zones: List[SR_Structure.RSR_Zone] = []
        self._aggr_sr_zones: List[SR_Structure.ASR_Zone] = []
        self._mode = mode
        self._sr_data = sr_data


    @property
    def sr_data(self):
        return self._sr_data
    
    @sr_data.setter
    def sr_data(self, value):
        self._sr_data = value

    def reset_segments(self):
        self._segments = {
            Constants.SR_DATA_LEVEL.LOW.value: [PrimarySegment(str(uuid4()), "T1")],
            Constants.SR_DATA_LEVEL.HIGH.value: [PrimarySegment(str(uuid4()), "T2")]
        }

    # adds candle to the structure and calculates side effects
    def process_candle(self, level, candle):
        # start a new segment if segment closed by confirmed ChOC
        if self._segments[level][-1].choc_confirmed:
            logger.debug("Appending new primary segment to SR structure")
            self._segments[level].append(
                PrimarySegment(str(uuid4()),
                self._segments[level][-1].time_frame,
                self._segments[level][-1].opp_dir,
                self._segments[level][-1].key_low,
                self._segments[level][-1].key_high,
                self._segments[level][-1].last_low,
                self._segments[level][-1].last_high))
        # get last segment
        activ_ps: PrimarySegment = self._segments[level][-1]
        # add current candle to segment
        activ_ps.add_candle(candle)


    """
    Gather zones from candle structure segments
    """
    def compile_zones(self):

        self._raw_sr_zones.clear()

        levels = [Constants.SR_DATA_LEVEL.LOW.value, Constants.SR_DATA_LEVEL.HIGH.value]

        for level in levels:
            # check segments for SR levels
            # slice the array to exclude the first segment since it might not have a well formed character
            for segment in self._segments[level][1:]:

                zone = None

                if segment.dir == Constants.DIRECTION.UP:
                    # get a resistance zone
                    candle_data = self._sr_data[level].loc[segment.highest_candle]

                    if candle_data['open'] > candle_data['close']:
                        # bearish candle
                        body = (candle_data["close"], candle_data["open"])
                        wick = (candle_data["open"], candle_data["high"])
                    else:
                        # bullish candle
                        body = (candle_data["open"], candle_data["close"])
                        wick = (candle_data["close"], candle_data["high"])

                    zone = SR_Structure.RSR_Zone(Constants.ZONE_TYPE.RESISTANCE, segment.highest_candle, (candle_data['low'], candle_data['high']), body, wick)

                elif segment.dir == Constants.DIRECTION.DOWN:
                    # get a resistance zone
                    candle_data = self._sr_data[level].loc[segment.lowest_candle]

                    if candle_data['open'] > candle_data['close']:
                        # bearish candle
                        body = (candle_data["close"], candle_data["open"])
                        wick = (candle_data["low"], candle_data["close"])
                    else:
                        # bullish candle
                        body = (candle_data["open"], candle_data["close"])
                        wick = (candle_data["low"], candle_data["open"])

                    zone = SR_Structure.RSR_Zone(Constants.ZONE_TYPE.SUPPORT, segment.lowest_candle, (candle_data['low'], candle_data['high']), body, wick)

                if zone is not None:
                    self._raw_sr_zones.append(zone)

    
    """
    Method will try to merge overlapping zones. Returns false if no overlap
    """
    def merge_zones(self, aggr: ASR_Zone, raw: RSR_Zone) -> bool:

        mode = Constants.ZONING_MODE.CANDLE if self._mode is None else self._mode

        # set interval depending on mode
        int_low: float = None
        int_high: float = None

        if mode == Constants.ZONING_MODE.WICK:
            int_low = raw.wick[0]
            int_high = raw.wick[1]
        elif mode == Constants.ZONING_MODE.BODY:
            int_low = raw.body[0]
            int_high = raw.body[1]
        else:
            # defaults to "CANDLE"
            int_low = raw.full_candle[0]
            int_high = raw.full_candle[1]

        if int_high < aggr.interval[1] and int_high > aggr.interval[0]:
            # overlap exists
            # compute new interval
            int_high = aggr.interval[1]
            int_low = int_low if int_low < aggr.interval[0] else aggr.interval[0]

            # compare datetimes
            newtime = None
            newtype = None

            #datetime_fmt = "%Y-%m-%d %H:%M:%S"
            #r_datetime = datetime.strptime( raw.x, datetime_fmt)
            #a_datetime = datetime.strptime(aggr.x, datetime_fmt)

            #if r_datetime < a_datetime:
            if raw.x < aggr.x:
                newtime = raw.x
                newtype = raw.type
            else:
                newtime = aggr.x
                newtype = aggr.type

            # update zone
            aggr.x = newtime
            aggr.type = newtype
            aggr.interval = [int_low, int_high]
            aggr.retested()

            return True

        elif int_high > aggr.interval[1] and int_low < aggr.interval[1]:
            # overlap exists
            # compute new interval
            int_low = int_low if int_low < aggr.interval[0] else aggr.interval[0]

            # compare datetimes
            newtime = None
            newtype = None

            #datetime_fmt = "%Y-%m-%d %H:%M:%S"
            #r_datetime = datetime.strptime( raw.x, datetime_fmt)
            #a_datetime = datetime.strptime(aggr.x, datetime_fmt)

            #if r_datetime < a_datetime:
            if raw.x < aggr.x:
                newtime = raw.x
                newtype = raw.type
            else:
                newtime = aggr.x
                newtype = aggr.type

            # update zone
            aggr.x = newtime
            aggr.type = newtype
            aggr.interval = [int_low, int_high]
            aggr.retested()

            return True

        else:
            # no overlap
            return False


    """
    Try to find an aggregate zone which overlaps with current raw zone
    """
    def add_to_aggregate_zone(self, r_zone: RSR_Zone) -> bool:

        # attempt to add to existing aggregate zone
        for a_zone in self._aggr_sr_zones:
            if self.merge_zones(a_zone, r_zone):
                # if added to one return true
                return True

        return False


    """
    Generate aggregrated zones from raw zones
    """
    def process_zones(self):
            
        if len(self._raw_sr_zones) < 1:
            logger.warn("No zones available to process!")
            return
        
        self._aggr_sr_zones.clear()
        
        mode = Constants.ZONING_MODE.CANDLE if self._mode is None else self._mode

        for r_zone in self._raw_sr_zones:
            # check each raw zone to see if it is overlapping with another zone
            # creat a new aggregate zone for any zone that is not overlapping with a previously created aggregrate zone
            # if there is overlap, add that zone to the aggregate zone

            if not self.add_to_aggregate_zone(r_zone):
                # if raw zone could not be added to aggregate zone create new aggregate zone
                # set interval depending on mode
                int_low: float = None
                int_high: float = None

                if mode == Constants.ZONING_MODE.WICK:
                    int_low = r_zone.wick[0]
                    int_high = r_zone.wick[1]
                elif mode == Constants.ZONING_MODE.BODY:
                    int_low = r_zone.body[0]
                    int_high = r_zone.body[1]
                else:
                    # defaults to "CANDLE"
                    int_low = r_zone.full_candle[0]
                    int_high = r_zone.full_candle[1]

                self._aggr_sr_zones.append(SR_Structure.ASR_Zone(r_zone.type, r_zone.x, [int_low, int_high]))

    """
    Return zones in dictionary format
    """
    def get_zones(self) -> dict:
        zones = []

        for zone in self._aggr_sr_zones:
            zones.append({
                "id": zone.id,
                "type": zone.type.value,
                "x": zone.x,
                "interval": zone.interval,
                "retests": zone.retests
            })

        return zones



"""
The Kraken
"""
class Kraken:
    def __init__(self, pst_timeframes = None) -> None:

        if pst_timeframes is None:
            pst_timeframes = ["LOW T-FRAME", "MID T-FRAME", "HIGH T-FRAME"]
        
        # structure segments made up of candles
        self._segments = {
            Constants.PST_DATA_LEVEL.LOW.value : [PrimarySegment(str(uuid4()), pst_timeframes[0])],   # list of all segments of low time frame
            Constants.PST_DATA_LEVEL.MID.value : [PrimarySegment(str(uuid4()), pst_timeframes[1])],   # list of all segments of middle time frame
            Constants.PST_DATA_LEVEL.HIGH.value : [PrimarySegment(str(uuid4()), pst_timeframes[2])]  # list of all segments of high time frame
        }

        # dataframes containing primary candle data 
        self._pst_data = {
            Constants.PST_DATA_LEVEL.LOW.value : None,
            Constants.PST_DATA_LEVEL.MID.value : None,
            Constants.PST_DATA_LEVEL.HIGH.value : None
        }

        self._sr_structure = None

    @property
    def pst_data(self):
        return self._pst_data
    
    @property
    def sr_data(self):
        return self._sr_data

    """
    adds new candle to segment
    """
    def add_candle(self, level: str, time: datetime, open: float, high: float, low: float, close: float):

        # add candle to dataframe

        self._pst_data[level].loc[time] = {
            "open": open,
            "high": high,
            "low": low,
            "close": close
        }

        # process candle
        self.process_candle(level, Candle(time, open, high, low, close))

    """
    Add candle to segment and process side effects. The level parameter selects the appropriate structure
    level to add candle to
    """
    def process_candle(self, level: str, candle: Candle):
        logger.debug("Processing candle: %s", candle.timestamp)

        # start a new segment if segment closed by confirmed ChOC
        if self._segments[level][-1].choc_confirmed:
            logger.debug("Appending new primary segment: Level %s", level)
            self._segments[level].append(
                PrimarySegment(str(uuid4()),
                self._segments[level][-1].time_frame,
                self._segments[level][-1].opp_dir,
                self._segments[level][-1].key_low,
                self._segments[level][-1].key_high,
                self._segments[level][-1].last_low,
                self._segments[level][-1].last_high,
                self._segments[level][-1].key_low_candle,
                self._segments[level][-1].key_high_candle,
                self._segments[level][-1].last_low_candle,
                self._segments[level][-1].last_high_candle))
        
        # get last segment
        activ_ps: PrimarySegment = self._segments[level][-1]
        # add current candle to segment
        activ_ps.add_candle(candle)


    """
    Function gathers price structure representation data relevant for entering and exiting trades
    """
    def get_signal_data(self) -> dict:

        logger.info("Compiling signal data...")

        levels = [
            Constants.PST_DATA_LEVEL.LOW.value,
            Constants.PST_DATA_LEVEL.MID.value,
            Constants.PST_DATA_LEVEL.HIGH.value
        ]

        data = {}

        for level in levels:
            # get the current primary segment for the level
            ps = self._segments[level][-1]
            if len(self._segments[level]) < 2:
                prev_ps = self._segments[level][-1]
            else:
                prev_ps = self._segments[level][-2]

            _data = {
                "seg_id": ps.seg_id,
                "seg_dir": ps.dir,
                "candle": ps.candles[-1],
                "candle_dir": self.get_candle_dir(level, ps.candles[-1]),
                "bos_num": ps.bos_num,
                "in_bos": ps.in_bos,
                "in_pull_back": ps.in_pull_back,
                "highs": ps.key_high_candles,
                "lows": ps.key_low_candles,
                "choc": ps.choc,
                "choc_confirmed": ps.choc_confirmed,
                "key_levels": {
                    "high": ps.key_high,
                    "low": ps.key_low
                },
                "segment_range": {
                    "highest": ps.segment_high,
                    "lowest": ps.segment_low
                },
                "prev_segment": {
                    "seg_id": prev_ps.seg_id,
                    "seg_dir": prev_ps.dir,
                    "segment_range": {
                        "highest": prev_ps.segment_high,
                        "lowest": prev_ps.segment_low
                    }
                }
            }

            data["pst_" + level] = _data


        # get sr zones if available
        sr_zones = self._sr_structure.get_zones() if self._sr_structure is not None else None

        data["sr_zones"] = sr_zones

        return data

    """
    This function generates information required to mark out points of interest on graphs
    """
    def get_annotation(self, ratios, candle_length: int = 100) -> dict:
        logger.info("Compiling annotation data...")

        levels = [
            Constants.PST_DATA_LEVEL.LOW.value,
            Constants.PST_DATA_LEVEL.MID.value,
            Constants.PST_DATA_LEVEL.HIGH.value
        ]

        data = {}

        for level in levels:

            # set number of p-segments to retrieve
            pss = 0
            candles = int(candle_length/ratios[level])

            while True:
                pss += 1
                candles = candles - len(self._segments[level][-pss].candles)
                if candles <= 0 or pss >= len(self._segments[level]):
                    break

            _data = {
                "bos": [],
                "key_high": None,
                "key_low": None,
                "choc": [],
                "choc_confirm": [],
                "min": None,
                "max": None
            }

            # loop throgh p-segments from the last in reverse
            for ps in self._segments[level][-1:-pss-1:-1]:
                _data["bos"].extend(ps.bos_candles)
                _data["choc"].extend(ps.choc_candles)
                _data["choc_confirm"].append(ps.choc_confirm_candle)

                if _data["min"] is None:
                    _data["min"] = ps.segment_low
                elif _data["min"] > ps.segment_low:
                    _data["min"] = ps.segment_low

                if _data["max"] is None:
                    _data["max"] = ps.segment_high
                elif _data["max"] < ps.segment_high:
                    _data["max"] = ps.segment_high


            # get some info from current p-segment
            activ_ps = self._segments[level][-1]
            _data["key_high"] = activ_ps.key_high
            _data["key_low"] = activ_ps.key_low
            _data["timeframe"] = activ_ps.time_frame
            _data["dir"] = activ_ps.dir.value
            _data["in_choc"] = activ_ps.choc

            data["pst_" + level] = _data

        # get sr zones if available
        sr_zones = self._sr_structure.get_zones() if self._sr_structure is not None else None

        data["sr_zones"] = sr_zones

        return data

    """
    Initialize the Kraken with a lookback window for pst and sr data
    """   
    def initialize(self,
                   pst_data,
                   sr_data,
                   sr_timeframes = None,
                   mode: Constants.ZONING_MODE = None):

        logger.info("Initializing the Kraken...")

        logger.info("Processing primary structure data and constructing internal representation.")
        
        # copy pst dataframes
        levels = [
            Constants.PST_DATA_LEVEL.LOW.value,
            Constants.PST_DATA_LEVEL.MID.value,
            Constants.PST_DATA_LEVEL.HIGH.value
        ]

        for level in levels:
            self._pst_data[level]: pd.DataFrame = pst_data[level].copy()        # Pandas DataFrame with candlestick data

        # iterate through candlestick data per level
        for level in levels:
            for index, row in self._pst_data[level].iterrows():

                # create candle object
                candle = Candle(index, row['open'], row['high'], row['low'], row['close'])

                # add candle
                self.process_candle(level, candle)

        if sr_data is not None:
            self.initialize_new_zones(sr_data, mode)

    def initialize_new_zones(self, sr_data: pd.DataFrame, mode: Constants.ZONING_MODE = None):
        logger.info("Processing support and resistance levels from higher timeframe data.")

        levels = [Constants.SR_DATA_LEVEL.LOW.value, Constants.SR_DATA_LEVEL.HIGH.value]

        neo_sr_data = {}
        for level in levels:
            neo_sr_data[level] = sr_data[level].copy()
        
        if self._sr_structure is not None:
            self._sr_structure.sr_data = neo_sr_data
            self._sr_structure.reset_segments()
        else:
            self._sr_structure = SR_Structure(neo_sr_data, mode)

        for level in levels:
            for index, row in self._sr_structure.sr_data[level].iterrows():
                # create candle object
                candle = Candle(index, row['open'], row['high'], row['low'], row['close'])

                # add candle to SR Structure
                self._sr_structure.process_candle(level, candle)

        # compile zones from the processed candles
        self._sr_structure.compile_zones()

        # merge zones for consumption
        self._sr_structure.process_zones()

    
    def get_candle_dir(self, level, candle_timestamp: datetime) -> str:

        candle_row = self._pst_data[level].loc[candle_timestamp]

        return Constants.DIRECTION.UP if candle_row["close"] > candle_row["open"] else Constants.DIRECTION.DOWN