import plotly.express as px
import streamlit as st
from utils import load_data

st.set_page_config(layout="wide")

st.title("📊 Strain Gauge Sensor")
df = load_data()

df_filtered = df[df["sensor_type"] == "strain"]

if df_filtered.empty:
    st.warning("No strain data available.")
else:
    st.sidebar.markdown("### Smoothing Options")
    apply_smoothing = st.sidebar.checkbox("Apply smoothing (rolling mean)", value=True)
    resample_interval = st.sidebar.selectbox(
        "Resample interval", ["1s", "5s", "10s", "30s"], index=2
    )

    # Garder uniquement les colonnes utiles pour la moyenne
    df_resampled = (
        df_filtered[["timestamp", "sensor_id", "value"]]
        .set_index("timestamp")
        .groupby("sensor_id")
        .resample(resample_interval)["value"]
        .mean()
        .reset_index()
    )

    if apply_smoothing:
        df_resampled["value"] = df_resampled.groupby("sensor_id")["value"].transform(
            lambda x: x.rolling(window=5, min_periods=1).mean()
        )

    fig = px.line(
        df_resampled,
        x="timestamp",
        y="value",
        color="sensor_id",
        title="Strain over Time",
    )
    st.plotly_chart(fig, use_container_width=True)
