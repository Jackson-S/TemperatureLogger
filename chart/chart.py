#!/usr/bin/python3

import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Any, Iterator, Set

from flask import Flask, render_template, request, jsonify

app=Flask(__name__)

DEVICES = None
DATATYPES = None
MAX_DATA_POINTS = 500

# Get the database location from the OS environment (should be set by docker)
DATABASE_LOCATION = os.getenv("DATABASE_LOCATION")


class DataPoint:
    def __init__(self, time: str, value: float, type: str):
        self.assigned_values = set(type)
        self.time: datetime = datetime.fromisoformat(time)
        self.temperature: float = None
        self.humidity: float = None
        self.pressure: float = None
        self.assign_value(value, type)
    
    def assign_value(self, value: float, type: str) -> None:
        if (type == "temperature"):
            self.temperature = value
        elif (type == "humidity"):
            self.humidity = value
        elif (type == "pressure"):
            self.pressure = value
        self.assigned_values |= set(type)


def database_query(query: str, params: List[Any] = []) -> Iterator[Any]:
    database = sqlite3.connect(DATABASE_LOCATION)
    database.set_trace_callback(lambda x: print(x))
    results = database.execute(query, params)
    return results


def filter_data(data: Iterator[DataPoint]) -> Iterator[DataPoint]:
    first_point = data[0]
    last_point = first_point

    yield first_point

    # Get the amount minimum amount of minutes between each recording
    min_timeframe = (datetime.utcnow() - first_point.time).total_seconds() / 60 / MAX_DATA_POINTS

    # Filter out values that aren't within the minimum timeframe
    for data_point in data:
        if (data_point.time - last_point.time).total_seconds() / 60 >= min_timeframe:
            last_point = data_point
            yield data_point


def combine_data(query_results: List[Any]) -> List[DataPoint]:
    results: List[DataPoint] = [DataPoint(*next(query_results))]

    for time, value, type in query_results:
        if datetime.fromisoformat(time) - results[-1].time <= timedelta(seconds=300):
            if type not in results[-1].assigned_values:
                results[-1].assign_value(value, type)
            else:
                results.append(DataPoint(time, value, type))
        else:
            results.append(DataPoint(time, value, type))
    
    return results


def fetch_data(time_range: timedelta, device: str) -> List[DataPoint]:
    query = "SELECT time, value, type FROM Responses WHERE time >= ? AND device = ? ORDER BY time ASC"

    # Convert the range we want to the least recent date in the range, and convert it to a string format SQLite understands    
    earliest_time = (datetime.utcnow() - time_range)

    parameters = [earliest_time, device]

    print(parameters)

    query_response = database_query(query, parameters)

    return filter_data(combine_data(query_response))


def get_devices() -> List[str]:
    query = "SELECT DISTINCT(device) FROM Responses ORDER BY device;"
    query_result = database_query(query)
    return list(x[0] for x in query_result)


def get_datatypes() -> List[str]:
    query = "SELECT name FROM RecordingType ORDER BY name;"
    query_result = database_query(query)
    return list(x[0] for x in query_result)


@app.route("/")
def root_page():
    datatypes = [x.title() for x in DATATYPES]

    return render_template("index.html", devices=DEVICES, datatypes=datatypes)


@app.route("/<timeframe>/<device_name>")
def request_data(timeframe="24", device_name="Temperature-Sensor_1"):
    timeframe = timedelta(hours=int(timeframe))
    print(timeframe, device_name, DATABASE_LOCATION)

    # Fetch the data
    dataset = fetch_data(timeframe, str(device_name))
    datapoints = list(dataset)
    
    json_data = {"labels": list(x.time.isoformat() for x in datapoints), 
                 "Temperature": list(x.temperature for x in datapoints),
                 "Humidity": list(x.humidity for x in datapoints),
                 "Pressure": list(x.pressure for x in datapoints)}

    return jsonify(json_data)

if __name__ == '__main__':
    DEVICES = get_devices()
    DATATYPES = get_datatypes()
    app.run(debug=True, host='0.0.0.0')