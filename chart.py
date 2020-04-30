#!/usr/bin/python3

import sys
import json
import sqlite3
import argparse
from dataclasses import dataclass
from time import localtime, strftime, time
from datetime import datetime, timedelta
from typing import List, Optional

from flask import Flask, render_template

from settings import *

app=Flask(__name__)

@dataclass
class Dataset:
    timestamp: List[datetime]
    temperature: List[Optional[float]]
    humidity: List[Optional[float]]


def fetch_data_hourly(time_range: timedelta) -> Dataset:
    db = sqlite3.connect(DATABASE_LOCATION)
    cursor = db.cursor()
    earliest_time = (datetime.utcnow() - time_range).strftime("%Y-%m-%d %H:%M:%S")
    query_string = """
    SELECT DATETIME(timestamp, 'localtime'), temperature, humidity 
      FROM Recordings
      WHERE timestamp >= ? AND timestamp LIKE '%:00:%'
      ORDER BY timestamp
    """
    query = cursor.execute(query_string, (earliest_time, ))
    results = list(query.fetchall())   
    cursor.close()
    db.close()     
    timestamps = [datetime.fromisoformat(x[0]) for x in results]
    temperature = [x[1] for x in results]
    humidity = [x[2] for x in results]
    return Dataset(timestamps, temperature, humidity)


def fetch_data(time_range: timedelta) -> Dataset:
    db = sqlite3.connect(DATABASE_LOCATION)
    cursor = db.cursor()
    earliest_time = (datetime.utcnow() - time_range).strftime("%Y-%m-%d %H:%M:%S")
    query_string = """
    SELECT DATETIME(timestamp, 'localtime'), temperature, humidity 
      FROM Recordings
      WHERE timestamp >= ?
      ORDER BY timestamp
    """
    query = cursor.execute(query_string, (earliest_time, ))
    results = list(query.fetchall())
    cursor.close()
    db.close()
    timestamps = [datetime.fromisoformat(x[0]) for x in results]
    temperature = [x[1] for x in results]
    humidity = [x[2] for x in results]
    return Dataset(timestamps, temperature, humidity)


def format_timestamps(timestamps: List[datetime]) -> List[str]:
    current_time = datetime.utcnow()
    least_recent_timestamp = min(timestamps)
    # The format string for < 24 hours (i.e. "1:30 PM")
    format_string = "%I:%M %p"
    if current_time - least_recent_timestamp >= timedelta(hours=24):
        # The format string for 144 < x <= 24 (i.e. "Mon 01:30 PM")
        format_string = "%a %-I %p"
    if current_time - least_recent_timestamp >= timedelta(hours=144):
        # The format string for >144 hours (i.e. "2020/01/01 13:30")
        format_string = "%Y/%m/%d %H:%M"
    result = [x.strftime(format_string) for x in timestamps]
    return result


def format_data(data: List[Optional[float]]) -> str:
    result = []
    for x in data:
        if x:
            if type(x) == str:
                result.append("\"{}\"".format(x))
            else:
                result.append(str(x))
        else:
            result.append("NaN")
    result = "[" + ",".join(result) + "]"
    return result

@app.route("/")
@app.route("/<length>")
def root_page(length="small"):
    properties = None
    for property in OUTPUT_PROPERTIES:
        if property["name"] == length:
            properties = property
            break
    else:
        return "Unknown Length"
    
    # Convert the hours into a timeframe object
    timeframe = timedelta(hours=properties["duration"])
    
    # Fetch the data
    if properties["detail_level"] == "fine":
        data = fetch_data(timeframe)
    else:
        data = fetch_data_hourly(timeframe)

    return render_template("chart.html", 
        properties=OUTPUT_PROPERTIES, 
        temperature=format_data(data.temperature),
        humidity=format_data(data.humidity),
        labels=format_timestamps(data.timestamp),
        uptime=strftime("%Y-%m-%d %I:%M %p", localtime()))