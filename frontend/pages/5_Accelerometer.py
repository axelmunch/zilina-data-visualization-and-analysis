import streamlit as st
import plotly.express as px
from utils import load_data

st.set_page_config(layout="wide")

st.title("📡 Accelerometer Sensor (Axes x, y, z)")
df = load_data()

df_filtered = df["sensor_type"].isin(["x", "y", "z"])

if df[df_filtered].empty:
    st.warning("No accelerometer data available.")
else:
    fig = px.line(
        df[df_filtered],
        x="timestamp",
        y="value",
        color="sensor_type",
        line_group="sensor_id",
        title="Acceleration per Axis Over Time"
    )
    st.plotly_chart(fig, use_container_width=True)
