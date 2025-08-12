import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from influxdb_client import InfluxDBClient

CSV_PATH = Path("data/sensor_data.csv")
INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "klQGaUK53OtG1Bzk1Ezon9N-_7fM9TSSMHOsivQoFthzGgH_53E1GhOiFoCNq8Y92y64BKx0gtML12N43fEyoA=="
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "sensor_data"


# -----------------------------
# Helpers
# -----------------------------
def _normalize_list(x):
    """None -> None ; list/tuple/set -> list[str] ; autre -> [str(x)]"""
    if x is None:
        return None
    if isinstance(x, (list, tuple, set)):
        return [str(v) for v in x if v is not None]
    return [str(x)]


def _or_eq(column: str, values: list[str]) -> str:
    """Construit une clause OR Flux: r.column == "a" or r.column == "b" ..."""
    esc = [str(v).replace('"', r"\"") for v in values]
    return " or ".join([f'r.{column} == "{v}"' for v in esc])


def _time_clause(hours: int | None, start: dt.datetime | None, end: dt.datetime | None) -> str:
    """Construit la clause range(...) Flux en relatif (hours) ou absolu (start/end)."""
    if start:
        start_iso = (start if start.tzinfo else start.replace(tzinfo=dt.timezone.utc)).isoformat()
        if end is None:
            return f'range(start: time(v: "{start_iso}"), stop: now())'
        end_iso = (end if end.tzinfo else end.replace(tzinfo=dt.timezone.utc)).isoformat()
        return f'range(start: time(v: "{start_iso}"), stop: time(v: "{end_iso}"))'
    hrs = int(hours if hours is not None else 24)
    return f"range(start: -{hrs}h)"


# -----------------------------
# 1) get_sensors
# -----------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_sensors(filter_measurements: list[str] | None = None, hours: int = 24) -> list[str]:
    """
    Renvoie la liste des capteurs disponibles (union des tags 'sensor' et 'device').
    Si filter_measurements est fourni, ne garder que les capteurs ayant au moins un point
    dans l'un des measurements spécifiés.
    """
    filter_measurements = _normalize_list(filter_measurements)
    meas_filter = ""
    if filter_measurements:
        meas_filter = f'  |> filter(fn: (r) => {_or_eq("_measurement", filter_measurements)})\n'

    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> {_time_clause(hours, None, None)}
{meas_filter}  |> keep(columns: ["sensor", "device"])
'''

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        df = client.query_api().query_data_frame(flux)
        if isinstance(df, list) and len(df) > 0:
            df = pd.concat(df, ignore_index=True)
        sensors = set()
        if isinstance(df, pd.DataFrame) and not df.empty:
            if "sensor" in df.columns:
                sensors.update(df["sensor"].dropna().astype(str).tolist())
            if "device" in df.columns:
                sensors.update(df["device"].dropna().astype(str).tolist())
        return sorted(sensors)
    finally:
        client.close()


# -----------------------------
# 2) get_measurements
# -----------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_measurements(filter_sensors: list[str] | None = None, hours: int = 24) -> list[str]:
    """
    Renvoie la liste des _measurement distincts.
    - Sans filtre capteurs -> utilise schema.measurements (plus fiable/rapide).
    - Avec filtre capteurs -> from |> range |> filter(sensor/device) |> keep |> group |> distinct
      puis extraction robuste (colonne peut s'appeler _measurement, _value, distinct ...).
    """
    filter_sensors = _normalize_list(filter_sensors)
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        if not filter_sensors:
            # Chemin rapide/fiable
            flux = f'''
import "influxdata/influxdb/schema"
schema.measurements(bucket: "{INFLUX_BUCKET}")
'''
            df = client.query_api().query_data_frame(flux)
            if isinstance(df, list) and len(df) > 0:
                df = pd.concat(df, ignore_index=True)
            if isinstance(df, pd.DataFrame) and not df.empty:
                # schema.measurements renvoie en général dans _value
                for col in ["_value", "_measurement", "distinct"]:
                    if col in df.columns:
                        return sorted(df[col].dropna().astype(str).unique().tolist())
            return []

        # Avec filtre capteurs
        f1 = _or_eq("sensor", filter_sensors)
        f2 = _or_eq("device", filter_sensors)
        flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> {_time_clause(hours, None, None)}
  |> filter(fn: (r) => ({f1}) or ({f2}))
  |> keep(columns: ["_measurement"])
  |> group()
  |> distinct(column: "_measurement")
'''
        df = client.query_api().query_data_frame(flux)
        if isinstance(df, list) and len(df) > 0:
            df = pd.concat(df, ignore_index=True)
        if isinstance(df, pd.DataFrame) and not df.empty:
            # Extraire quel que soit le nom de colonne retourné
            for col in ["_measurement", "_value", "distinct"]:
                if col in df.columns:
                    return sorted(df[col].dropna().astype(str).unique().tolist())
        return []
    finally:
        client.close()



# -----------------------------
# 3) get_data : version filtrable (comme load_data + filtres)
# -----------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_data(
    hours: int | None = 24,
    start: dt.datetime | None = None,
    end: dt.datetime | None = None,
    filter_sensors: list[str] | None = None,
    filter_measurements: list[str] | None = None,
    filter_sensor_types: list[str] | None = None,
    value_min: float | None = None,
    value_max: float | None = None,
) -> pd.DataFrame:
    """
    Récupère des données InfluxDB et renvoie un DataFrame *long* (melt) avec :
      timestamp, sensor_id, sensor, _measurement, sensor_type, value

    Filtres :
      - hours OU (start/end) pour la période
      - filter_sensors : liste de capteurs (match sur tags 'sensor' ou 'device')
      - filter_measurements : liste de _measurement
      - filter_sensor_types : sous-ensemble des colonnes numériques (x, y, z, temperature_c, ...)
      - value_min / value_max : bornes sur value (après melt)
    """
    # Normalisation
    filter_sensors = _normalize_list(filter_sensors)
    filter_measurements = _normalize_list(filter_measurements)
    filter_sensor_types = _normalize_list(filter_sensor_types)

    # Filtres Flux
    meas_filter = _or_eq("_measurement", filter_measurements) if filter_measurements else None
    sensors_filter = None
    if filter_sensors:
        f1 = _or_eq("sensor", filter_sensors)
        f2 = _or_eq("device", filter_sensors)
        sensors_filter = f"({f1}) or ({f2})"

    filter_block = ""
    if meas_filter:
        filter_block += f"  |> filter(fn: (r) => {meas_filter})\n"
    if sensors_filter:
        filter_block += f"  |> filter(fn: (r) => {sensors_filter})\n"

    # Colonnes numériques possibles (doivent exister côté Influx)
    value_columns_all = ["x", "y", "z", "temperature_c", "distance_cm", "distance_mm", "pressure_pa", "strain"]

    # Construire keep(columns: [...]) avec des double quotes (sinon parse error Flux)
    keep_cols_py = ["_time", "_measurement", "device", "sensor"] + value_columns_all
    keep_cols_flux = ", ".join(f'"{c}"' for c in keep_cols_py)

    flux = f'''
import "influxdata/influxdb/schema"

from(bucket: "{INFLUX_BUCKET}")
  |> {_time_clause(hours, start, end)}
  |> filter(fn: (r) => r._measurement =~ /.*/ )
{filter_block}  |> schema.fieldsAsCols()
  |> keep(columns: [{keep_cols_flux}])
'''

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        df = client.query_api().query_data_frame(flux)
        if isinstance(df, list) and len(df) > 0:
            df = pd.concat(df, ignore_index=True)

        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.DataFrame(columns=["timestamp", "sensor_id", "sensor", "_measurement", "sensor_type", "value"])

        # Harmonisation
        df = df.rename(columns={"_time": "timestamp", "device": "sensor_id"})
        df["sensor_id"] = df["sensor_id"].fillna(df.get("sensor"))

        # Colonnes de valeur effectivement présentes
        existing_value_cols = [c for c in value_columns_all if c in df.columns]

        # Filtre par types de valeurs si demandé
        if filter_sensor_types:
            existing_value_cols = [c for c in existing_value_cols if c in set(filter_sensor_types)]
            if not existing_value_cols:
                return pd.DataFrame(columns=["timestamp", "sensor_id", "sensor", "_measurement", "sensor_type", "value"])

        # Passage au format long
        df_long = df.melt(
            id_vars=["timestamp", "sensor_id", "sensor", "_measurement"],
            value_vars=existing_value_cols,
            var_name="sensor_type",
            value_name="value",
        ).dropna(subset=["value"])

        # Bornes éventuelles
        if value_min is not None:
            df_long = df_long[df_long["value"] >= float(value_min)]
        if value_max is not None:
            df_long = df_long[df_long["value"] <= float(value_max)]

        return df_long.sort_values("timestamp").reset_index(drop=True)
    finally:
        client.close()

# -----------------------------
# 4) Chargeur simple (version de base)
# -----------------------------
@st.cache_data(ttl=30, show_spinner=False)
def load_data(hours=24) -> pd.DataFrame:
    """
    Version simple : fenêtre relative (hours), pas de filtres avancés.
    Retourne le même format long que get_data.
    """
    flux_query = f'''
    import "influxdata/influxdb/schema"
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement =~ /.*/ )
      |> schema.fieldsAsCols()
      |> keep(columns: ["_time", "_measurement", "device", "sensor",
                        "x", "y", "z", "temperature_c", "distance_cm", "distance_mm", "pressure_pa", "strain"])
    '''

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        query_api = client.query_api()
        df = query_api.query_data_frame(flux_query)
        if isinstance(df, list):
            df = pd.concat(df, ignore_index=True)

        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.DataFrame(columns=["timestamp", "sensor_id", "sensor", "_measurement", "sensor_type", "value"])

        df = df.rename(columns={"_time": "timestamp", "device": "sensor_id"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)

        value_columns = ["x", "y", "z", "temperature_c", "distance_cm", "distance_mm", "pressure_pa", "strain"]
        df = df.melt(
            id_vars=["timestamp", "sensor_id", "sensor", "_measurement"],
            value_vars=[c for c in value_columns if c in df.columns],
            var_name="sensor_type",
            value_name="value",
        )
        df = df.dropna(subset=["value"]).sort_values("timestamp").reset_index(drop=True)
        return df
    finally:
        client.close()
