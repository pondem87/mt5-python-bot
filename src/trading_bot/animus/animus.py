"""
Developed by Dr Tendai Pfidze
Start date 21 November 2023

Animus is my back testing engine for trading strategies on historical price data
This engine will simulate buy and sell positions and update profit and loss per candle
It will provide methods for opening and closing virtual positions
It will keep history of the trades and their outcomes

"""
from typing import List
from kraken.kraken import Kraken
from kraken.ict_components.types import PST_DATA_LEVEL, SR_DATA_LEVEL
from .types import DATA_TYPE
from advisor import Advisor
import pandas as pd
from trade_objects import Account, Position, ShortPosition, LongPosition, POSITION_TYPE, POSITION_STATE, engine
from sqlalchemy.orm import Session
from sqlalchemy import select
from util.utility import round_to_ref
import time
from datetime import datetime
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


"""
The Animus
"""
class Animus():
    def __init__(self) -> None:
        self._simulation: bool = True
        self._pst_data = {}
        self._sr_data = None                    # stores simulation sr data
        self._pst_iloc: int = None              # marks the current location during simulation
        self._pst_last_iloc: int = None         # marks end of simulation end of 
        self._pst_sr_iloc_ratio: int = 0
        self._pst_level_ratios = {}
        self._sr_level_ratios = {}
        self._kraken: Kraken = None
        self._advisor: Advisor = None
        self._annotation_data = None
        self._positions_data = None
        self._annotation_candle_length = 100
        self._account_id = None
        self._sim_speed = 0.0
        self._publish_live_data = False
        self._publish_cycle = 1
        self._sim_options = None

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


    @property
    def publish_live_data(self):
        return self._publish_live_data
    
    @publish_live_data.setter
    def publish_live_data(self, value):
        self._publish_live_data = value

    @property
    def publish_cycle(self):
        return self._publish_cycle
    
    @publish_cycle.setter
    def publish_cycle(self, value):
        self._publish_cycle = value

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
    def run_backtest(self, start: str, end: str, strategy: str, options, extras, publish_data_func,
                      pst_files, sr_files = None, sr_pst_cycle = 100, sr_zoning_mode = None):
        
        logger.info("Running backtest: %s on %s from %s to %s...", strategy, options["instr"], start, end)
        print("Running backtest: {} on {} from {} to {}...".format(strategy, options["instr"], start, end))
        
        # load data from files
        # load pst files
        levels = [PST_DATA_LEVEL.LOW.value, PST_DATA_LEVEL.MID.value, PST_DATA_LEVEL.HIGH.value]
        for level in levels:
            self._pst_data[level] = pd.read_csv(pst_files[level], index_col="time")
        # check for and load sr file
        if sr_files is not None:
            self._sr_data = {}
            levels = [SR_DATA_LEVEL.LOW.value, SR_DATA_LEVEL.HIGH.value]
            for level in levels:
                self._sr_data[level] = pd.read_csv(sr_files[level], index_col="time")

            self._sr_level_ratios = self.get_sr_level_ratios()
            self._pst_sr_iloc_ratio = self.get_pst_sr_iloc_ratio()

        self._sim_options = options

        self._pst_level_ratios = self.get_pst_level_ratios()

        # get initial iloc positions
        # pst iloc
        self._pst_iloc = self._pst_data[PST_DATA_LEVEL.LOW.value].index.get_loc(start)
        
        try:
            self._pst_last_iloc = self._pst_data[PST_DATA_LEVEL.LOW.value].index.get_loc(end)
        except KeyError as err:
            # if index not found use last index in dataframe
            self._pst_last_iloc = len(self._pst_data) - 1
        
        if self._sr_data is not None:
            self._sr_iloc = self._sr_data[SR_DATA_LEVEL.LOW.value].index.get_loc(start)

        ### Initialize the kraken
        self._kraken = Kraken()

        #gather warm up data
        pst_data = self.load_warm_up_data(DATA_TYPE.PST_DATA, options["pst_lookback_window"])
        if self._sr_data is not None:
            sr_data = self.load_warm_up_data(DATA_TYPE.SR_DATA, options["sr_lookback_window"])
        else:
            sr_data = None

        # call initialize
        self._kraken.initialize(pst_data, sr_data, mode=sr_zoning_mode)
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
            
            for index, row in self._pst_data[PST_DATA_LEVEL.LOW.value].iloc[self._pst_iloc:self._pst_last_iloc+1].iterrows():
                self._pst_iloc = self._pst_data[PST_DATA_LEVEL.LOW.value].index.get_loc(index)
                #print("ROW INDEX IS {}, PST_ILOC IS {}".format(index, self._pst_iloc))

                # renew SR levels at intervals
                if self._pst_iloc % sr_pst_cycle == 0:
                    self._kraken.initialize_new_zones(self.load_warm_up_data(DATA_TYPE.SR_DATA, options["sr_lookback_window"]))

                # step through the candles
                # add candle to the Kraken
                levels = [PST_DATA_LEVEL.LOW.value, PST_DATA_LEVEL.MID.value, PST_DATA_LEVEL.HIGH.value]
                for level in levels:
                    # add low level candle
                    if level == PST_DATA_LEVEL.LOW.value:
                        self._kraken.add_candle(
                            level, index, row["open"], row["high"], row["low"], row["close"]
                        )
                    elif self._pst_iloc % self._pst_level_ratios[level] == 0:
                        # add higher timeframe candles at intervals
                        _row = self._pst_data[level].iloc[int(self._pst_iloc/self._pst_level_ratios[level])]
                        self._kraken.add_candle(
                            level, _row.name, _row["open"], _row["high"], _row["low"], _row["close"]
                        )


                # get signals and annotations
                signals = self._kraken.get_signal_data()
                if self.publish_live_data and self._pst_iloc % self._publish_cycle == 0:
                    self._annotation_data = self._kraken.get_annotation(self._pst_level_ratios, self._annotation_candle_length)
                    position_data = []
                    for pos in account.positions:
                        position_data.append(
                            {
                                "type": pos.type,
                                "entry_time": pos.entry_time,
                                "exit_time": pos.exit_time,
                                "price": pos.price,
                                "tsl": pos.sl,
                                "sl": pos.initial_sl,
                                "tp": pos.tp,
                                "close": pos.close,
                                "state": pos.state
                            }
                        )
                        #print(pos)

                    self._annotation_data["account"] = {
                        "initial_balance": account.initial_balance,
                        "equity": account.equity,
                        "balance": account.balance
                    }

                    self._positions_data = position_data

                # get signal actions
                _balance = account.initial_balance if options["compound_risk"] == False else account.balance
                trade = self._advisor.generate_positions(row["close"], _balance, signals)
                mods = self._advisor.modify_positions(row["close"], _balance, signals)

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
                                options["symbol"]["trade_contract_size"],
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
                                options["symbol"]["trade_contract_size"],
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
                        
                        case "MOVE_SL":
                            ptype = action["position_type"]
                            instr = action["instr"]

                            for p in account.positions:
                                if p.type == ptype and p.instr == instr and p.state == POSITION_STATE.OPEN.value:
                                    # check options
                                    if options["move_sl"]["allow"] == True:
                                        # moving SL allowed
                                        # check positions R
                                        r = (p.price - row["close"])/(p.initial_sl - p.price)
                                        if r >= options["move_sl"]["to_break_even_at_r"] and r <= options["move_sl"]["trailing_at_r"]:
                                            # move stop loss to break even
                                            p.move_sl(p.price, row["close"])
                                        elif r > options["move_sl"]["trailing_at_r"]:
                                            if action["new_sl_target"] > p.price and p.type == POSITION_TYPE.BUY.value:
                                                # add margin to sl
                                                sl = action["new_sl_target"] - (p.price - p.initial_sl) * options["sl_level_margin"]
                                                p.move_sl(sl, row["close"])
                                            elif action["new_sl_target"] < p.price and p.type == POSITION_TYPE.SELL.value:
                                                # add margin to sl
                                                sl = action["new_sl_target"] + (p.initial_sl - p.price) * options["sl_level_margin"]
                                                p.move_sl(sl, row["close"])
                                            else:
                                                p.move_sl(p.price, row["close"])


                # slow down simulation speed to see trades in real time
                session.commit()

                # publish data
                if self._publish_live_data and self._pst_iloc % self._publish_cycle == 0:
                    publish_data_func()
                    time.sleep(self._sim_speed)

                

            session.commit()
            logger.info("Completed simultion/backtest successfully...")
            print("Simulation complete: \n{}".format(account))

    """
    This function returns all the data at the end of the simulation
    """
    def get_all_simulation_data(self):
        # get the candle sticks
        bars = self._kraken.pst_data[PST_DATA_LEVEL.LOW.value].reset_index(inplace=False).to_csv(orient="records")
        # get annotation for candlesticks
        annotation = self._kraken.get_annotation(self.get_pst_level_ratios, len(bars))
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
                        "price": pos.price,
                        "tsl": pos.sl,
                        "sl": pos.initial_sl,
                        "tp": pos.tp,
                        "close": pos.close,
                        "state": pos.state
                    }
                )

        return {
            "bars": bars,
            "annotation": annotation,
            "trades": trades,
            "options": self._sim_options
        }

    """
    This function returns data during simulation to show how trades are being made
    """
    def get_running_simulation_data(self):
        # get the candle sticks       
        bars = self._kraken.pst_data[PST_DATA_LEVEL.LOW.value].iloc[-self._annotation_candle_length:].reset_index(inplace=False).to_dict(orient="records")
        annotation = self.annotation_data
        trades = self._positions_data

        return {
            "bars": bars,
            "annotation": annotation,
            "trades": trades,
            "options": self._sim_options
        }

    """
    Returns look back data. A dataframe containing the specified number of candles
    From current candle going back
    """
    def load_warm_up_data(self, data_type: DATA_TYPE, num_candles: int) -> pd.DataFrame:
        if self._simulation:
            # during simulation, data is obtained locally
            if data_type == DATA_TYPE.PST_DATA:
                pst_data = {}
                levels = [PST_DATA_LEVEL.LOW.value,
                          PST_DATA_LEVEL.MID.value,
                          PST_DATA_LEVEL.HIGH.value]
                
                # get data for each timeframe level
                for level in levels:
                    start_iloc = (self._pst_iloc - num_candles) if num_candles <= self._pst_iloc else 0
                    # get a slice of data for each level adjusting the slicer with timeframe ratios
                    pst_data[level] = self._pst_data[level][int(start_iloc/self._pst_level_ratios[level]):int(self._pst_iloc/self._pst_level_ratios[level])]
                
                return pst_data
            
            elif data_type == DATA_TYPE.SR_DATA:
                sr_data = {}
                levels = [SR_DATA_LEVEL.LOW.value,
                          SR_DATA_LEVEL.HIGH.value]
                
                for level in levels:
                    # get data for each timeframe level
                    start_iloc = int((self._pst_iloc/self._pst_sr_iloc_ratio) - (num_candles/self._pst_sr_iloc_ratio)) if num_candles <= self._sr_iloc else 0
                    sr_iloc = self._pst_iloc/self._pst_sr_iloc_ratio
                    # get a slice of data for each level adjusting the slicer with timeframe ratios
                    sr_data[level] = self._sr_data[level][int(start_iloc/self._sr_level_ratios[level]):int(sr_iloc/self._sr_level_ratios[level])]

                return sr_data
                
            else:
                logger.error("Invalid data type argument for loading warm up data")
                raise RuntimeError("Incorrect data type argument.")
    

    """
    """
    def get_pst_level_ratios(self):
        dtfmt = "%Y-%m-%d %H:%M:%S"

        level = [PST_DATA_LEVEL.LOW.value,
                 PST_DATA_LEVEL.MID.value,
                 PST_DATA_LEVEL.HIGH.value]

        interval1 = datetime.strptime(self._pst_data[level[0]].iloc[1].name, dtfmt) - datetime.strptime(self._pst_data[level[0]].iloc[0].name, dtfmt)
        interval2 = datetime.strptime(self._pst_data[level[1]].iloc[1].name, dtfmt) - datetime.strptime(self._pst_data[level[1]].iloc[0].name, dtfmt)
        interval3 = datetime.strptime(self._pst_data[level[2]].iloc[1].name, dtfmt) - datetime.strptime(self._pst_data[level[2]].iloc[0].name, dtfmt)

        return {
            level[0]: 1,
            level[1]: interval2/interval1,
            level[2]: interval3/interval1
        }
    
    def get_sr_level_ratios(self):
        dtfmt = "%Y-%m-%d %H:%M:%S"

        level = [SR_DATA_LEVEL.LOW.value,
                    SR_DATA_LEVEL.HIGH.value]
        
        interval1 = datetime.strptime(self._pst_data[level[0]].iloc[1].name, dtfmt) - datetime.strptime(self._pst_data[level[0]].iloc[0].name, dtfmt)
        interval2 = datetime.strptime(self._pst_data[level[1]].iloc[1].name, dtfmt) - datetime.strptime(self._pst_data[level[1]].iloc[0].name, dtfmt)

        return {
            level[0]: 1,
            level[1]: interval2/interval1
        }
    
    def get_pst_sr_iloc_ratio(self):
        dtfmt = "%Y-%m-%d %H:%M:%S"

        pst_interval = datetime.strptime(self._pst_data[PST_DATA_LEVEL.LOW.value].iloc[1].name, dtfmt) - datetime.strptime(self._pst_data[PST_DATA_LEVEL.LOW.value].iloc[0].name, dtfmt)
        sr_interval = datetime.strptime(self._sr_data[SR_DATA_LEVEL.LOW.value].iloc[1].name, dtfmt) - datetime.strptime(self._sr_data[SR_DATA_LEVEL.LOW.value].iloc[0].name, dtfmt)

        return sr_interval/pst_interval