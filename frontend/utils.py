import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from influxdb_client import InfluxDBClient

CSV_PATH = Path("data/sensor_data.csv")
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "klQGaUK53OtG1Bzk1Ezon9N-_7fM9TSSMHOsivQoFthzGgH_53E1GhOiFoCNq8Y92y64BKx0gtML12N43fEyoA=="
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "sensor_data"


def get_columns():
    return [
        "x",
        "y",
        "z",
        "temperature_c",
        "distance_cm",
        "distance_mm",
        "pressure_pa",
        "strain",
    ]


@st.cache_data(ttl=30)
def load_data(hours=24) -> pd.DataFrame:
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    flux_query = f'''
    import "influxdata/influxdb/schema"
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement =~ /.*/ )
      |> schema.fieldsAsCols()
      |> keep(columns: ["_time", "_measurement", "device", "sensor", "x", "y", "z", "temperature_c", "distance_cm", "distance_mm", "pressure_pa", "strain"])
    '''

    df = query_api.query_data_frame(flux_query)
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    df = df.rename(columns={"_time": "timestamp", "device": "sensor_id"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)

    value_columns = get_columns()
    df = df.melt(
        id_vars=["timestamp", "sensor_id", "sensor", "_measurement"],
        value_vars=[c for c in value_columns if c in df.columns],
        var_name="sensor_type",
        value_name="value",
    )
    df = df.dropna(subset=["value"])
    df = df.sort_values("timestamp")
    client.close()
    return df


@st.cache_data(ttl=30)
def get_sensors(filter_measurements: list[str] = []) -> list[str]:
    # TODO
    # Return all on empty list
    return []


@st.cache_data(ttl=30)
def get_measurements(filter_sensors: list[str] = []) -> list[str]:
    # TODO
    # Return all on empty list
    return []


@st.cache_data(ttl=30)
def get_data(
    sensors: list[str],
    measurements: list[str],
    start_time: dt.datetime,
    end_time: dt.datetime,
) -> pd.DataFrame:
    # TODO
    return pd.DataFrame()
