import websocket
import json
from confluent_kafka import Producer
from datetime import datetime
import time

#More info about coinbase websocket https://docs.cloud.coinbase.com/exchange/docs/websocket-channels#ticker-batch-channel
COINBASE_PARAMS = {
    "type": "subscribe",
    "product_ids": [
        "ETH-USD",
        "BTC-USD",
        "SOL-USD",
        "BNB-USD",
        "XRP-USD",
        "ADA-USD",
        "AVAX-USD",
        "DOT-USD",
    ],
    "channels": ["ticker_batch"]
}

TICKER_BATCH_TOPIC = "ticker_batch"


def format_data(mess):
    data = {}
    data["product"] = mess["product_id"]
    data["w_time"] = int(datetime.fromisoformat(mess["time"].rstrip('Z')).timestamp())
    data["price"] = float(mess["price"])
    return json.dumps(data)

def on_message(ws, message):
    mess = json.loads(message)
    if "product_id" in mess:
        json_data = format_data(mess)
        producer.produce(TICKER_BATCH_TOPIC, value = bytes(f'{json_data}','UTF-8'))

def on_error(ws, error):
    print(f"ERROR-------------{error}")

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    print("Opened connection")
    ws.send(json.dumps(COINBASE_PARAMS))


if __name__ == "__main__":
    time.sleep(30)
    kafka_conf = {'bootstrap.servers': 'broker:19092',
        'client.id': 'coinbase-producer'}
    producer = Producer(kafka_conf)

    ws = websocket.WebSocketApp("wss://ws-feed.exchange.coinbase.com",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    ws.run_forever(reconnect=5)