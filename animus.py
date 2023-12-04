"""
Developed by Dr Tendai Pfidze
Start date 21 November 2023

Animus is my back testing engine for trading strategies on historical price data
This engine will simulate buy and sell positions and update profit and loss per candle
It will provide methods for opening and closing virtual positions
It will keep history of the trades and their outcomes

"""
from typing import List
from kraken import Kraken, Constants
from datetime import datetime
import pandas as pd
from trade_objects import Account, Position, ShortPosition, LongPosition, POSITION_TYPE, POSITION_STATE, engine
from config import strategy, options, extras
from sqlalchemy.orm import Session
from sqlalchemy import select
import time
import logging

# set up logging
logger = logging.getLogger(__name__)
# set general log level
logger.setLevel("INFO")
# shared log formatter
formatter = logging.Formatter("%(asctime)s : %(name)s [%(funcName)s] : %(levelname)s -> %(message)s")

# create log handlers
# general, contains all logs
general_file_handler = logging.FileHandler("log/animus.log")
general_file_handler.setFormatter(formatter)
# warning, contains warn and higher level logs
warn_file_handler = logging.FileHandler("log/animus.warn.log")
warn_file_handler.setFormatter(formatter)
warn_file_handler.setLevel("WARN")

# add handlers to logger
logger.addHandler(general_file_handler)
logger.addHandler(warn_file_handler)

class DATA_TYPE:
    PST_DATA = 1
    SR_DATA = 2


"""
This class implements strategies based on structural data from the Kraken.
"""
class Advisor():
    def __init__(self, strategy: str, options) -> None:
        self._strategy: str = strategy
        self._options = options

    def generate_positions(self, closing_price, balance, signals, options):

        match self._strategy:
            case "SIMPLE_TREND":
                # trading simple trends
                # if secondary structure trend is UP we are looking to buy when primary structure turns to the up side 
                if signals["secondary_struct"]["dir"] == Constants.DIRECTION.UP:

                    if self._options["entry"] == "CHOC_CONFIRMED":
                        if signals["primary_struct"]["choc_confirmed"] and signals["primary_struct"]["seg_dir"] == Constants.DIRECTION.DOWN: # down changing to UP
                            # enter position
                            # sl
                            sl = signals["primary_struct"]["key_levels"]["low"] if self._options["sl_level"] == "KEY_LEVEL" else signals["primary_struct"]["segment_range"]["lowest"]
                            sl = sl - (closing_price - sl) * self._options["sl_level_margin"]
                            tp = closing_price + (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.BUY, closing_price, sl, tp, balance, signals, options)
                    elif self._options["entry"] == "CHOC":
                        if signals["primary_struct"]["choc"] and signals["primary_struct"]["dir"] == Constants.DIRECTION.DOWN: # down changing to UP
                            # enter position
                            # sl
                            sl = signals["primary_struct"]["key_levels"]["low"]
                            sl = sl - (closing_price - sl) * self._options["sl_level_margin"]
                            tp = closing_price + (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.BUY, closing_price, sl, tp, balance, signals, options)
                    else:
                        return None
                    
                elif signals["secondary_struct"]["dir"] == Constants.DIRECTION.DOWN:
                    
                    if self._options["entry"] == "CHOC_CONFIRMED":
                        if signals["primary_struct"]["choc_confirmed"] and signals["primary_struct"]["seg_dir"] == Constants.DIRECTION.UP: # down changing to DOWN
                            # enter position
                            # sl
                            sl = signals["primary_struct"]["key_levels"]["high"] if self._options["sl_level"] == "KEY_LEVEL" else signals["primary_struct"]["segment_range"]["highest"]
                            sl = sl + (sl - closing_price) * self._options["sl_level_margin"]
                            tp = closing_price - (sl - closing_price) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.SELL, closing_price, sl, tp, balance, signals, options)
                    elif self._options["entry"] == "CHOC":
                        if signals["primary_struct"]["choc"] and signals["primary_struct"]["dir"] == Constants.DIRECTION.UP: # down changing to DOWN
                            # enter position
                            # sl
                            sl = signals["primary_struct"]["key_levels"]["high"]
                            sl = sl + (sl - closing_price) * self._options["sl_level_margin"]
                            tp = closing_price - (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.SELL, closing_price, sl, tp, balance, signals, options)
                    else:
                        return None
                    

            case "PRICE_ACTION":
                pass
            case _:
                logger.warn("Incorrect parameter for strategy selection. No positions computed.")
                return None

    
    def modify_positions(self, closing_price, balance, signals, options):
        match self._strategy:
            case "SIMPLE_TREND":
                logger.debug("matched SIMPLE_TREND...")
                # trading simple trends
                # if secondary structure trend is UP we are looking to buy when primary structure turns to the up side 
                if signals["secondary_struct"]["dir"] == Constants.DIRECTION.UP:

                    if self._options["exit"] == "CHOC_CONFIRMED":
                        if signals["primary_struct"]["choc_confirmed"] and signals["primary_struct"]["seg_dir"] == Constants.DIRECTION.UP: # UP changing to DOWN
                            # close_positions
                            return {
                                "actions": [
                                    {
                                        "action": "CLOSE",
                                        "position_type": POSITION_TYPE.BUY.value,
                                        "instr": self._options["instr"]
                                    }
                                ]
                            }
                        
                        else:
                            return {"actions": []}
                    elif self._options["exit"] == "CHOC":
                        if signals["primary_struct"]["choc"] and signals["primary_struct"]["seg_dir"] == Constants.DIRECTION.UP: # UP changing to DOWN
                            # close_positions
                            return {
                                "actions": [
                                    {
                                        "action": "CLOSE",
                                        "position_type": POSITION_TYPE.BUY.value,
                                        "instr": self._options["instr"]
                                    }
                                ]
                            }
                        
                        else:
                            return {"actions": []}
                    else:
                        return {"actions": []}
                    
                elif signals["secondary_struct"]["dir"] == Constants.DIRECTION.DOWN:
                    
                    if self._options["exit"] == "CHOC_CONFIRMED":
                        if signals["primary_struct"]["choc_confirmed"] and signals["primary_struct"]["seg_dir"] == Constants.DIRECTION.DOWN: # down changing to DOWN
                            # close_positions
                            return {
                                "actions": [
                                    {
                                        "action": "CLOSE",
                                        "position_type": POSITION_TYPE.SELL.value,
                                        "instr": self._options["instr"]
                                    }
                                ]
                            }

                        else:
                            return {"actions": []}   
                    elif self._options["exit"] == "CHOC":
                        if signals["primary_struct"]["choc"] and signals["primary_struct"]["seg_dir"] == Constants.DIRECTION.DOWN: # down changing to DOWN
                            # close_positions
                            return {
                                "actions": [
                                    {
                                        "action": "CLOSE",
                                        "position_type": POSITION_TYPE.SELL.value,
                                        "instr": self._options["instr"]
                                    }
                                ]
                            }
                        
                        else:
                            return {"actions": []}
                    
                    else:
                        return {"actions": []}

            case _:
                logger.debug("No strategy match")
                return {"actions": []}            

    def build_position(self, type: POSITION_TYPE, closing_price: float, sl: float, tp: float, balance: float, signals, options):
        
        volume = (balance * options["risk_per_trade"]) / (abs(closing_price - sl) * options["trade_contract_size"])

        take_profit = tp

        if options["reward_ratio"] is not None:
            rr = options["reward_ratio"]
            risk = abs(closing_price - sl)
            take_profit = closing_price - (rr * risk) if type == POSITION_TYPE.SELL else closing_price + (rr * risk)

        return {
            "type": type.value,
            "instr": options["instr"],
            "vol": volume,
            "price": closing_price,
            "sl": sl,
            "tp": take_profit
        }

"""
The Animus
"""
class Animus():
    def __init__(self) -> None:
        self._simulation: bool = True
        self._pst_data: pd.DataFrame = None
        self._sr_data: pd.DataFrame = None      # stores simulation sr data
        self._pst_iloc: int = None              # marks the current location during simulation
        self._sr_iloc: int = None               # marks the current location during simulation
        self._pst_last_iloc: int = None         # marks end of simulation end of 
        self._pst_sr_iloc_ratio: int = None
        self._kraken: Kraken = None
        self._advisor: Advisor = None
        self._annotation_data = None
        self._positions_data = None
        self._annotation_candle_length = 100
        self._account_id = None
        self._sim_speed = 0.0

    # returns data used to mark points of interest on graphs
    # includes price action, support and resistance, positions
    @property
    def annotation_data(self):
        return self._annotation_data
    
    # the size of window, in terms of candles for which annotation should be provided
    @property
    def annotation_candle_length(self):
        return self._annotation_candle_length
    
    @annotation_candle_length.setter
    def annotation_candle_length(self, value):
        self._annotation_candle_length = value

    # set candle walk through speed for simulation
    @property
    def sim_speed(self) -> float:
        return self._sim_speed
    
    @sim_speed.setter
    def sim_speed(self, value):
        self._sim_speed = value
    """
    Method to kick off a simulation of the market.
    start: the starting date and time of the simulation
    end: end of simulation
    strategy: e.g "SIMPLE_TREND", "PRICE_ACTION"
    options:
    {
        "entry": e.g "CHOC", "CHOC_CONFIRMED,
        "sl_level": e.g "KEY_LEVEL", "LAST_SEGMENT_RANGE",
        "sl_level_margin": e.g 0.1, 0.2,
        "reward_ratio": e.g 1.5, 2, 3, None,
        "pst_lookback_window": e.g 200, 250, 300,
        "sr_lookback_window": e.g 200, 250, 300,
        "init_account_balance": e.g 100,
        "risk_per_trade": e.g 0.1, 0.4,
        "compound_risk": e.g True, False,
        "max_concurrent_trades": e.g 5, 10 
    }
    """
    def run_backtest(self, start: str, end: str, strategy: str, options,
                      pst_file: str, sr_file: str = None, pst_sr_ratio: int = None):
        
        logger.info("Running backtest: %s on %s from %s to %s...", strategy, options["instr"], start, end)
        print("Running backtest: {} on {} from {} to {}...xxxxxxx".format(strategy, options["instr"], start, end))
        
        # load data from files
        # load pst file
        self._pst_data = pd.read_csv(pst_file, index_col="time")
        # check for and load sr file
        if sr_file is not None:
            self._sr_data = pd.read_csv(sr_file, index_col="time")
            if pst_sr_ratio is None:
                raise ValueError ("pst_sr_ratio cannot be null when sr data provided")
            else:
                self._pst_sr_iloc_ratio = pst_sr_ratio

        # get initial iloc positions
        # pst iloc
        self._pst_iloc = self._pst_data.index.get_loc(start)
        
        try:
            self._pst_last_iloc = self._pst_data.index.get_loc(end)
        except KeyError as err:
            # if index not found use last index in dataframe
            self._pst_last_iloc = len(self._pst_data) - 1
        
        if self._sr_data is not None:
            self._sr_iloc = self._sr_data.index.get_loc(start)

        ### Initialize the kraken
        self._kraken = Kraken()

        #gather warm up data
        pst_data = self.load_warm_up_data(DATA_TYPE.PST_DATA, options["pst_lookback_window"])
        if self._sr_data is not None:
            sr_data = self.load_warm_up_data(DATA_TYPE.SR_DATA, options["sr_lookback_window"])
        else:
            sr_data = None

        # call initialize
        self._kraken.initialize(pst_data, sr_data)
        # create advisor
        self._advisor = Advisor(strategy, options)

        ### Begin simulation

        # open database connection
        with Session(engine) as session:

            # create simulated account
            description = "{} {} {}".format(strategy, options, extras)
            account = Account(description, balance=options["init_account_balance"])
            session.add(account)            # save to database
            self._account_id = account.id
            session.commit()
            
            for index, row in self._pst_data.iloc[self._pst_iloc:self._pst_last_iloc+1].iterrows():
                self._pst_iloc = self._pst_data.index.get_loc(index)

                # step through the candles
                # add candle to the Kraken
                self._kraken.add_candle(
                    index, row["open"], row["high"], row["low"], row["close"]
                )
                # get signals and annotations
                signals = self._kraken.get_signal_data()
                self._annotation_data = self._kraken.get_annotation(self._annotation_candle_length)
                position_data = []
                for pos in account.positions:
                    position_data.append(
                        {
                            "type": pos.type,
                            "entry_time": pos.entry_time,
                            "exit_time": pos.exit_time,
                            "entry": pos.price,
                            "sl": pos.sl,
                            "tp": pos.tp,
                            "close": pos.close
                        }
                    )

                self._positions_data = position_data

                # get signal actions
                trade = self._advisor.generate_positions(row["close"], account.balance, signals, options)
                mods = self._advisor.modify_positions(row["close"], account.balance, signals, options)

                # update positions
                for position in account.positions:
                    position.check_position_and_update(index, row["low"], row["high"])

                # update equity
                account.update_equity(row["low"], row["high"])

                # implement actions
                # place trade
                open_positions = account.count_open_positions()

                if trade is not None and open_positions < options["max_concurrent_trades"]:
                    if trade["type"] == POSITION_TYPE.SELL.value:
                        account.positions.append(
                            ShortPosition(
                                account.id,
                                trade["instr"],
                                index,
                                options["trade_contract_size"],
                                trade["vol"],
                                trade["price"],
                                trade["sl"],
                                trade["tp"]
                            )
                        )
                    else:
                        account.positions.append(
                            LongPosition(
                                account.id,
                                trade["instr"],
                                index,
                                options["trade_contract_size"],
                                trade["vol"],
                                trade["price"],
                                trade["sl"],
                                trade["tp"]
                            )
                        )
                        
                    session.commit()

                if open_positions >= options["max_concurrent_trades"]:
                    print("MAX POSITIONS OPEN")
                    logger.warn("MAX POSITIONS OPEN")        
                    
                
                for action in mods["actions"]:
                    match action["action"]:
                        case "CLOSE":
                            ptype = action["position_type"]
                            instr = action["instr"]

                            for p in account.positions:
                                if p.type == ptype and p.instr == instr and p.state == POSITION_STATE.OPEN.value:
                                    p.close_position(index, row["close"])
                                    session.commit()

                # slow down simulation speed to see trades in real time
                time.sleep(self._sim_speed)

            session.commit()
            logger.info("Completed simultion/backtest successfully...")
            print("Simulation complete: \n{}".format(account))

    """
    This function returns all the data at the end of the simulation
    """
    def get_all_simulation_data(self):
        # get the candle sticks
        bars = self._kraken.pst_data.to_csv(orient="records")
        # get annotation for candlesticks
        annotation = self._kraken.get_annotation(len(bars))
        # get positions/trades
        trades = []

        # retrieve positions from database
        with Session(engine) as session:
            positions = session.execute(select(Position).where(Position._account_id == self._account_id)).scalars().all()
            for pos in positions:
                trades.append(
                    {
                        "type": pos.type,
                        "entry_time": pos.entry_time,
                        "exit_time": pos.exit_time,
                        "entry": pos.price,
                        "sl": pos.sl,
                        "tp": pos.tp,
                        "close": pos.close
                    }
                )

        return {
            "bars": bars,
            "annotation": annotation,
            "trades": trades
        }

    """
    This function returns data during simulation to show how trades are being made
    """
    def get_running_simulation_data(self):
        # get the candle sticks       
        bars = self._kraken.pst_data.iloc[self._pst_iloc-self._annotation_candle_length:self._pst_iloc+1].to_dict(orient="records")
        annotation = self.annotation_data
        trades = self._positions_data

        return {
            "bars": bars,
            "annotation": annotation,
            "trades": trades
        }

    """
    Returns look back data. A dataframe containing the specified number of candles
    From current candle going back
    """
    def load_warm_up_data(self, data_type: DATA_TYPE, num_candles: int) -> pd.DataFrame:
        if self._simulation:
            # during simulation, data is obtained locally
            if data_type == DATA_TYPE.PST_DATA:
                start_iloc = (self._pst_iloc - num_candles) if num_candles <= self._pst_iloc else 0
                return self._pst_data[start_iloc:self._pst_iloc]
            elif data_type == DATA_TYPE.SR_DATA:
                start_iloc = (self._sr_iloc - num_candles) if num_candles <= self._sr_iloc else 0
                return self._sr_data[(self._sr_iloc - num_candles):self._sr_iloc]
            else:
                logger.error("Invalid data type argument for loading warm up data")
                raise RuntimeError("Incorrect data type argument.")
            
