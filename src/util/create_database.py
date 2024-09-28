from trade_objects import *
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

Base.metadata.create_all(engine)