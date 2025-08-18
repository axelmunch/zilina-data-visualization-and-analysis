from typing import Any, List, TypedDict


class Measurement(TypedDict):
    name: str
    value: float


class DataPoint(TypedDict):
    measurements: List[Measurement]
    timestamp: Any


class Sensor(TypedDict):
    sensor_id: str
    sensor_type: str
    data: List[DataPoint]


class Device(TypedDict):
    device: str
    sensors: List[Sensor]


Data = Device
