import streamlit as st

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="📊", layout="wide")

st.title("📊 ESP32 Sensor Dashboard")
st.markdown("""
This dashboard displays data from various sensors (connected to ESP32 devices). Explore the data using the sidebar menu:
- Temperature
- Pressure
- Distance ultrasonics
- Strain gauge
- Accelerometer
""")
