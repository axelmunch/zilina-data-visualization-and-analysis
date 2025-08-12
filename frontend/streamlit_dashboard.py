import plotly.express as px
import streamlit as st
from data_selector import data_selector
from utils import load_data

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="📊", layout="wide")

st.title("ESP32 Sensor Dashboard")

with st.container(border=True):
    _, selected_measurements = data_selector()

    if len(selected_measurements) > 0:
        df = load_data()

        df_temp = df[df["sensor_type"].str.contains(selected_measurements[0])]

        if df_temp.empty:
            st.warning("No data.")
        else:
            st.plotly_chart(
                px.line(
                    df_temp,
                    x="timestamp",
                    y="value",
                    color="sensor_id",
                    title="Variation",
                ),
                use_container_width=True,
            )
