import random
import time
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ----- InfluxDB Configuration -----
INFLUX_URL = "http://influxdb:8086"  # Use "influxdb" as hostname inside Docker
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

# ----- Simulated devices -----
devices = ["esp32-01", "esp32-02", "esp32-03"]


# ----- Generate data for one device -----
def generate_data(device_id):
    now = datetime.now(timezone.utc)
    data = []

    data.append(
        Point("acceleration")
        .tag("device", device_id)
        .tag("sensor", "acc-01")
        .field("x", round(random.uniform(-2, 2), 3))
        .field("y", round(random.uniform(-2, 2), 3))
        .field("z", round(random.uniform(8, 10), 3))
        .time(now, WritePrecision.NS)
    )

    data.append(
        Point("strain")
        .tag("device", device_id)
        .tag("sensor", "strain-01")
        .field("strain", round(random.uniform(0, 1000), 2))
        .time(now, WritePrecision.NS)
    )

    data.append(
        Point("ultrasonic_distance")
        .tag("device", device_id)
        .tag("sensor", "ultra-01")
        .field("distance_cm", round(random.uniform(10, 400), 2))
        .time(now, WritePrecision.NS)
    )

    data.append(
        Point("laser_distance")
        .tag("device", device_id)
        .tag("sensor", "laser-01")
        .field("distance_mm", round(random.uniform(500, 2000), 1))
        .time(now, WritePrecision.NS)
    )

    data.append(
        Point("pressure")
        .tag("device", device_id)
        .tag("sensor", "press-01")
        .field("pressure_pa", round(random.uniform(90000, 110000), 1))
        .time(now, WritePrecision.NS)
    )

    data.append(
        Point("temperature")
        .tag("device", device_id)
        .tag("sensor", "temp-01")
        .field("temperature_c", round(random.uniform(15, 35), 2))
        .time(now, WritePrecision.NS)
    )

    return data


# ----- Main loop: write data every second -----
try:
    while True:
        all_data = []
        for device in devices:
            all_data.extend(generate_data(device))

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=all_data)
        print(
            f"✅ Wrote data for {len(devices)} devices at {datetime.now(timezone.utc).isoformat()}"
        )

        time.sleep(1)

except KeyboardInterrupt:
    print("🛑 Simulation manually stopped.")

finally:
    client.close()
