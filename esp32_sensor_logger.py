"""
ESP32 + DHT11 Sensor Wi-Fi Data Logger

This program reads temperature and humidity values from a DHT11 sensor and transmits the data to an API over Wi-Fi.

Configuration:
- SENSOR_PIN_NUM: GPIO pin number where the DHT11 sensor is connected.
- API_ADDRESS / API_PORT: Target server
- IS_ACCESS_POINT: Switch between AP mode and STA mode.
- RESET_WIFI: Option to disable/re-enable Wi-Fi before connecting.
- WIFI_SSID / WIFI_PASSWORD: Network credentials for STA mode.
"""

from time import sleep

import requests
from dht import DHT11
from machine import Pin
from network import AP_IF, STA_IF, WLAN

# Sensor PIN
SENSOR_PIN_NUM: int = 23

# API
API_ADDRESS: str = ""
API_PORT: int = 5000

assert len(API_ADDRESS) > 0, "API address is empty"
API_URL: str = f"http://{API_ADDRESS}:{API_PORT}"

# Create access point or connect to existing network
IS_ACCESS_POINT: bool = False

# Disables and re-enables the Wi-Fi connection. By default, Wi-Fi remains active to prevent long reloads and disconnections.
RESET_WIFI: bool = True

WIFI_SSID: str = ""
WIFI_PASSWORD: str = ""

assert len(WIFI_SSID) > 0, "Wi-Fi name is empty"

if RESET_WIFI:
    lan = WLAN(STA_IF)
    lan.active(False)
    lan = WLAN(AP_IF)
    lan.active(False)

lan = None

if IS_ACCESS_POINT:
    lan = WLAN(AP_IF)
    if not lan.active():
        print("Enabling Wi-Fi (access point)...")
        lan.active(True)

    lan.config(ssid=WIFI_SSID, password=WIFI_PASSWORD, authmode=3)
else:
    lan = WLAN(STA_IF)

    if not lan.active():
        print("Enabling Wi-Fi (connection)...")
        lan.active(True)

        lan.connect(WIFI_SSID, WIFI_PASSWORD)

        while not lan.isconnected():
            print("Connection status:", lan.status())
            sleep(1)

ip = lan.ifconfig()[0]
print(f"Connected to network {WIFI_SSID}\nIP address: {ip}")

# Sensor
dht_pin = Pin(SENSOR_PIN_NUM)
dht_sensor = DHT11(dht_pin)

started: bool = False

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

        # Send data
        response = requests.post(API_URL, json=data)
        if response.status_code != 200:
            raise Exception(
                f"API request failed, status: {response.status_code} ({response.text})"
            )

        # print(data)

        sleep(4)
    except Exception as e:
        print(e)
        # break

print("Error. Exiting...")
