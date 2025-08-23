import pandas as pd

# import plotly.express as px
import streamlit as st


def stats(data: pd.DataFrame, title: str, description: bool = True):
    with st.expander(title, expanded=not description or data.empty):
        if data.empty:
            st.warning("No data")
            return

        st.write(data)
        if description:
            st.write("Data statistics:")
            st.write(data.describe())

            # data["smoothed"] = data["value"].rolling(window=4).mean()

            # fig = px.line(data, x="timestamp", y="value", markers=True)

            # st.plotly_chart(fig, use_container_width=True, key=title + "_normal")

            # fig = px.line(data, x="timestamp", y="smoothed", markers=True)

            # st.plotly_chart(fig, use_container_width=True, key=title + "_smoothed")


def data_analysis(data: pd.DataFrame, key="data_analysis"):
    with st.container(border=True, key=key + "container_1"):
        st.subheader("Data analysis")

        stats(data, "All", description=False)

        if not data.empty:
            for device, sensor in (
                data[["sensor_id", "sensor"]].drop_duplicates().values
            ):
                sensor_data = data[
                    (data["sensor_id"] == device) & (data["sensor"] == sensor)
                ]
                stats(sensor_data, f"{device}: {sensor}")
