import streamlit as st
from utils import get_data, get_measurements, get_sensors


def data_selector():
    selected_sensors = []
    selected_measurements = []

    selection_type = st.radio(
        "Data filter type",
        ["Any", "Sensor", "Measurement"],
        captions=[
            "Select any values",
            "Filter measurements by sensor",
            "Filter sensors by measurement",
        ],
        index=1,
    )

    match selection_type:
        case "Any":
            selected_sensors, selected_measurements = get_sensors(), get_measurements()

            sensors = get_sensors()
            selected_sensors = st.multiselect("Sensors", sensors, key="1")
            measurements = get_measurements()
            selected_measurements = st.multiselect(
                "Measurements", measurements, key="2"
            )

        case "Sensor":
            sensors = get_sensors()
            selected_sensors = st.multiselect("Sensors", sensors, key="3")
            measurements = get_measurements(selected_sensors)
            selected_measurements = st.multiselect(
                "Measurements", measurements, key="4"
            )
        case "Measurement":
            measurements = get_measurements()
            selected_measurements = st.multiselect(
                "Measurements", measurements, key="5"
            )
            sensors = get_sensors(selected_measurements)
            selected_sensors = st.multiselect("Sensors", sensors, key="6")

    return selected_sensors, selected_measurements
