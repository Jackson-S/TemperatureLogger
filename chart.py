#!/usr/bin/python3

import sys
import json
import sqlite3
import argparse
from dataclasses import dataclass
from time import localtime, strftime, time
from datetime import datetime, timedelta
from typing import List, Optional
from settings import *


@dataclass
class Dataset:
    timestamp: List[datetime]
    temperature: List[Optional[float]]
    humidity: List[Optional[float]]


def fetch_data_hourly(time_range: timedelta) -> Dataset:
    earliest_time = (datetime.utcnow() - time_range).strftime("%Y-%m-%d %H:%M:%S")
    query_string = """
    SELECT DATETIME(timestamp, 'localtime'), temperature, humidity 
      FROM Recordings
      WHERE timestamp >= ? AND timestamp LIKE '%:00:%'
      ORDER BY timestamp
    """
    query = cursor.execute(query_string, (earliest_time, ))
    results = list(query.fetchall())        
    timestamps = [datetime.fromisoformat(x[0]) for x in results]
    temperature = [x[1] for x in results]
    humidity = [x[2] for x in results]
    return Dataset(timestamps, temperature, humidity)


def fetch_data(time_range: timedelta) -> Dataset:
    earliest_time = (datetime.utcnow() - time_range).strftime("%Y-%m-%d %H:%M:%S")
    query_string = """
    SELECT DATETIME(timestamp, 'localtime'), temperature, humidity 
      FROM Recordings
      WHERE timestamp >= ?
      ORDER BY timestamp
    """
    query = cursor.execute(query_string, (earliest_time, ))
    results = list(query.fetchall())        
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


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-t", "--type", action="store", default="small", type=str)
    args = arg_parser.parse_args()

    # Open the Database
    db = sqlite3.connect(DATABASE_LOCATION)
    cursor = db.cursor()

    for property_list in OUTPUT_PROPERTIES:
        if property_list["name"] == args.type:
            properties = property_list
            break
    else:
        print("Unknown output type \"{}\"".format(args.type), file=sys.stderr)
        sys.exit(1)

    # Convert the timeframe into a time delta object
    timeframe = timedelta(hours=properties["duration"])

    # Read the template output file
    with open(TEMPLATE_LOCATION) as in_file:
        chart_data = in_file.read()

    if properties["detail_level"] == "fine":
        data = fetch_data(timeframe)
    else:
        data = fetch_data_hourly(timeframe)
    
    chart_data = chart_data.replace("{{ properties }}", json.dumps(OUTPUT_PROPERTIES))
    chart_data = chart_data.replace("{{ uptime }}", strftime("%Y-%m-%d %I:%M %p", localtime()))
    chart_data = chart_data.replace("{{ temperature }}", format_data(data.temperature))
    chart_data = chart_data.replace("{{ humidity }}", format_data(data.humidity))
    chart_data = chart_data.replace("{{ labels }}", format_data(format_timestamps(data.timestamp)))

    with open(properties["location"], "w") as out_file:
        out_file.write(chart_data)

    cursor.close()
    db.close()