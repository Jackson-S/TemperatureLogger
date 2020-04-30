#!/usr/bin/python3

import sys
import json
import sqlite3
import requests
from settings import *

db = sqlite3.connect(DATABASE_LOCATION)
cursor = db.cursor()

temperature = None
humidity = None

query_text = "INSERT INTO Recordings (temperature, humidity) VALUES (?, ?)"

try:
    response = requests.get("http://{}/".format(SENSOR_ADDRESS), timeout=2)
except requests.Timeout:
    print("No response received from server.", file=sys.stderr)
    cursor.execute(query_text, (temperature, humidity))
    exit(1)

if response.status_code == requests.codes.ok:
    response_json = json.loads(response.content)
    
    if (type(response_json) is dict) and ("temperature" and "humidity" in response_json):
        temperature = response_json["temperature"]
        humidity = response_json["humidity"]
    else:
        print("Invalid response received from server: \n\"{}\"".format(response.content), file=sys.stderr)

cursor.execute(query_text, (temperature, humidity))

cursor.close()
db.commit()
db.close()
