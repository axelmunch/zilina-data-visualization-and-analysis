"""
Streamlit Dashboard for ESP32 Multi-Sensor Data (CSV or InfluxDB)
Author: BRISSON Jordan, MUNCH Axel
Date: Summer 2025

Install requirements with:
    pip install streamlit pandas numpy plotly influxdb-client psycopg2-binary

Launch with:
    streamlit run streamlit_dashboard.py
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

DATA_SOURCE: Literal["influxdb"] = "influxdb"

# ---------- CSV settings ----------
CSV_PATH = Path("data/sensor_data.csv")

# ---------- InfluxDB settings ----------
if DATA_SOURCE == "influxdb":
    st.sidebar.subheader("InfluxDB config")
    INFLUX_URL = "http://influxdb:8086"
    INFLUX_TOKEN = "klQGaUK53OtG1Bzk1Ezon9N-_7fM9TSSMHOsivQoFthzGgH_53E1GhOiFoCNq8Y92y64BKx0gtML12N43fEyoA=="
    INFLUX_ORG = "my-org"
    INFLUX_BUCKET = "sensor_data"
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
        import "influxdata/influxdb/schema"

        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -{QUERY_WINDOW_HOURS}h)
          |> filter(fn: (r) => r._measurement =~ /.*/)
          |> schema.fieldsAsCols()
          |> keep(columns: ["_time", "_measurement", "device", "sensor", "x", "y", "z", "temperature_c", "distance_cm", "distance_mm", "pressure_pa", "strain"])
        """

        dfs = query_api.query_data_frame(flux_query)
        if isinstance(dfs, list):
            df = pd.concat(dfs, ignore_index=True)
        else:
            df = dfs

        df = df.rename(columns={"_time": "timestamp", "device": "sensor_id"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)

        value_columns = ["x", "y", "z", "temperature_c", "distance_cm", "distance_mm", "pressure_pa", "strain"]
        df = df.melt(
            id_vars=["timestamp", "sensor_id", "sensor", "_measurement"],
            value_vars=[col for col in value_columns if col in df.columns],
            var_name="sensor_type",
            value_name="value",
        )
        df = df.dropna(subset=["value"])
        df = df.sort_values("timestamp")
        client.close()

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

    if df.empty:
        st.warning("No data available.")
        return

    # ---------- Sidebar filters ----------
    sensor_types = sorted(df["sensor_type"].unique())
    selected_types = st.sidebar.multiselect(
        "Sensor types", sensor_types, default=sensor_types
    )

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
                hover_data=["sensor_id", "_measurement", "sensor"],
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Spatial Heatmap (latest snapshot)")
        if {"x", "y"}.issubset(df.columns):
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
        import time
        time.sleep(REFRESH_EVERY_SEC)
        st.rerun()


if __name__ == "__main__":
    main()
