# Crypto Data Streaming Project

## Overview

This project is a data engineering learning project designed to fetch real-time cryptocurrency prices from Coinbase using websockets, process the data, and visualize it through Grafana dashboards. This project is orchestrated using Docker, making it easy to set up and deploy.
The main purpose of this project is to showcase the power of real-time data engineering using Kafka as a messaging system. By leveraging Kafka producers, the system can easily accommodate additional financial products, such as stocks, by adhering to the same standardized data format. This extensibility allows for the seamless integration of various financial instruments into the existing data pipeline without significant modifications.

![Diagram](/media/diagram.png)


![Dashboard](/media/dashboard.png)


### Features

- **Real-time Data:** Fetches the price of the most important cryptocurrencies using Coinbase websocket that provides data every 5 seconds.
- **Scalable Architecture:** Utilizes Docker for containerization, allowing seamless deployment and scalability.
- **Data Pipeline:** Connects to Coinbase via websockets, sends data to a Kafka broker, consumes it with Telegraf, and stores it in InfluxDB.
- **Visualization:** Grafana is used to create dynamic line and candlestick charts that display the real-time cryptocurrency prices.


## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Docker](#docker)
4. [Coinbase API](#coinbase-api)
5. [Kafka](#kafka)
6. [Telegraf](#telegraf)
7. [InfluxDB](#influxdb)
8. [Grafana](#grafana)


## Prerequisites

This project is designed to be self-contained within Docker containers, simplifying the setup process. To run this project, ensure you have the following prerequisites installed on your system:

- **Docker:** Install Docker to leverage containerization for a consistent and isolated environment.

- **Docker Compose:** Docker Compose is used for orchestrating the containers. Make sure to have Docker Compose installed on your machine.

With Docker and Docker Compose in place, you can effortlessly deploy and run the entire project with a single command, making the setup process seamless and efficient.

## Setup

To get the project up and running, follow these steps:

### InfluxDB Configuration

1. Create an `influxv2.env` file based on the provided example [influxv2.env-example](influxv2.env-example). Set the following values:

    ```env
    DOCKER_INFLUXDB_INIT_MODE=setup
    DOCKER_INFLUXDB_INIT_USERNAME=Username
    DOCKER_INFLUXDB_INIT_PASSWORD=Password
    DOCKER_INFLUXDB_INIT_ORG=org
    ## If this is different you would have to change the queries in the grafana dashboards
    DOCKER_INFLUXDB_INIT_BUCKET=coinbase-bucket 
    DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=token
    DOCKER_INFLUXDB_INIT_CLI_CONFIG_NAME=defaultconfig
    ```

    Adjust the username, password, organization, bucket, and admin token as needed.

### Build Coinbase Producer Docker Image

2. Navigate to the [coinbase-producer](coinbase-producer/) directory.

3. Build the Docker image for the Coinbase producer using the following command:

    ```bash
    docker build -t coinbase-producer -f Dockerfile-producer .
    ```

### Run the Project

4. Return to the project root directory.

5. Run the entire project using Docker Compose:

    ```bash
    docker-compose up --build
    ```

This will orchestrate the deployment of all necessary containers, including Coinbase producer, Kafka, Telegraf, InfluxDB, and Grafana. The project is now live, and you can access Grafana dashboards to visualize real-time cryptocurrency prices.


## Docker

#### 1. Grafana

   - **Image:** grafana/grafana-enterprise
   - **Description:** Grafana serves as the visualization platform, displaying real-time cryptocurrency prices through dynamic line and candlestick charts.
   - **Volumes:**
     - `./grafana-provisioning:/etc/grafana/provisioning`
     - `./grafana-dashboards:/var/lib/grafana/dashboards`
   - **Ports:** 3000 
   - **Environment Variables:** Loaded from `influxv2.env`
   - **Dependencies:** InfluxDB, Kafka Initialization

#### 2. Zookeeper

   - **Image:** confluentinc/cp-zookeeper:latest
   - **Description:** Zookeeper is a distributed coordination service, essential for Kafka's functioning.
   - **Ports:** 2181

#### 3. Broker (Kafka)

   - **Image:** confluentinc/cp-kafka:latest
   - **Description:** Kafka acts as the central message broker, handling the streaming of cryptocurrency prices.
   - **Ports:** 
     - 9092 
     - 19092 
   - **Environment Variables:** Defined in the Docker Compose file
   - **Dependencies:** Zookeeper

#### 4. Init-Kafka

   - **Image:** confluentinc/cp-kafka:latest
   - **Description:** Initializes Kafka topics required for the project.
   - **Dependencies:** Broker
   - **Command:** Initializes Kafka topics and lists existing topics.

#### 5. Coinbase Producer

   - **Image:** coinbase-producer:latest
   - **Description:** Fetches real-time cryptocurrency prices from Coinbase and sends them to the Kafka broker.
   - **Dependencies:** Kafka Initialization, Broker

#### 6. InfluxDB

   - **Image:** influxdb:2.7.4
   - **Description:** InfluxDB is the time-series database where cryptocurrency prices are stored.
   - **Ports:** 8086 
   - **Environment Variables:** Loaded from `influxv2.env`
   - **Volumes:**
     - `./influxdb2/config:/etc/influxdb2`
     - `./influxdb2/db:/var/lib/`

#### 7. Telegraf

   - **Image:** telegraf:1.29.1
   - **Description:** Telegraf consumes data from Kafka and writes it to InfluxDB, facilitating the data flow within the pipeline.
   - **Volumes:** `./telegraf/telegraf.conf:/etc/telegraf/telegraf.conf:ro`
   - **Environment Variables:** Loaded from `influxv2.env`
   - **Dependencies:** InfluxDB, Kafka Initialization

## Coinbase API

The [script](coinbase-producer/src/producer.py) establishes a WebSocket connection to the Coinbase API, subscribing to the "ticker_batch" channel for the specified cryptocurrencies:

```python
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
```

Upon receiving messages from the WebSocket, the script formats the data and publishes it to the Kafka broker in the "ticker_batch" topic:
 ```python
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
 ```

## Kafka

 Apache Kafka is used as a central message broker to facilitate the seamless flow of real-time cryptocurrency price data. The Kafka setup involves topic creation, data production, and consumption within the Docker containers.

### Kafka Topic Initialization

The initialization of Kafka topics is handled by the `init-kafka` Docker container. It executes a script to create the required topic, "ticker_batch," ensuring it is ready for data ingestion:

```yaml
init-kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - broker
    container_name: init-kafka
    entrypoint: [ '/bin/sh', '-c' ]
    command: |
      "
      kafka-topics --bootstrap-server broker:19092 --list
      echo -e 'Creating kafka topics'
      kafka-topics --bootstrap-server broker:19092 --create --if-not-exists --topic ticker_batch --replication-factor 1 --partitions 1
      echo -e 'Successfully created the following topics:'
      kafka-topics --bootstrap-server broker:19092 --list
      "
    networks:
      - broker-kafka
```

### Kafka Producer
The Coinbase producer script [coinbase-producer.py](coinbase-producer/src/producer.py) acts as the Kafka producer, pushing real-time cryptocurrency prices to the "ticker_batch" topic:

```python
producer.produce(TICKER_BATCH_TOPIC, value = bytes(f'{json_data}','UTF-8'))
```
### Kafka Consumer
Telegraf, running in a separate Docker container, acts as the Kafka consumer, consuming data from the "ticker_batch" topic and forwarding it to InfluxDB for storage. The Telegraf configuration (telegraf.conf) specifies the Kafka input plugin:
```yml
[[inputs.kafka_consumer]]
  brokers = ["broker:19092"]
  topics = ["ticker_batch"]
```
## Telegraf

Telegraf plays a vital role by serving as the data consumer from Kafka and the producer to InfluxDB. The configuration file, [telegraf.conf](telegraf/telegraf.conf), defines the necessary settings for both Kafka consumption and InfluxDB data output.

Telegraf is configured to output data to InfluxDB using the InfluxDB v2 output plugin:

```yaml
[[outputs.influxdb_v2]]
  ## The URLs of the InfluxDB cluster nodes.
  urls = ["http://influxdb:8086"]

  ## Token for authentication.
  token = "${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}"
  
  ## Organization is the name of the organization you wish to write to; must exist.
  organization = "${DOCKER_INFLUXDB_INIT_ORG}"
  
  ## Destination bucket to write into.
  bucket = "${DOCKER_INFLUXDB_INIT_BUCKET}"
```
Telegraf is configured to consume data from the "ticker_batch" topic in Kafka using the Kafka input plugin.This section specifies the Kafka broker details, the topic to consume, and the data format (JSON). Additionally, it defines how to extract timestamp information from the incoming data:

```yaml
[[inputs.kafka_consumer]]
  ## Kafka brokers.
  brokers = ["broker:19092"]

  ## Topics to consume.
  topics = ["ticker_batch"]

  max_message_len = 1000000
  data_format = "json"
  tag_keys = ["product"]
  json_time_key = "w_time"
  json_time_format = "unix"
```
The agent section includes a configuration to omit the hostname because it is not necessary:
```yaml
[agent]
  omit_hostname = true
```


## InfluxDB

InfluxDB serves as the central time-series database for storing real-time cryptocurrency price data. The configuration for InfluxDB is managed through the `influxv2.env` file and the Docker Compose settings.

In the `influxv2.env` file, the necessary parameters for initializing InfluxDB are defined. These parameters include the mode, username, password, organization, bucket, and admin token:

```env
DOCKER_INFLUXDB_INIT_MODE=setup
DOCKER_INFLUXDB_INIT_USERNAME=Username
DOCKER_INFLUXDB_INIT_PASSWORD=Password
DOCKER_INFLUXDB_INIT_ORG=org
## If this is different you would have to change the queries in the grafana dashboards
DOCKER_INFLUXDB_INIT_BUCKET=coinbase-bucket
DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=token
DOCKER_INFLUXDB_INIT_CLI_CONFIG_NAME=defaultconfig
```

Telegraf, acting as the data consumer, receives real-time cryptocurrency prices from the Kafka broker. It then processes and forwards this data to InfluxDB based on the configured parameters. The data is stored in the specified InfluxDB organization and bucket for future analysis and visualization in Grafana.

## Grafana

Grafana is the visualization platform used in the Crypto Data Streaming project, providing dynamic dashboards for monitoring and analyzing real-time cryptocurrency prices. The dashboard configurations are stored in the [grafana-provisioning](grafana-provisioning/) directory, including datasources and dashboard settings.

### Datasource Configuration

Datasource settings are defined in the [grafana-provisioning/datasources](grafana-provisioning/datasources/) directory. These settings connect Grafana to the InfluxDB database where cryptocurrency price data is stored.

### Dashboard Configuration

The dashboards are defined in the [grafana-provisioning/dashboards](grafana-provisioning/dashboards/) directory. The main dashboard includes two key charts: a timeline chart and a candlestick chart.

### Variable Configuration
The variables in the queries, such as `${product}` (selected cryptocurrency) and `${Interval}` (time interval), allow users to dynamically interact with the dashboard, selecting different cryptocurrencies and time ranges for analysis.

#### Timeline Chart

The timeline chart displays the mean prices of the selected cryptocurrency over a specified time interval. The query used for this chart is as follows:

```plaintext
from(bucket: "coinbase-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "kafka_consumer")
  |> filter(fn: (r) => r["_field"] == "price")
  |> filter(fn: (r) => r["product"] == "${product}")
  |> aggregateWindow(every: ${Interval}, fn: mean, createEmpty: false)
  |> yield(name: "mean")
```
![Timeline](/media/timeline.png)
#### Candlestick Chart

The candlestick chart displays the open, close, high and low prices of the selected cryptocurrency over a specified time interval. The query used for this chart is as follows:

```plaintext
close = from(bucket: "coinbase-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "kafka_consumer")
  |> filter(fn: (r) => r["_field"] == "price")
  |> filter(fn: (r) => r["product"] == "${product}")
  |> aggregateWindow(every: ${Interval}, fn: last)
  |> set(key: "newValue", value: "close")

open = from(bucket: "coinbase-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "kafka_consumer")
  |> filter(fn: (r) => r["_field"] == "price")
  |> filter(fn: (r) => r["product"] == "${product}")
  |> aggregateWindow(every: ${Interval}, fn: first)
  |> set(key: "newValue", value: "open")

low = from(bucket: "coinbase-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "kafka_consumer")
  |> filter(fn: (r) => r["_field"] == "price")
  |> filter(fn: (r) => r["product"] == "${product}")
  |> aggregateWindow(every: ${Interval}, fn: min)
  |> set(key: "newValue", value: "low")

high = from(bucket: "coinbase-bucket")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "kafka_consumer")
  |> filter(fn: (r) => r["_field"] == "price")
  |> filter(fn: (r) => r["product"] == "${product}")
  |> aggregateWindow(every: ${Interval}, fn: max)
  |> set(key: "newValue", value: "high")

union(tables: [close, open, low, high])
  |> pivot(rowKey:["_time"], columnKey: ["newValue"], valueColumn: "_value")
```
![Candlestick](/media/candlestick.png)
