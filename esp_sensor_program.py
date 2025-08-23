from time import sleep

from dht import DHT11
from machine import Pin

PIN_NUM = 23

# Sensor
dht_pin = Pin(PIN_NUM)
dht_sensor = DHT11(dht_pin)

started = False

while True:
    try:
        if not started:
            sleep(2)
            started = True
            continue

        dht_sensor.measure()

        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()

        print(f"Temperature: {temperature}")
        print(f"Humidity: {humidity}")

        # Putting data in the API structure
        data = [
            {
                "device": "ESP32",
                "sensors": [
                    {
                        "sensor_id": "DHT11",
                        "sensor_type": "temperature-humidity",
                        "data": [
                            {
                                "measurements": [
                                    {"name": "temperature", "value": temperature},
                                    {"name": "humidity", "value": humidity},
                                ]
                            }
                        ],
                    }
                ],
            }
        ]

        print(data)

        sleep(2)
    except Exception as e:
        print(e)
        break

print("Error. Exiting...")
