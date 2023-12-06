from config import strategy, options, extras
from animus import Animus
import pika
import json


animus = Animus()

animus.sim_speed = 0.25
animus.publish_live_data = True
animus.annotation_candle_length = 200

# establish pika connenction and queue
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
        options["raw_data"]["primary"],
        None,
        None)

    return "Simulation complete"

# start simlation
run_backtest(strategy, options, extras, publish_live_data)

# close pika connection
conn.close()