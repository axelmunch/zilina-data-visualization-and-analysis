from typing import Any, TypedDict


class Measurement(TypedDict):
    name: str
    value: float


class DataPoint(TypedDict):
    measurements: list[Measurement]
    timestamp: Any


class Sensor(TypedDict):
    sensor_id: str
    sensor_type: str
    data: list[DataPoint]


class Device(TypedDict):
    device: str
    sensors: list[Sensor]


Data = Device
