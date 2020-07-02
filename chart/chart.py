#!/usr/bin/python3

import os
import sys
import sqlite3
from dataclasses import dataclass
from time import localtime, strftime, time
from datetime import datetime, timedelta
from typing import List, Optional, Any

from flask import Flask, render_template, request

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
    query = cursor.execute(query)
    result = query.fetchall()
    cursor.close()
    database.close()

    return result


def create_dataset(data: List[List[str]]) -> Dataset:
    times = [datetime.fromisoformat(x[0]) for x in data]
    values = [x[1] for x in data]
    return Dataset(times, values)


def fetch_data(range: timedelta, datatype: str, device: str) -> Dataset:
    query = """
    SELECT DATETIME(time, 'localtime'), value 
        FROM Responses
        WHERE device = ? 
            AND type = ?
            AND timestamp >= ?;
    """

    # Convert the range we want to the least recent date in the range, and convert it to a string format SQLite understands    
    earliest_time = (datetime.utcnow() - range).strftime("%Y-%m-%d %H:%M:%S")

    parameters = [device, datatype, earliest_time]

    query_response = database_query(query, parameters)

    return create_dataset(query_response)


def pretty_print_timestamps(timestamp_list: List[datetime]) -> List[str]:
    # Get the range of times covered by the list
    max_time_delta = datetime.utcnow() - min(timestamp_list)
    
    if max_time_delta >= timedelta(weeks=1):
        timestamp_format = "%Y/%m/%d %H:%M"
    elif max_time_delta >= timedelta(days=1):
        timestamp_format = "%a %-I %p"
    else:
        timestamp_format = "%I:%M %p"

    # Convert the times to the format string decided above and return
    return [x.strftime(timestamp_format) for x in timestamp_list]


@app.route("/")
def root_page():
    # Get the time delta in hours (default to 24)
    timeframe = timedelta(hours=request.args.get("timeframe", default=24, type=int))
    
    datatype = request.args.get("datatype", default="temperature", type=str)
    
    device = request.args.get("device", default=0, type=int)
    
    # Fetch the data
    dataset = fetch_data(timeframe, datatype, device)

    return render_template("chart.html", 
        properties=OUTPUT_PROPERTIES, 
        temperature=data.temperature,
        humidity=data.humidity,
        labels=format_timestamps(data.timestamp),
        uptime=strftime("%Y-%m-%d %I:%M %p", localtime()))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')