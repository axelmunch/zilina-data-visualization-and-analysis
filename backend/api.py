import time
from typing import List

from api_types import Data
from flask import Flask, abort, request
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ----- InfluxDB Configuration -----
INFLUX_URL = "http://localhost:8086"  # Use "influxdb" as hostname inside Docker
INFLUX_TOKEN = "klQGaUK53OtG1Bzk1Ezon9N-_7fM9TSSMHOsivQoFthzGgH_53E1GhOiFoCNq8Y92y64BKx0gtML12N43fEyoA=="
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "sensor_data"


# ----- Wait for InfluxDB to become ready -----
def wait_for_influxdb(max_retries=10, delay=5):
    for attempt in range(max_retries):
        try:
            client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
            health = client.health()
            if health.status == "pass":
                print("✅ InfluxDB is ready.")
                return client
        except Exception as e:
            print(
                f"⏳ Attempt {attempt + 1}/{max_retries}: InfluxDB not ready yet ({e})"
            )
        time.sleep(delay)
    raise RuntimeError("❌ Failed to connect to InfluxDB after multiple attempts.")


client = wait_for_influxdb()
write_api = client.write_api(write_options=SYNCHRONOUS)

app = Flask(__name__)


def extract_data(data: Data):
    data_points = []

    device_name = data["device"]
    sensors = data["sensors"]
    for sensor in sensors:
        sensor_id = sensor["sensor_id"]
        sensor_type = sensor["sensor_type"]
        measurements = sensor["data"]

        for measurement in measurements:
            timestamp = measurement.get("timestamp")

            data_point = (
                Point(sensor_type)
                .tag("device", device_name)
                .tag("sensor", sensor_id)
                .time(timestamp, WritePrecision.NS)
            )

            for m in measurement["measurements"]:
                name = m["name"]
                value = m["value"]
                print(
                    f"{device_name} - {sensor_id} ({sensor_type}): {name} => {value} ({timestamp})"
                )

                data_point.field(name, value)

            data_points.append(data_point)

    return data_points


def insert_data(data: list[Data]):
    data_points = []

    for e in data:
        data_points.extend(extract_data(e))

    print(data_points)
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=data_points)
    print(f"✅ Wrote {len(data_points)} data points")


@app.post("/")
def receive_data():
    data = request.get_json()

    match data:
        case dict():
            print("Dictionary")
            insert_data([data])
        case list():
            print("List")
            insert_data(data)
        case _:
            abort(400)

    return ""
