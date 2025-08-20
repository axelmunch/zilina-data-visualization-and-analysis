import streamlit as st
from utils import get_measurements, get_sensors


def data_selector(key="data_selector") -> tuple[list[str], list[str]]:
    """
    Component for selecting sensors and measurements to visualize data.
    Returns:
        tuple: Selected sensors and measurements.
    """

    selected_sensors = []
    selected_measurements = []

    with st.container(border=True, key=key + "container_1"):
        st.text("Select sensors and measurements to visualize data.")

        selection_type = st.radio(
            "Data filter type",
            ["Any", "Sensor", "Measurement"],
            captions=[
                "Select any values",
                "Filter measurements by sensor/device",
                "Filter sensors by measurement",
            ],
            index=1,
            key=key + "radio_1",
        )

        match selection_type:
            case "Any":
                selected_sensors, selected_measurements = (
                    get_sensors(),
                    get_measurements(),
                )

                sensors = get_sensors()
                selected_sensors = st.multiselect(
                    "Sensors", sensors, key=key + "multiselect_1"
                )
                measurements = get_measurements()
                selected_measurements = st.multiselect(
                    "Measurements", measurements, key=key + "multiselect_2"
                )

            case "Sensor":
                sensors = get_sensors()
                selected_sensors = st.multiselect(
                    "Sensors", sensors, key=key + "multiselect_3"
                )
                measurements = get_measurements(selected_sensors)
                selected_measurements = st.multiselect(
                    "Measurements", measurements, key=key + "multiselect_4"
                )

            case "Measurement":
                measurements = get_measurements()
                selected_measurements = st.multiselect(
                    "Measurements", measurements, key=key + "multiselect_5"
                )

                sensors = get_sensors(selected_measurements)
                selected_sensors = st.multiselect(
                    "Sensors", sensors, key=key + "multiselect_6"
                )

    print(selected_sensors, selected_measurements)
    return selected_sensors, selected_measurements
