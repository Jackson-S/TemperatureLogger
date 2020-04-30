from os import path, getenv

# The IP Address or URL of the sensor
SENSOR_ADDRESS = getenv("SENSOR_ADDRESS", "127.0.0.1")

# The base directory for both input and output files
INPUT_DIRECTORY = getenv("INPUT_DIRECTORY", "/logger/")

# Locations of input files
TEMPLATE_LOCATION = path.join(INPUT_DIRECTORY, "chart.html")
DATABASE_LOCATION = path.join(INPUT_DIRECTORY, "temperatures.db")

# Parameters for the output files:
# {
#   "name": the name of the item as used in -t NAME when running the program
#   "location": output path,
#   "duration": duration in hours,
#   "duration_string": the name of the page in-browser
#   "detail_level": "fine" for 5 minute intervals, "coarse" for 1 hour intervals
# }
#
# Custom properties can be run using:
# python3 -t PROPERTY_NAME
OUTPUT_PROPERTIES = [
    {
        "name": "small",
        "duration": 24,
        "duration_string": "1 Day",
        "detail_level": "fine"
    },
    {
        "name": "medium",
        "duration": 168,
        "duration_string": "1 Week",
        "detail_level": "coarse"
    },
    {
        "name": "large",
        "duration": 672,
        "duration_string": "1 Month",
        "detail_level": "coarse"
    },
    {
        "name": "year",
        "duration": 8760,
        "duration_string": "1 Year",
        "detail_level": "coarse"
    }
]
