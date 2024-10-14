from kraken.ict_components.types import PST_DATA_LEVEL, DIRECTION
from .types import POSITION_TYPE
from util.utility import round_to_ref
import logging

# set up logging
logger = logging.getLogger(__name__)
# set general log level
logger.setLevel("INFO")
# shared log formatter
formatter = logging.Formatter("%(asctime)s : %(name)s [%(funcName)s] : %(levelname)s -> %(message)s")

"""
This class implements strategies based on structural data from the Kraken.
"""
class Advisor:
    def __init__(self, strategy: str, options) -> None:
        self._strategy: str = strategy
        self._options = options
        self._choc_expired = False
        self._bos_expired = False
        self._mods_bos_expired = False

    def choc_reset(self):
        self._choc_expired = False

    def choc_expire(self):
        self._choc_expired = True

    def bos_reset(self):
        self._bos_expired = False

    def bos_expire(self):
        self._bos_expired = True

    def mods_bos_reset(self):
        self._mods_bos_expired = False

    def mods_bos_expire(self):
        self._mods_bos_expired = True


    def generate_positions(self, closing_price, balance, signals):
        if not signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc"]:
            self.choc_reset()

        match self._strategy:
            case "SIMPLE_TREND":
                # trading simple trends
                # if secondary structure trend is UP we are looking to buy when primary structure turns to the up side 
                if (signals["pst_" + PST_DATA_LEVEL.MID.value]["seg_dir"] == DIRECTION.UP or \
                    (signals["pst_" + PST_DATA_LEVEL.MID.value]["seg_dir"] == DIRECTION.DOWN and signals["pst_" + PST_DATA_LEVEL.MID.value]["choc"])) \
                    and ((signals["pst_" + PST_DATA_LEVEL.HIGH.value]["seg_dir"] == DIRECTION.UP or \
                        (signals["pst_" + PST_DATA_LEVEL.HIGH.value]["seg_dir"] == DIRECTION.DOWN and signals["pst_" + PST_DATA_LEVEL.HIGH.value]["choc"])) or self._options["exclude_high_trend"]):

                    if self._options["entry"] == "CHOC_CONFIRMED":
                        if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc_confirmed"] and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.DOWN: # down changing to UP
                            # enter position
                            # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["low"] if self._options["sl_level"] == "KEY_LEVEL" else signals["pst_" + PST_DATA_LEVEL.LOW.value]["segment_range"]["lowest"]
                            sl = sl - (closing_price - sl) * self._options["sl_level_margin"]
                            tp = closing_price + (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.BUY, closing_price, sl, tp, balance, signals, self._options)
                    elif self._options["entry"] == "CHOC":
                        if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc"] and not self._choc_expired and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.DOWN: # down changing to UP
                            # enter position
                            # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["low"] if self._options["sl_level"] == "KEY_LEVEL" else signals["pst_" + PST_DATA_LEVEL.LOW.value]["segment_range"]["lowest"]
                            sl = sl - (closing_price - sl) * self._options["sl_level_margin"]
                            tp = closing_price + (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            self.choc_expire()
                            return self.build_position(POSITION_TYPE.BUY, closing_price, sl, tp, balance, signals, self._options)
                    else:
                        return None
                    
                elif (signals["pst_" + PST_DATA_LEVEL.MID.value]["seg_dir"] == DIRECTION.DOWN or \
                       (signals["pst_" + PST_DATA_LEVEL.MID.value]["seg_dir"] == DIRECTION.UP and signals["pst_" + PST_DATA_LEVEL.MID.value]["choc"])) \
                        and ((signals["pst_" + PST_DATA_LEVEL.HIGH.value]["seg_dir"] == DIRECTION.DOWN or \
                              (signals["pst_" + PST_DATA_LEVEL.HIGH.value]["seg_dir"] == DIRECTION.UP and signals["pst_" + PST_DATA_LEVEL.HIGH.value]["choc"])) or self._options["exclude_high_trend"]):
                    
                    if self._options["entry"] == "CHOC_CONFIRMED":
                        if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc_confirmed"] and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.UP: # down changing to DOWN
                            # enter position
                            # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["high"] if self._options["sl_level"] == "KEY_LEVEL" else signals["pst_" + PST_DATA_LEVEL.LOW.value]["segment_range"]["highest"]
                            sl = sl + (sl - closing_price) * self._options["sl_level_margin"]
                            tp = closing_price - (sl - closing_price) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.SELL, closing_price, sl, tp, balance, signals, self._options)
                    elif self._options["entry"] == "CHOC":
                        if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc"] and not self._choc_expired and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.UP: # down changing to DOWN
                            # enter position
                            # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["high"] if self._options["sl_level"] == "KEY_LEVEL" else signals["pst_" + PST_DATA_LEVEL.LOW.value]["segment_range"]["highest"]
                            sl = sl + (sl - closing_price) * self._options["sl_level_margin"]
                            tp = closing_price - (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            self.choc_expire()
                            return self.build_position(POSITION_TYPE.SELL, closing_price, sl, tp, balance, signals, self._options)
                    else:
                        return None
                    

            case "PRICE_ACTION":
                if (signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc"] and self._options["entry"] in ["CHOC", "CHOC+BOS"] and not self._choc_expired) \
                     or (signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc_confirmed"] and self._options["entry"] in ["CHOC_CONFIRMED", "CHOC_CONFIRMED+BOS"]):
                    

                    # respond to CHOC only once
                    if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc"] and self._options["entry"] in ["CHOC", "CHOC+BOS"]:
                            self.choc_expire()
                    
                    # check if price at significant level
                    trade_zone = self.test_choc_zone_interaction(signals["sr_zones"], 
                                               signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"],
                                               signals["pst_" + PST_DATA_LEVEL.LOW.value]["segment_range"],
                                               closing_price)
                    
                    if trade_zone is not None and trade_zone[0]:

                        if signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.UP:
                            # enter position short position
                            # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["high"] if self._options["sl_level"] == "KEY_LEVEL" else signals["pst_" + PST_DATA_LEVEL.LOW.value]["segment_range"]["highest"]
                            sl = sl if sl > trade_zone[1][1] else trade_zone[1][1]
                            sl = sl + (sl - closing_price) * self._options["sl_level_margin"]
                            tp = closing_price - (sl - closing_price) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.SELL, closing_price, sl, tp, balance, signals, self._options)
                        else:
                            # enter long position
                             # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["low"] if self._options["sl_level"] == "KEY_LEVEL" else signals["pst_" + PST_DATA_LEVEL.LOW.value]["segment_range"]["lowest"]
                            sl = sl if sl < trade_zone[1][0] else trade_zone[1][0]
                            sl = sl - (closing_price - sl) * self._options["sl_level_margin"]
                            tp = closing_price + (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.BUY, closing_price, sl, tp, balance, signals, self._options)
                        

                if (signals["pst_" + PST_DATA_LEVEL.LOW.value]["in_bos"] and self._options["entry"] in ["CHOC+BOS","CHOC_CONFIRMED+BOS"] and not self._bos_expired):
                    

                    # respond to BOS only once
                    self.bos_expire()
                    
                    # check if price at significant level
                    trade_zone = self.test_bos_zone_interaction(signals["sr_zones"], 
                                               signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"],
                                               signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["low"],
                                               signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["high"],
                                               closing_price)
                    
                    if trade_zone is not None and trade_zone[0]:

                        if signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.DOWN \
                            and signals["pst_" + PST_DATA_LEVEL.MID.value]["seg_dir"] == DIRECTION.DOWN \
                            and signals["pst_" + PST_DATA_LEVEL.HIGH.value]["seg_dir"] == DIRECTION.DOWN:
                            # enter position short position
                            # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["high"]
                            sl = sl if sl > trade_zone[1][1] else trade_zone[1][1]
                            sl = sl + (sl - closing_price) * self._options["sl_level_margin"]
                            tp = closing_price - (sl - closing_price) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.SELL, closing_price, sl, tp, balance, signals, self._options)
                        elif signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.UP \
                            and signals["pst_" + PST_DATA_LEVEL.MID.value]["seg_dir"] == DIRECTION.UP \
                            and signals["pst_" + PST_DATA_LEVEL.HIGH.value]["seg_dir"] == DIRECTION.UP:
                            # enter long position
                             # sl
                            sl = signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["low"]
                            sl = sl if sl < trade_zone[1][0] else trade_zone[1][0]
                            sl = sl - (closing_price - sl) * self._options["sl_level_margin"]
                            tp = closing_price + (closing_price - sl) * self._options["reward_ratio"] \
                                if self._options["reward_ratio"] is not None else None
                            return self.build_position(POSITION_TYPE.BUY, closing_price, sl, tp, balance, signals, self._options)
                        
                        else:
                            return None
                # No position created        
                return None
            case _:
                logger.warning("Incorrect parameter for strategy selection. No positions computed.")
                return None

    """
    modify positions that are already open
    """
    def modify_positions(self, closing_price, balance, signals):

        result = {
            "actions": []
        }

        if not signals["pst_" + PST_DATA_LEVEL.LOW.value]["in_bos"]:
            self.bos_reset()

        
        if self._options["exit"] == "CHOC_CONFIRMED":
            if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc_confirmed"] and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.UP: # UP changing to DOWN
                # close_positions
                            
                result["actions"].append(
                    {
                        "action": "CLOSE",
                        "position_type": POSITION_TYPE.BUY.value,
                        "instr": self._options["instr"]
                    })
                        
            elif signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc_confirmed"] and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.DOWN: # DOWN changing to UP
                # close_positions
                result["actions"].append(
                    {
                        "action": "CLOSE",
                        "position_type": POSITION_TYPE.SELL.value,
                        "instr": self._options["instr"]
                    })
                        
        elif self._options["exit"] == "CHOC":
            if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc"] and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.UP: # UP changing to DOWN
                # close_positions
                result["actions"].append(
                    {
                        "action": "CLOSE",
                        "position_type": POSITION_TYPE.BUY.value,
                        "instr": self._options["instr"]
                    })
                        
            if signals["pst_" + PST_DATA_LEVEL.LOW.value]["choc"] and signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.DOWN: # down changing to DOWN
                # close_positions
                result["actions"].append(
                    {
                        "action": "CLOSE",
                        "position_type": POSITION_TYPE.SELL.value,
                        "instr": self._options["instr"]
                    })
                       
                    
        if signals["pst_" + PST_DATA_LEVEL.LOW.value]["in_bos"] and not self._mods_bos_expired:

            result["actions"].append({
                "action": "MOVE_SL",
                "position_type": POSITION_TYPE.SELL.value if signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.DOWN else POSITION_TYPE.BUY.value,
                "instr": self._options["instr"],
                "new_sl_target": signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["high"] if signals["pst_" + PST_DATA_LEVEL.LOW.value]["seg_dir"] == DIRECTION.DOWN \
                    else signals["pst_" + PST_DATA_LEVEL.LOW.value]["key_levels"]["low"]
            })

            self.mods_bos_expire()

        return result
    
       

    def build_position(self, type: POSITION_TYPE, closing_price: float, sl: float, tp: float, balance: float, signals, options):

        volume = (balance * options["risk_per_trade"]) / (abs(closing_price - sl) * options["symbol"]["trade_contract_size"])

        # if volume acceptable
        if volume < options["symbol"]["volume_min"]:
            logger.warn("Volume for {} should be more than {}: Current volume is {}".format(options["instr"], options["symbol"]["volume_min"], volume))
            print("NO TRADE: POSITION REQUIRES TOO HIGH VOLUME")
            return None
        elif volume > options["symbol"]["volume_max"]:
            logger.warn("Volume for {} should be less than {}: Current volume is {}".format(options["instr"], options["symbol"]["volume_max"], volume))
            volume = options["symbol"]["volume_max"]
        else:
            # clean up decimal places
            volume = round_to_ref(volume, options["symbol"]["volume_min"])

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
    test if bos occurs at SR zone
    """
    def test_bos_zone_interaction(self, sr_zones, seg_dir, key_low, key_high, close_price) -> bool:

        zone = None

        bos_seg_dir = DIRECTION.UP if seg_dir == DIRECTION.DOWN else DIRECTION.DOWN

        # choose zone criteria
        if self._options["sr_zone_interaction"] == "TOUCH":
            zone = Advisor.in_zone(sr_zones, key_low \
                if seg_dir == DIRECTION.UP else key_high)
        elif self._options["sr_zone_interaction"] == "PROXIMITY":
            zone = self.around_zone(sr_zones, bos_seg_dir, \
                                    key_low if seg_dir == DIRECTION.UP else key_high)

        if zone is not None:
            return (self.test_zone_exit(zone, bos_seg_dir, close_price) and self.zone_clearence(sr_zones, bos_seg_dir, zone), zone["interval"])
        else:
            # test failed
            return None




    """
    check if choc occurs at SR zone
    """
    def test_choc_zone_interaction(self, sr_zones, seg_dir, segment_range, close_price) -> bool:

        zone = None
        
        # choose zone criteria
        if self._options["sr_zone_interaction"] == "TOUCH":
            zone = Advisor.in_zone(sr_zones, segment_range["highest"] \
                if seg_dir == DIRECTION.UP else segment_range["lowest"])
        elif self._options["sr_zone_interaction"] == "PROXIMITY":
            zone = self.around_zone(sr_zones, seg_dir, segment_range["highest"] \
                if seg_dir == DIRECTION.UP else segment_range["lowest"])

        if zone is not None:
            return (self.test_zone_exit(zone, seg_dir, close_price) and self.zone_clearence(sr_zones, seg_dir, zone), zone["interval"])
        else:
            # test failed
            return None
        
    """
    Check if no other zone interfering with trade
    """
    def zone_clearence(self, sr_zones, seg_dir, zone):
        clearence_size = (zone["interval"][1] - zone["interval"][0]) * self._options["sr_zone_clearence_factor"]
        clearence_zone = [zone["interval"][1], zone["interval"][1] + clearence_size] if seg_dir == DIRECTION.DOWN else [zone["interval"][0] - clearence_size, zone["interval"][0]]

        for sr_zone in sr_zones:
            if not (sr_zone["interval"][0] >= clearence_zone[1] or sr_zone["interval"][1] <= clearence_zone[0]):
                return False
            
        return True

    
    """
    Find the zone in which our key level lies
    """       
    def in_zone(sr_zones, key_level):
        for sr_zone in sr_zones:
            if key_level >= sr_zone["interval"][0] and key_level <= sr_zone["interval"][1]:
                return sr_zone
  
        return None
    
    """
    Find the zone in whose proximity the key level lies
    """
    def around_zone(self, sr_zones, seg_dir , key_level):
        for zone in sr_zones:
            allowed_distance = (zone["interval"][1] - zone["interval"][0]) * self._options["sr_zone_proximity_margin"]
            if (key_level >= zone["interval"][0] and key_level <= (zone["interval"][1] + allowed_distance) \
                and seg_dir == DIRECTION.UP) or \
                (key_level <= zone["interval"][1] and key_level >= (zone["interval"][0] - allowed_distance) \
                and seg_dir == DIRECTION.DOWN):
                return zone
 
        return None

    """
    Check if closing price in the direction of exiting the zone
    """
    def test_zone_exit(self, sr_zone, seg_dir, close_price):
        allowed_distance = (sr_zone["interval"][1] - sr_zone["interval"][0]) * self._options["sr_zone_entry_margin"]

        if seg_dir == DIRECTION.UP:
            distance = sr_zone["interval"][0] - close_price
            if distance > 0 and distance <= allowed_distance:
                #pass
                return True
            else:
                # failed
                return False
        else:
            distance = close_price - sr_zone["interval"][1]
            if distance > 0 and distance <= allowed_distance:
                #pass
                return True
            else:
                # failed
                return False