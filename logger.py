#!/usr/bin/python3

import os
import sys
import math
import json
import time
import sqlite3
import paho.mqtt.client as mqtt

from typing import Optional, Iterable
from datetime import datetime, timedelta
from threading import Timer
from dataclasses import dataclass

import requests


@dataclass
class SensorData:
    temperature: Optional[float]
    humidity: Optional[float]


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


mqtt_sensor_data = SensorData(None, None)


def fetch_data() -> Optional[SensorData]:
    sensor_address = os.getenv("SENSOR_ADDRESS")

    if not sensor_address:
        print("SENSOR_ADDRESS environment variable is not set", file=sys.stderr)
        return None

    sensor_url = f"http://{sensor_address}/"

    try:
        response = requests.get(sensor_url, timeout=5)
    except requests.ConnectionError:
        print(f"Failed to connect to resource {sensor_url}", file=sys.stderr)
        return None

    if not response.status_code is requests.codes.ok:
        print(f"Got response code {response.status_code}", file=sys.stderr)
        return None

    try:
        response_content = json.loads(response.content)
    except json.JSONDecodeError:
        print("Unable to decode JSON data from server", file=sys.stderr)
        return None

    if not isinstance(response_content, dict):
        print("Invalid response type", file=sys.stderr)
        return None

    result = SensorData(
        response_content.get("temperature", None),
        response_content.get("humidity", None)
    )

    return result


def update_database(query: str, arguments: Iterable) -> bool:
    database_location = os.getenv("DATABASE_LOCATION")

    if not database_location:
        print("SENSOR_ADDRESS environment variable is not set", file=sys.stderr)
        return False

    if not os.path.isfile(database_location):
        # Create the database if it doesn't exist
        try:
            _create_database(database_location)
        except sqlite3.DatabaseError as error:
            print(f"Error initialising database:\n{error}", file=sys.stderr)
            return False

    database = sqlite3.connect(database_location)
    cursor = database.cursor()

    try:
        cursor.execute(query, arguments)
    except sqlite3.DatabaseError as error:
        print(f"Error inserting into database:\n{error}", file=sys.stderr)
        cursor.close()
        database.close()
        return False

    cursor.close()
    database.commit()
    database.close()
    return True


def _create_database(path: os.path):
    # Connect to the database (will create the database in the process)
    database = sqlite3.connect(path)
    cursor = database.cursor()

    # Initialise the database
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS Recordings (\n" + \
        "  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,\n" + \
        "  temperature FLOAT,\n" + \
        "  humidity FLOAT\n" + \
        ");"
    )

    cursor.close()

    database.commit()
    database.close()


def _http_record_sensor_data() -> None:
    sensor_data = fetch_data()

    if sensor_data:
        record_sensor_data(sensor_data)


def record_sensor_data(sensor_data: SensorData) -> None:
    query = "INSERT INTO Recordings (temperature, humidity) VALUES (?, ?)"
    arguments = [sensor_data.temperature, sensor_data.humidity]

    # Record the data
    if update_database(query, arguments):
        print(f"{datetime.now()}: Recorded temp: {arguments[0]}, humidity: {arguments[1]}.")


def get_start_time_delta() -> int:
    # Calculate the start of the next even 5 minute period
    current_time = datetime.now()

    next_clock_numeral = (math.ceil(current_time.minute / 5) * 5) % 60
    initialisation_time = current_time.replace(minute=next_clock_numeral)

    # If the time is (55, 59] then the first recording will happen in the next hour
    if next_clock_numeral == 0:
        next_hour = current_time.hour + 1
        initialisation_time = initialisation_time.replace(hour=next_hour)
    
    # Make up the difference in the sub-minute intervals
    sub_minute_delta = timedelta(seconds=current_time.second, microseconds=current_time.microsecond)
    initialisation_time -= sub_minute_delta

    # If the current minutes is a multiple of 5 then we have to go to the next 5 minute period
    if current_time.minute % 5 == 0:
        initialisation_time += timedelta(minutes=5)

    # I'm not confident in my algorithm for this. 
    # I'd rather it shuts down than never runs so assert this and hope for a crash.
    if initialisation_time < datetime.now():
        print("Invalid time calculated. This is a bug.")
        print(initialisation_time, datetime.now())
        sys.exit(1)

    return (initialisation_time - datetime.now()).total_seconds()


def http_start():
    # Wait until the interval
    start_time_delta = get_start_time_delta()

    start_time = datetime.now() + timedelta(seconds=start_time_delta)
    print(f"Will begin recording data every 5 minutes in {start_time_delta} seconds. {start_time.time()}")

    time.sleep(start_time_delta)

    # Do an initial recording
    record_sensor_data()

    # Set a timer to repeat recordings every 5 minutes
    timer = RepeatTimer(5 * 60, record_sensor_data)
    timer.start()


def _mqtt_connect(client, userdata, flags, rc) -> None:
    channel = os.getenv("SENSOR_CHANNEL")
    temperature_topic = channel + "/Temperature"
    humidity_topic = channel + "/Humidity"
    print(f"Subscribing to channels {temperature_topic} and {humidity_topic}.")
    print(temperature_topic, humidity_topic)
    client.subscribe(temperature_topic, 1)
    client.message_callback_add(temperature_topic, _mqtt_message_temperature)
    client.subscribe(humidity_topic, 2)
    client.message_callback_add(humidity_topic, _mqtt_message_humidity)
    print("Completed subscriptions")


def _mqtt_message_temperature(client, userdata, msg) -> None:
    print("Received temperature data")
    global mqtt_sensor_data
    try:
        value = float(msg.payload)
    except ValueError:
        print("Unable to convert value " + msg.payload)
        return

    mqtt_sensor_data.temperature = value
    print(f"Temperature {value}")
    
    if mqtt_sensor_data.temperature and mqtt_sensor_data.humidity:
        record_sensor_data(mqtt_sensor_data)
        mqtt_sensor_data = SensorData(None, None)
        print("Logged sensor data")


def _mqtt_message_humidity(client, userdata, msg) -> None:
    print("Received humidity data")
    global mqtt_sensor_data
    try:
        value = float(msg.payload)
    except ValueError:
        print("Unable to convert value " + msg.payload)
        return

    mqtt_sensor_data.humidity = value
    print(f"Humidity {value}")
    
    if mqtt_sensor_data.temperature and mqtt_sensor_data.humidity:
        record_sensor_data(mqtt_sensor_data)
        mqtt_sensor_data = SensorData(None, None)
        print("Logged sensor data")


def _mqtt_message(client, userdata, msg) -> None:
    print(msg.topic + " " + str(msg.payload))


def mqtt_start():
    client = mqtt.Client()
    client.on_connect = _mqtt_connect
    client.on_message = _mqtt_message
    client.on_log = lambda x: print(x)

    client.connect(os.getenv("DEVICE_ADDRESS"), 1883, 60)

    client.loop_forever(max_packets=10, retry_first_connection=True)


if __name__ == "__main__":
    # Check the environment
    if not os.getenv("DATABASE_LOCATION"):
        print("DATABASE_LOCATION environment variable is not set")
        sys.exit(1)

    #Determine protocol type and begin execution
    if os.getenv("PROTOCOL_TYPE") == "MQTT":
        if not os.getenv("SENSOR_CHANNEL"):
            print("SENSOR_CHANNEL environment variable is not set, use HTTP or set channel")
            sys.exit(1)
        if not os.getenv("DEVICE_ADDRESS"):
            print("DEVICE_ADDRESS environment variable is not set")
            sys.exit(1)
        print("Starting MQTT service")
        mqtt_start()
        sys.exit(1)

    elif os.getenv("PROTOCOL_TYPE") == "HTTP":
        if not os.getenv("SENSOR_ADDRESS"):
            print("SENSOR_ADDRESS environment variable is not set, use MQTT or set channel")
            sys.exit(1)
        print("Starting HTTP service")
        http_start()
        sys.exit(1)

    else:
        print("PROTOCOL_TYPE not specified, MQTT or HTTP")