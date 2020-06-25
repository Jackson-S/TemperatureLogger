#!/usr/bin/python3

import os
import sys
import sqlite3
import paho.mqtt.client as mqtt

from typing import Optional, Iterable, List

import requests


class DatabaseManager:
    def __init__(self, path: os.path):
        self.path = path

        if not os.path.isfile(path):
            self._create_database()

    def _create_database(self):
        # Connect to the database (will create the database in the process)
        database = sqlite3.connect(self.path)

        schema = """
        CREATE TABLE IF NOT EXISTS RecordingType (
            name STRING PRIMARY KEY,
            unit STRING NOT NULL
        );

        INSERT OR IGNORE INTO RecordingType VALUES ('temperature', 'celsius');
        INSERT OR IGNORE INTO RecordingType VALUES ('humidity', 'percent');
        INSERT OR IGNORE INTO RecordingType VALUES ('pressure', 'hectopascal');

        CREATE TABLE IF NOT EXISTS Responses (
        time DATETIME DEFAULT CURRENT_TIMESTAMP,
        device STRING NOT NULL,
        type STRING NOT NULL REFERENCES RecordingType(name),
        value FLOAT NOT NULL
        );
        """

        # Initialise the database
        cursor = database.cursor()
        try:
            cursor.execute(schema)
        except sqlite3.DatabaseError as error:
            print(f"Unable to initialize database:\n{error}", file=sys.stderr)
            sys.exit(1)

        cursor.close()
        database.commit()
        database.close()

    def record(self, device: str, measurement_type: str, value: float) -> bool:
        success = True
        query = "INSERT INTO Responses (device, type, value) VALUES (?, ?, ?)"
        arguments = (device, measurement_type, value)
        
        database = sqlite3.connect(self.path)
        cursor = database.cursor()

        try:
            cursor.execute(query, arguments)
            print(f"Added measurement {device}: {value} ({measurement_type}) to database.")
        except sqlite3.DatabaseError as error:
            print(f"Error inserting into database:\n{error}", file=sys.stderr)
            success = False

        cursor.close()
        database.commit()
        database.close()
        return success


def get_sensors(sensors: str) -> List[str]:
    if (sensors == None):
        print("Environment variable SENSORS is unset. Format should be SENSOR_A,SENSOR_B,etc", file=sys.stderr)
        sys.exit(1)
    if len(sensors) == 0:
        print("No sensors have been specified, use environment variable SENSORS=SENSOR_A,SENSOR_B,etc", file=sys.stderr)
        sys.exit(1)
    return sensors.split(",")


def mqtt_connect(client, userdata, flags, rc) -> None:
    for sensor in self.sensors:
        topic = sensor + "/#"
        print(f"Subscribing to {topic}")
        self.client.subscribe(topic)


def mqtt_message(client, userdata, message) -> None:
    topic = message.topic
    device = topic.split("/")[0]
    measurement_type = topic.split("/")[-1]
    value = message.payload
    print(f"Recieved message from {device}: [{measurement_type}: {value}]")
    try:
        value = float(value)
    except ValueError:
        print("Unable to convert value to number, ignoring message")
        return
    global database
    database.record(device, measurement_type, value)


def check_environment(variable: str) -> str:
    retrieved_variable = os.getenv(variable)
    if not retrieved_variable:
        print(f"{variable} environment variable is not set!")
        sys.exit(1)
    return retrieved_variable


if __name__ == "__main__":
    # Check the environment
    database_location = check_environment("DATABASE_LOCATION")
    device_address = check_environment("DEVICE_ADDRESS")
    sensors = check_environment("SENSORS")

    client = mqtt.Client()
    database = DatabaseManager(database_location)
    sensors = get_sensors(sensors)
    client.on_connect = mqtt_connect
    client.on_message = mqtt_message
    client.connect(device_address)
    client.loop_forever()
