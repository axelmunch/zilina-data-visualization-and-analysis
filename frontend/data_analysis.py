import pandas as pd
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
