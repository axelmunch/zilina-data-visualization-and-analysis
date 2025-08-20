import datetime as dt

import plotly.express as px
import streamlit as st
from data_selector import data_selector
from utils import get_data

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="📊", layout="wide")

st.title("ESP32 Sensor Dashboard")

with st.container(border=True):
    selected_sensors, selected_measurements = data_selector()

    print(selected_sensors, selected_measurements)
    data = get_data(
        sensors=selected_sensors,
        measurements=selected_measurements,
        start_time=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1000),
        end_time=dt.datetime.now(dt.timezone.utc),
    )
    print(data)

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
