import streamlit as st

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="🛰️", layout="wide")

st.title("🛰️ ESP32 Multi-Sensor Dashboard")
st.markdown("""
Bienvenue sur le tableau de bord multi-capteurs ESP32 !
Utilisez le menu à gauche pour explorer les différents types de capteurs :
- Température 🌡️
- Pression 📉
- Distance / Ultrason 📏
- Jauge de contrainte 📊
- Accéléromètre 📡
""")
