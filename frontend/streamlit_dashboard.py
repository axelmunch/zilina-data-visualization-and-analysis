"""
Streamlit Dashboard for ESP32 Multi-Sensor Data (CSV or InfluxDB)
Author: BRISSON Jordan, MUNCH Axel
Date: Summer 2025

Install requirements with:
    pip install streamlit pandas numpy plotly influxdb-client psycopg2-binary

Launch with:
    streamlit run streamlit_dashboard.py

The app can connect to **InfluxDB 2.x** (recommended) or fall back to a local CSV.
Place a `sensor_data.csv` next to this script with columns:
    timestamp,sensor_id,sensor_type,value,x,y

InfluxDB schema expected:
    • _measurement = "sensor_data"
    • Tags  : sensor_id, sensor_type
    • Fields: value (float)  x (float)  y (float)
    • _time : timestamp automatically set by InfluxDB

Bucket retention and query window are configurable in the sidebar.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

##############
# APP CONFIG #
##############

st.set_page_config(page_title="ESP32 Sensor Dashboard", layout="wide", page_icon="📊")

st.sidebar.title("📡 Data Source")

DATA_SOURCE: Literal["csv", "influxdb"] = st.sidebar.radio(
    "Choose backend", ("csv", "influxdb"), help="Where to load data from"
)

# ---------- CSV settings ----------
CSV_PATH = Path("data/sensor_data.csv")

# ---------- InfluxDB settings ----------
if DATA_SOURCE == "influxdb":
    st.sidebar.subheader("InfluxDB config")
    INFLUX_URL = st.sidebar.text_input("URL", "http://localhost:8086")
    INFLUX_TOKEN = st.sidebar.text_input("API token", value="", type="password")
    INFLUX_ORG = st.sidebar.text_input("Org", "esp32-org")
    INFLUX_BUCKET = st.sidebar.text_input("Bucket", "esp32")
    QUERY_WINDOW_HOURS = st.sidebar.number_input(
        "Look-back window (h)", min_value=1, max_value=720, value=24, step=1
    )

REFRESH_EVERY_SEC = st.sidebar.number_input(
    "Auto-refresh (s)", min_value=0, max_value=300, value=10, step=5
)

###############
# DATA LOADER #
###############


@st.cache_data(ttl=30)
def load_data(source: str) -> pd.DataFrame:
    """Return a dataframe with columns: timestamp, sensor_id, sensor_type, value, x, y"""
    if source == "csv":
        if CSV_PATH.exists():
            df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
        else:
            st.warning("CSV not found. Generating synthetic data…")
            df = _generate_synthetic()
    else:  # InfluxDB
        try:
            from influxdb_client import InfluxDBClient
        except ImportError:
            st.error(
                "Package `influxdb-client` not installed. Add it to your Dockerfile / requirements."
            )
            st.stop()

        if not INFLUX_TOKEN:
            st.error("Please provide your InfluxDB API token in the sidebar.")
            st.stop()

        client = InfluxDBClient(
            url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=60000
        )
        query_api = client.query_api()

        flux_query = f"""
        from(bucket: \"{INFLUX_BUCKET}\")
            |> range(start: -{QUERY_WINDOW_HOURS}h)
            |> filter(fn: (r) => r[\"_measurement\"] == \"sensor_data\")
            |> pivot(rowKey:[\"_time\"], columnKey:[\"_field\"], valueColumn:\"_value\")
            |> keep(columns: [\"_time\", \"sensor_id\", \"sensor_type\", \"value\", \"x\", \"y\"])
        """
        dfs = query_api.query_data_frame(flux_query)
        if isinstance(dfs, list):
            df = pd.concat(dfs, ignore_index=True)
        else:
            df = dfs
        df = df.rename(columns={"_time": "timestamp"})
        client.close()
    # Ensure proper dtypes
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
    df = df.sort_values("timestamp")
    return df


def _generate_synthetic(n: int = 10_000) -> pd.DataFrame:
    rng = pd.date_range(dt.datetime.now() - dt.timedelta(hours=1), periods=n, freq="S")
    sensor_types = [
        "temperature",
        "accelerometer",
        "strain_gauge",
        "pressure",
        "ultrasonic",
        "laser",
    ]
    data = {
        "timestamp": np.tile(rng, len(sensor_types)),
        "sensor_type": np.repeat(sensor_types, len(rng)),
        "sensor_id": np.repeat(np.arange(len(sensor_types)), len(rng)),
        "x": np.repeat(np.linspace(0, 1, len(sensor_types)), len(rng)),
        "y": np.repeat(np.linspace(0, 0.5, len(sensor_types)), len(rng)),
        "value": np.random.randn(len(sensor_types) * len(rng)),
    }
    return pd.DataFrame(data)


############
# MAIN APP #
############


def main():
    st.header("ESP32 Multi-Sensor Dashboard")
    df = load_data(DATA_SOURCE)

    # ---------- Sidebar filters ----------
    sensor_types = sorted(df["sensor_type"].unique())
    selected_types = st.sidebar.multiselect(
        "Sensor types", sensor_types, default=sensor_types
    )

    if df.empty:
        st.warning("No data available.")
        return

    min_time, max_time = df["timestamp"].min(), df["timestamp"].max()
    min_time, max_time = min_time.to_pydatetime(), max_time.to_pydatetime()

    start, end = st.sidebar.slider(
        "Time range",
        min_value=min_time,
        max_value=max_time,
        value=(min_time, max_time),
        format="YYYY-MM-DD HH:mm:ss",
    )

    filtered = df[
        (df["sensor_type"].isin(selected_types))
        & (df["timestamp"] >= start)
        & (df["timestamp"] <= end)
    ]

    # ---------- UI Tabs ----------
    tab1, tab2 = st.tabs(["📈 Time Series", "🌡️ Heatmap"])

    with tab1:
        st.subheader("Sensor Time Series")
        if filtered.empty:
            st.info("No data for selection.")
        else:
            fig = px.line(
                filtered,
                x="timestamp",
                y="value",
                color="sensor_type",
                line_group="sensor_id",
                hover_data=["sensor_id"],
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Spatial Heatmap (latest snapshot)")
        if {"x", "y"}.issubset(filtered.columns):
            latest_ts = filtered["timestamp"].max()
            latest = filtered[filtered["timestamp"] == latest_ts]
            if latest.empty:
                st.info("No spatial data in selection.")
            else:
                fig = px.density_heatmap(
                    latest,
                    x="x",
                    y="y",
                    z="value",
                    histfunc="avg",
                    nbinsx=20,
                    nbinsy=10,
                    color_continuous_scale="thermal",
                )
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No spatial coordinates available.")

    # ---------- Auto‑refresh ----------
    if REFRESH_EVERY_SEC > 0:
        # TODO
        # st.experimental_rerun()
        # st.rerun()
        pass
