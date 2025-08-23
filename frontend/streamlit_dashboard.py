import datetime as dt

import plotly.express as px
import streamlit as st
from data_analysis import data_analysis
from data_selector import data_selector
from utils import get_data

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="📊", layout="wide")

st.title("ESP32 Sensor Dashboard")

with st.container(border=True):
    st.sidebar.subheader("Settings")

    data_source = st.sidebar.radio(
        "Data source",
        ["Database", "CSV"],
        captions=[
            "InfluxDB",
            "CSV import",
        ],
    )

    if data_source == "CSV":
        csv_content = st.sidebar.text_area("CSV data")

    selected_sensors, selected_measurements = data_selector()

    data = get_data(
        sensors=selected_sensors,
        measurements=selected_measurements,
        start_time=dt.datetime.fromtimestamp(0),
        end_time=dt.datetime.now(dt.timezone.utc),
    )

    fig = px.line(
        data,
        x="timestamp",
        y="value",
        color="sensor_type",
        line_group="sensor",
        hover_data=[
            "timestamp",
            "sensor_id",
            "sensor",
            "_measurement",
            "sensor_type",
            "value",
        ],
        markers=True,
    )

    st.plotly_chart(fig, use_container_width=True)

    data_analysis(data)
