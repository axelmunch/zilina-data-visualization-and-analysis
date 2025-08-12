import streamlit as st
from data_selector import data_selector

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="📊", layout="wide")

st.title("ESP32 Sensor Dashboard")

data_selector()
