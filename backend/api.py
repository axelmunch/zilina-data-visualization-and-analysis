from api_types import Data
from flask import Flask, abort, request

app = Flask(__name__)


def insert_data(data: Data):
    device_name = data["device"]
    sensors = data["sensors"]
    for sensor in sensors:
        sensor_id = sensor["sensor_id"]
        sensor_type = sensor["sensor_type"]
        measurements = sensor["data"]

        for measurement in measurements:
            timestamp = measurement.get("timestamp")
            for m in measurement["measurements"]:
                name = m["name"]
                value = m["value"]
                print(
                    f"{device_name} - {sensor_id} ({sensor_type}): {name} => {value} ({timestamp})"
                )

                # TODO: Add data point


@app.post("/")
def receive_data():
    data = request.get_json()

    match data:
        case dict():
            print("Dictionary")
            insert_data(data)
        case list():
            print("List")
            for e in data:
                insert_data(e)
        case _:
            abort(400)

    return ""
