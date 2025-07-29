import streamlit as st
import plotly.express as px
from utils import load_data

st.set_page_config(layout="wide")

st.title("📏 Distance Sensor (Ultrasonic / Laser)")
df = load_data()

df_filtered = df["sensor_type"].str.contains("distance", case=False)

if df[df_filtered].empty:
    st.warning("No distance data available.")
else:
    fig = px.line(
        df[df_filtered],
        x="timestamp",
        y="value",
        color="sensor_id",
        title="Distance over Time"
    )
    st.plotly_chart(fig, use_container_width=True)
