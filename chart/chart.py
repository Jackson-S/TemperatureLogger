#!/usr/bin/python3

import os
import sys
import sqlite3
import statistics
from dataclasses import dataclass
from time import localtime, strftime, time
from datetime import datetime, timedelta
from typing import List, Optional, Any

from flask import Flask, render_template, request, jsonify

app=Flask(__name__)

@dataclass
class Dataset:
    time: List[datetime]
    value: List[float]


def database_query(query: str, parameters: List[Any]) -> List[Any]:
    # Get the database location from the OS environment (should be set by docker)
    database_location = os.getenv("DATABASE_LOCATION")

    database = sqlite3.connect(database_location)
    cursor = database.cursor()
    query = cursor.execute(query, parameters)
    result = query.fetchall()
    cursor.close()
    database.close()

    return result


def create_dataset(data: List[List[str]]) -> Dataset:
    times = [datetime.fromisoformat(x[0]) for x in data]
    values = [x[1] for x in data]
    return Dataset(times, values)


def filter_data(data: Dataset) -> Dataset:
    if len(data.time) == 0:
        return data

    # Sort the data
    sorted_dataset = sorted([*zip(data.time, data.value)], key=lambda x: x[0])

    maximum_response_size = 500

    new_times = []
    new_values = []

    # Get the amount minimum amount of minutes between each recording
    earliest_time = sorted_dataset[0][0]
    min_timeframe = (datetime.utcnow() - earliest_time).total_seconds() / 60 / maximum_response_size

    skipped_values = []

    # Filter out values that aren't within the minimum timeframe
    for time, value in sorted_dataset:
        if len(new_times) == 0 or len(new_values) == 0:
            new_times.append(time)
            new_values.append(value)
        elif (time - new_times[-1]).total_seconds() / 60 >= min_timeframe:
            # Get the average of all the skipped values
            skipped_values.append(value)
            mean = statistics.mean(skipped_values)
            rounded_mean = round(mean, 2)
            skipped_values = []

            # Append the average
            new_times.append(time)
            new_values.append(rounded_mean)
        else:
            # Append the value to be averaged later
            skipped_values.append(value)

    return Dataset(new_times, new_values)


def fetch_data(time_range: timedelta, datatype: str, device: str) -> Dataset:
    query = """
    SELECT DATETIME(time, 'localtime'), value 
        FROM Responses
        WHERE device = ? 
            AND type = ?
            AND time >= ?;
    """

    # Convert the range we want to the least recent date in the range, and convert it to a string format SQLite understands    
    earliest_time = (datetime.utcnow() - time_range).strftime("%Y-%m-%d %H:%M:%S")

    parameters = [device, datatype, earliest_time]

    query_response = database_query(query, parameters)

    return filter_data(create_dataset(query_response))


def to_iso_timestamp(timestamp_list: List[datetime]) -> List[str]:
    return [x.isoformat() for x in timestamp_list]


def get_devices() -> List[str]:
    query = "SELECT DISTINCT(device) FROM Responses ORDER BY device;"
    query_result = database_query(query, [])
    return [str(x[0]) for x in query_result]


def get_datatypes() -> List[str]:
    query = "SELECT name FROM RecordingType ORDER BY name;"
    query_result = database_query(query, [])
    return [str(x[0]) for x in query_result]


@app.route("/")
def root_page():
    devices = get_devices()
    datatypes = get_datatypes()
    datatypes = [x.title() for x in datatypes]

    return render_template("index.html", devices=devices, datatypes=datatypes)


@app.route("/<timeframe>/<device_index>/<datatype>")
def request_data(timeframe="24", device_index="0", datatype="temperature"):
    device = get_devices()[int(device_index)]
    timeframe = timedelta(hours=int(timeframe))

    # Fetch the data
    dataset = fetch_data(timeframe, datatype, device)
    labels = to_iso_timestamp(dataset.time)
    values = dataset.value
    
    json_data = {"type": datatype.title(), "labels": labels, "values": values}

    return jsonify(json_data)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')