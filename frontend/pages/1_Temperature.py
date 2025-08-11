import plotly.express as px
import streamlit as st
from utils import load_data

st.set_page_config(layout="wide")

st.title("🌡️ Temperature sensor")
df = load_data()

df_temp = df[df["sensor_type"].str.contains("temperature")]

if df_temp.empty:
    st.warning("No temperature data.")
else:
    st.plotly_chart(
        px.line(
            df_temp,
            x="timestamp",
            y="value",
            color="sensor_id",
            title="Température dans le temps",
        ),
        use_container_width=True,
    )
