import time
import random
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ----- Configuration InfluxDB -----
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "klQGaUK53OtG1Bzk1Ezon9N-_7fM9TSSMHOsivQoFthzGgH_53E1GhOiFoCNq8Y92y64BKx0gtML12N43fEyoA=="
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "sensor_data"

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = client.write_api(write_options=SYNCHRONOUS)

# ----- Données simulées -----
devices = ["esp32-01", "esp32-02", "esp32-03"]

def generate_data(device_id):
    now = datetime.utcnow()

    data = []

    # Accelerometer
    point = Point("acceleration") \
        .tag("device", device_id).tag("sensor", "acc-01") \
        .field("x", round(random.uniform(-2, 2), 3)) \
        .field("y", round(random.uniform(-2, 2), 3)) \
        .field("z", round(random.uniform(8, 10), 3)) \
        .time(now, WritePrecision.NS)
    data.append(point)

    # Strain gauge
    point = Point("strain") \
        .tag("device", device_id).tag("sensor", "strain-01") \
        .field("strain", round(random.uniform(0, 1000), 2)) \
        .time(now, WritePrecision.NS)
    data.append(point)

    # Ultrasonic sensor
    point = Point("ultrasonic_distance") \
        .tag("device", device_id).tag("sensor", "ultra-01") \
        .field("distance_cm", round(random.uniform(10, 400), 2)) \
        .time(now, WritePrecision.NS)
    data.append(point)

    # Laser sensor
    point = Point("laser_distance") \
        .tag("device", device_id).tag("sensor", "laser-01") \
        .field("distance_mm", round(random.uniform(500, 2000), 1)) \
        .time(now, WritePrecision.NS)
    data.append(point)

    # Pressure
    point = Point("pressure") \
        .tag("device", device_id).tag("sensor", "press-01") \
        .field("pressure_pa", round(random.uniform(90000, 110000), 1)) \
        .time(now, WritePrecision.NS)
    data.append(point)

    # Temperature
    point = Point("temperature") \
        .tag("device", device_id).tag("sensor", "temp-01") \
        .field("temperature_c", round(random.uniform(15, 35), 2)) \
        .time(now, WritePrecision.NS)
    data.append(point)

    return data

# ----- Boucle d'envoi -----
try:
    while True:
        all_data = []
        for device in devices:
            data = generate_data(device)
            all_data.extend(data)

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=all_data)
        print(f"Wrote data for {len(devices)} devices at {datetime.utcnow().isoformat()}")

        time.sleep(1)

except KeyboardInterrupt:
    print("Simulation stopped.")

finally:
    client.close()
