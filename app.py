from config import strategy, options, extras, simulation
from animus import Animus
from kraken import Constants
import pika
import json


animus = Animus()

animus.sim_speed = simulation["sim_speed"]
animus.publish_cycle = simulation["publish_cycle"]
animus.publish_live_data = simulation["publish_live_data"]
animus.annotation_candle_length = simulation["annotation_candle_length"]

# establish pika connenction and queue
if animus.publish_live_data:
    conn_params = pika.ConnectionParameters("localhost")
    conn = pika.BlockingConnection(conn_params)
    channel = conn.channel()
    channel.queue_declare("mt5_sim_data")


# data publishing
def publish_live_data():

    message = animus.get_running_simulation_data()

    channel.basic_publish(exchange="", routing_key="mt5_sim_data", body=json.dumps(message))


# define the backtest app
def run_backtest(strategy, options, extras, publish_live_data):
    animus.run_backtest(
        options["start_date"],
        options["end_date"],
        strategy,
        options,
        extras,
        publish_live_data,
        options["raw_pst_data"],
        options["raw_sr_data"],
        options["sr_refresh_window"],
        Constants.ZONING_MODE.WICK)
    

    return "Simulation complete"

# start simlation
run_backtest(strategy, options, extras, publish_live_data)

if animus.publish_live_data:
    # close pika connection
    conn.close()