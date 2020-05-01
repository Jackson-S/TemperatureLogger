#!/usr/bin/python3

import sys
import json
import sqlite3
import requests
import threading
from settings import *

class DatabaseRecorder(threading.Thread):
    def __init__(self, event: threading.Event, period: int):
        threading.Thread.__init__(self)
        self.stopped = event
        self.period = period
    
    def run(self):
        self.call()
        while not self.stopped.wait(self.period):
            self.call()
            
    def call(self):
            try:
                if not record():
                    print("Unknown error occurred")
                else:
                    print("Success")
            except requests.Timeout:
                print("No response received from server")
            except BaseException as e:
                print("Unknown error occurred:")
                print(e)

def record():
    db = sqlite3.connect(DATABASE_LOCATION)
    cursor = db.cursor()

    temperature = None
    humidity = None

    query_text = "INSERT INTO Recordings (temperature, humidity) VALUES (?, ?)"

    response = requests.get("http://{}/".format(SENSOR_ADDRESS), timeout=2)

    if response.status_code == requests.codes.ok:
        response_json = json.loads(response.content)
        
        if (type(response_json) is dict) and ("temperature" and "humidity" in response_json):
            temperature = response_json["temperature"]
            humidity = response_json["humidity"]
        else:
            print("Invalid response received from server: \n\"{}\"".format(response.content))
            return False

    cursor.execute(query_text, (temperature, humidity))

    cursor.close()
    db.commit()
    db.close()

    return True

stopFlag = threading.Event()
thread = DatabaseRecorder(stopFlag, 5)
thread.start()
