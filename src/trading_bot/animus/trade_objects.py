"""
Developed by Dr Tendai Pfidze
Start date 21 November 2023

Animus is my back testing engine for trading strategies on historical price data
This engine will simulate buy and sell positions and update profit and loss per candle
It will provide methods for opening and closing virtual positions
It will keep history of the trades and their outcomes

This file defines classes used by Animus to set up positions and to track profit and loss
for a simulated account.

"""
from typing import List, Optional
from uuid import uuid4, UUID
from .types import POSITION_STATE, POSITION_TYPE
from sqlalchemy import ForeignKey, String, create_engine
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase, declared_attr
import logging

# set up logging
logger = logging.getLogger(__name__)
# set general log level
logger.setLevel("INFO")
# shared log formatter
formatter = logging.Formatter("%(asctime)s : %(name)s [%(funcName)s] : %(levelname)s -> %(message)s")

# create log handlers
# general, contains all logs
general_file_handler = logging.FileHandler("log/trade_objects.log")
general_file_handler.setFormatter(formatter)
# warning, contains warn and higher level logs
warn_file_handler = logging.FileHandler("log/trade_objects.warn.log")
warn_file_handler.setFormatter(formatter)
warn_file_handler.setLevel("WARN")

# add handlers to logger
logger.addHandler(general_file_handler)
logger.addHandler(warn_file_handler)

class Base(DeclarativeBase):
    pass


"""
Class for simulating a trading account
"""
class Account(Base):
    __tablename__ = "accounts"

    _id: Mapped[UUID] = mapped_column(primary_key=True)
    _description: Mapped[str]
    _initial_balance: Mapped[float]
    _balance: Mapped[float]
    _max_equity: Mapped[float]
    _min_equity: Mapped[float]
    positions: Mapped[List["Position"]] = relationship("Position", back_populates="account")

    def __init__(self, desc, balance) -> None:
        self._id = uuid4()
        self._description = desc     # contains information about the simulation
        self._initial_balance = balance
        self._balance = balance
        self._max_equity = balance
        self._min_equity = balance
        self._equity = balance

    def __repr__(self) -> str:
        return "Account: {},\nDescription: {}\n\nInitial bal: {}, Final balance: {}, Equity (min/max): {}/{}".format(
            self._id,
            self._description,
            self._initial_balance,
            self._balance,
            self._min_equity,
            self._max_equity
        )

    @property
    def id(self) -> str:
        return self._id
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def initial_balance(self) -> float:
        return self._initial_balance
    
    @property
    def balance(self) -> float:
        return self._balance
    
    @balance.setter
    def balance(self, value):
        self._balance = value

    @property
    def equity(self) -> float:
        return self._equity
    

    def update_equity(self, price_low: float, price_high: float):
        unrealised_profit: float = 0
        for position in self.positions:
            unrealised_profit += position.get_unrealised_profit(price_low, price_high)

        self._equity = self._balance + unrealised_profit

        # update minimum and maximum equity
        if self._equity > self._max_equity:
            self._max_equity = self._equity
        elif self._equity < self._min_equity:
            self._min_equity = self._equity

        return unrealised_profit
    

    def count_open_positions(self):
        count = 0
        
        for pos in self.positions:
            if pos.state == POSITION_STATE.OPEN.value:
                count += 1
        
        return count

"""
Class for handling trade positions. Inherited by specific classes for long and short positions
"""
class Position(Base):
    __tablename__ = "positions"

    __mapper_args__ = {
        "polymorphic_on": "_type"
    }

    _id: Mapped[UUID] = mapped_column(primary_key=True)
    _account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts._id"))
    _type: Mapped[str] = mapped_column(String(5))
    _instr: Mapped[str]
    _contract: Mapped[float]
    _vol: Mapped[float]
    _price: Mapped[float]
    _sl: Mapped[Optional[float]]
    _tp: Mapped[Optional[float]]
    _state: Mapped[str] = mapped_column(String(5))
    _initial_sl: Mapped[Optional[float]]
    _profit: Mapped[float]
    _reward_units: Mapped[Optional[float]]
    _entry_time: Mapped[str]
    _exit_time: Mapped[Optional[str]]
    _close: Mapped[Optional[float]]

    @declared_attr
    def account(self) -> Mapped[Account]:
        return relationship("Account", back_populates="positions")

    def __init__(self, account_id:UUID , type: str, instr: str, entry_time: str, contract: float, vol: float, price: float, sl: float = None, tp: float = None) -> None:
        self._id = uuid4()
        self._account_id = account_id
        self._type = type
        self._instr = instr
        self._contract = contract
        self._vol = vol
        self._price = price
        self._sl = sl
        self._tp = tp
        self._state = POSITION_STATE.OPEN.value
        self._initial_sl = sl
        self._profit = 0
        self._reward_units = None
        self._entry_time = entry_time
        self._exit_time = None
        self._close = None

        self._profit: int = 0

        logger.info("Simulation position created. Position(%s)-%s Price: %s, Volume: %s, SL: %s, TP: %s",
                    self._id, self._type, self._price, self._vol, self._sl, self._tp)

    def __repr__(self) -> str:
        return "Position: type {}, instr {}, entry time {}, price: {}, state {}, close price {}".format(self.type, self.instr, self.entry_time, self.price, self.state, self.close)
    

    def move_sl(self, value, close_price):
        self._sl = value

    @property
    def id(self) -> str:
        return self._id
    
    @property
    def account_id(self) -> str:
        return self._account_id
        
    @property
    def type(self) -> str:
        return self._type
        
    @property
    def instr(self) -> str:
        return self._instr

    @property
    def vol(self):
        return self._vol
        
    @property
    def price(self) -> str:
        return self._price
    
    @property
    def state(self) -> str:
        return self._state
        
    @property
    def profit(self):
        return self._profit
    
    @property
    def reward_units(self) -> float:
        return self._reward_units
    
    @reward_units.setter
    def reward_units(self, value):
        self._reward_units = value

    @property
    def entry_time(self) -> str:
        return self._entry_time

    @property
    def exit_time(self) -> str:
        return self._exit_time

    @property
    def sl(self) -> float:
        return self._sl
    
    @property
    def initial_sl(self) -> float:
        return self._initial_sl 

    @property
    def tp(self) -> str:
        return self._tp

    @property
    def close(self) -> str:
        return self._close

    """
    Actively close an open position
    """
    def close_position(self, time: str, price: float):
        # close position
        if self._state == POSITION_STATE.OPEN.value:
            # calculate profit
            self._profit = (self._price - price) if self._type == POSITION_TYPE.SELL.value else (price - self._price)
            # close position
            self._close = price
            self._state = POSITION_STATE.CLOSED.value
            # calculate and set reward units
            self._reward_units = self.profit / abs(self.price - self._initial_sl) if self._initial_sl is not None else None
            # set exit time
            self._exit_time = time
            # add profit to account
            profit = self._profit * self._vol * self._contract
            self.account.balance += profit

            logger.info("Closed position: %s, profit-in-pips: %s, price: %s, exit: %s, profit: %s, reward: %s",
                        self._id, self._profit, self._price, price, profit, self._reward_units)
        else:
            logger.warn("Attempting to close a closed position")


    """
    Check if a set TP or SL has been breached and close the position
    """
    def check_position_and_update(self, time: str, price_low: float, price_high: float):
        if self._state == POSITION_STATE.CLOSED.value:
            return

        if self._type == POSITION_TYPE.BUY.value:
            # check if there is a set SL
            if self._sl is not None:
                if price_low <= self._sl:
                    self.close_position(time, self._sl)
                    return

            # check if there is a set TP
            if self._tp is not None:
                if price_high >= self._tp:
                    self.close_position(time, self._tp)
                    return
                
            

        elif self._type == POSITION_TYPE.SELL.value:
            # check if there is a set SL
            if self._sl is not None:
                if price_high >= self._sl:
                    self.close_position(time, self._sl)
                    return

            # check if there is a set TP
            if self._tp is not None:
                if price_low <= self._tp:
                    self.close_position(time, self._tp)
                    return

        else:
            logger.warn("Position %s has improper type: %s", self._id, self._type)


    """
    Get unrealised profit
    """
    def get_unrealised_profit(self, price_low: float, price_high: float):
        if self._state == POSITION_STATE.CLOSED.value:
            return 0.0

        if self._type == POSITION_TYPE.BUY.value:
           if price_low > self._price:
               pip = price_high - self._price
           else:
               pip = price_low - self._price
        elif self._type == POSITION_TYPE.SELL.value:
            if price_high < self._price:
                pip = self._price - price_low
            else:
                pip = self._price - price_high

        # calculate profit from pip (profit in pips)
        return pip * self._contract * self._vol
"""
Class for Short psitions
"""
class ShortPosition(Position):
    
    __mapper_args__ = {
        "polymorphic_on": "_type",
        "polymorphic_identity": POSITION_TYPE.SELL.value
    }

    def __init__(self, account_id: UUID, instr: str, entry_time: str, contract_size: float, vol: float, price: float, sl: float = None, tp: float = None) -> None:

        # verify SL and TP values make sense
        if sl is not None:
            if sl <= price:
                logger.error("Rejected stop loss value for Short position.")
                raise ValueError("Stop loss on a Short position must be above entry price.")
            
        if tp is not None:
            if tp >= price:
                logger.error("Rejected take profit value for Short position.")
                raise ValueError("Take profit on a Short position must be below entry price.")

        type = POSITION_TYPE.SELL.value
        super().__init__(account_id, type, instr, entry_time, contract_size, vol, price, sl, tp)

    
    @property
    def sl(self):
        return self._sl

    def move_sl(self, value, close_price):
        if isinstance(value, float) and value > 0 and close_price < value:
            self._sl = float(value)
        else:
            logger.error("Value Error: Stop loss must be a positive float.")
            raise ValueError("Stop loss must be a positive float.")
        
    @property
    def tp(self):
        return self._tp

    @tp.setter
    def tp(self, value):
        if isinstance(value, float) and value > 0:
            self._tp = float(value)
        else:
            logger.error("Value Error: Take Profit must be a positive float.")
            raise ValueError("Take profit must be a positive float.")
        
"""
Class for Long psitions
"""
class LongPosition(Position):
    
    __mapper_args__ = {
        "polymorphic_on": "_type",
        "polymorphic_identity": POSITION_TYPE.BUY.value
    }

    def __init__(self, account_id: UUID, instr: str, entry_time: str, contract_size: float, vol: float, price: float, sl: float = None, tp: float = None) -> None:

        # verify SL and TP values make sense
        if sl is not None:
            if sl >= price:
                logger.error("Rejected stop loss value for Long position.")
                raise ValueError("Stop loss on a Long position must be below entry price.")
            
        if tp is not None:
            if tp <= price:
                logger.error("Rejected take profit value for Long position.")
                raise ValueError("Take profit on a Long position must be above entry price.")

        type = POSITION_TYPE.BUY.value
        super().__init__(account_id, type, instr, entry_time, contract_size, vol, price, sl, tp)

    @property
    def sl(self):
        return self._sl

    
    def move_sl(self, value, close_price):
        if isinstance(value, float) and value > 0 and close_price > value:
            self._sl = float(value)
        else:
            logger.error("Value Error: Stop loss must be a positive float.")
            raise ValueError("Stop loss must be a positive float.")
        
    @property
    def tp(self):
        return self._tp

    @tp.setter
    def tp(self, value):
        if isinstance(value, float) and value > 0:
            self._tp = float(value)
        else:
            logger.error("Value Error: Take Profit must be a positive float.")
            raise ValueError("Take profit must be a positive float.")

# database engine
engine = create_engine("sqlite:///data/my_testdb.db", echo=False)