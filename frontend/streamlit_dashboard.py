import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st
from data_analysis import data_analysis
from data_selector import data_selector
from utils import get_data

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="📊", layout="wide")

st.title("ESP32 Sensor Dashboard")

with st.container(border=True):
    st.sidebar.subheader("Settings")

    data = None

    data_source = st.sidebar.radio(
        "Data source",
        ["Database", "CSV"],
        captions=[
            "InfluxDB",
            "CSV import",
        ],
    )

    if data_source == "CSV":
        uploaded_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])
        if uploaded_file is not None:
            data = pd.read_csv(uploaded_file)
            st.sidebar.success("File uploaded successfully")
            st.badge("Using imported data", icon=":material/check:", color="blue")
        else:
            st.sidebar.warning("Please upload a CSV file")
            st.stop()

    st.sidebar.divider()

    filters_enabled = st.sidebar.checkbox("Enable filters", value=True)
    if filters_enabled:
        st.sidebar.text("Rolling mean")
        st.sidebar.text("Rolling mean window")
        st.sidebar.divider()
        st.sidebar.text("Low-pass filter")
        st.sidebar.divider()
        st.sidebar.text("High-pass filter")

    selected_sensors, selected_measurements = data_selector(data=data)

    selected_data = get_data(
        data=data,
        sensors=selected_sensors,
        measurements=selected_measurements,
        start_time=dt.datetime.fromtimestamp(0),
        end_time=dt.datetime.now(dt.timezone.utc),
    )

    fig = px.line(
        selected_data,
        x="timestamp",
        y="value",
        color="sensor_type",
        line_group="sensor",
        hover_data=[
            "timestamp",
            "sensor_id",
            "sensor",
            "measurement",
            "sensor_type",
            "value",
        ],
        markers=True,
    )

    st.plotly_chart(fig, use_container_width=True)

    data_analysis(selected_data)
