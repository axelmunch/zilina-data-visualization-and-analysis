import streamlit as st
import plotly.express as px
from utils import load_data

st.set_page_config(layout="wide")

st.title("📉 Pressure Sensor")
df = load_data()

df_filtered = df["sensor_type"].str.contains("pressure", case=False)

if df[df_filtered].empty:
    st.warning("No pressure data available.")
else:
    fig = px.line(
        df[df_filtered],
        x="timestamp",
        y="value",
        color="sensor_id",
        title="Pressure over Time"
    )
    st.plotly_chart(fig, use_container_width=True)
    
