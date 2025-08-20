import datetime as dt

# (Optionnel) éviter les warnings pandas/flux "MissingPivotFunction"
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from influxdb_client import InfluxDBClient
from influxdb_client.client.warnings import MissingPivotFunction

warnings.simplefilter("ignore", MissingPivotFunction)

CSV_PATH = Path("data/sensor_data.csv")
INFLUX_URL = "http://influxdb:8086"  # en Docker Compose -> "http://influxdb:8086"
INFLUX_TOKEN = "klQGaUK53OtG1Bzk1Ezon9N-_7fM9TSSMHOsivQoFthzGgH_53E1GhOiFoCNq8Y92y64BKx0gtML12N43fEyoA=="
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "sensor_data"


# ---------- Helpers ----------
def _normalize_list(x):
    return [str(v) for v in (x or []) if v is not None]


def _or_eq(column: str, values: list[str]) -> str:
    esc = [str(v).replace('"', r"\"") for v in values]
    return " or ".join([f'r.{column} == "{v}"' for v in esc])


def _time_clause_from_bounds(start: dt.datetime, end: dt.datetime) -> str:
    def to_rfc3339(t: dt.datetime) -> str:
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        return t.isoformat()

    return f'range(start: time(v: "{to_rfc3339(start)}"), stop: time(v: "{to_rfc3339(end)}"))'


def get_columns() -> list[str]:
    """
    Liste dynamique de tous les 'field keys' du bucket (aucune liste en dur).
    Utilisé par load_data ; get_data fait aussi une détection sur dtypes côté pandas.
    """
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        flux = f'''
import "influxdata/influxdb/schema"
schema.fieldKeys(bucket: "{INFLUX_BUCKET}")
'''
        df = client.query_api().query_data_frame(flux)
        if isinstance(df, list) and len(df) > 0:
            df = pd.concat(df, ignore_index=True)
        if not isinstance(df, pd.DataFrame) or df.empty:
            return []
        # schema.fieldKeys renvoie généralement le nom dans _value
        for col in ["_value", "fieldKey", "field"]:
            if col in df.columns:
                return sorted(df[col].dropna().astype(str).unique().tolist())
        # fallback: toutes les colonnes textuelles
        return sorted(
            df.select_dtypes(include=["object"])
            .stack()
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    finally:
        client.close()


@st.cache_data(ttl=30)
def load_data(hours=24) -> pd.DataFrame:
    """
    Version dynamique : on n'écrit PLUS la liste de colonnes dans le Flux.
    On détecte ensuite côté pandas les colonnes valeurs qui existent.
    """
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    flux_query = f'''
    import "influxdata/influxdb/schema"
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement =~ /.*/ )
      |> schema.fieldsAsCols()
    '''

    df = query_api.query_data_frame(flux_query)
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    if not isinstance(df, pd.DataFrame) or df.empty:
        client.close()
        return pd.DataFrame(
            columns=[
                "timestamp",
                "sensor_id",
                "sensor",
                "_measurement",
                "sensor_type",
                "value",
            ]
        )

    df = df.rename(columns={"_time": "timestamp", "device": "sensor_id"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
    # si device absent sur certains points, retomber sur 'sensor'
    if "sensor_id" in df.columns and "sensor" in df.columns:
        df["sensor_id"] = df["sensor_id"].fillna(df["sensor"])

    # Colonnes valeurs détectées dynamiquement (numériques, non-méta)
    meta_cols = {
        "result",
        "table",
        "_start",
        "_stop",
        "timestamp",
        "_measurement",
        "sensor",
        "sensor_id",
        "device",
    }
    cols = [c for c in df.columns if c not in meta_cols and not c.startswith("_")]
    value_columns = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

    if not value_columns:
        client.close()
        return pd.DataFrame(
            columns=[
                "timestamp",
                "sensor_id",
                "sensor",
                "_measurement",
                "sensor_type",
                "value",
            ]
        )

    df = df.melt(
        id_vars=["timestamp", "sensor_id", "sensor", "_measurement"],
        value_vars=value_columns,
        var_name="sensor_type",
        value_name="value",
    )
    df = df.dropna(subset=["value"]).sort_values("timestamp").reset_index(drop=True)
    client.close()
    return df


@st.cache_data(ttl=30)
def get_sensors(filter_measurements: list[str] = []) -> list[str]:
    """
    Renvoie la liste des capteurs (union des tags 'sensor' et 'device').
    Si filter_measurements est fourni, on ne garde que ceux qui ont des points
    dans au moins un des measurements donnés (fenêtre glissante = 24h).
    """
    filter_measurements = _normalize_list(filter_measurements)
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        meas_filter = (
            f"  |> filter(fn: (r) => {_or_eq('_measurement', filter_measurements)})\n"
            if filter_measurements
            else ""
        )
        flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -24h)
{meas_filter}  |> keep(columns: ["sensor", "device"])
'''
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


@st.cache_data(ttl=30)
def get_measurements(filter_sensors: list[str] = []) -> list[str]:
    """
    Renvoie la liste des _measurement distincts.
    - Si aucun filtre capteurs -> utilise schema.measurements (plus fiable/rapide).
    - Sinon -> filtre sur tags sensor OU device puis distinct(_measurement).
    Fenêtre glissante de 24h pour le cas filtré.
    """
    filter_sensors = _normalize_list(filter_sensors)
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        if not filter_sensors:
            flux = f'''
import "influxdata/influxdb/schema"
schema.measurements(bucket: "{INFLUX_BUCKET}")
'''
            df = client.query_api().query_data_frame(flux)
            if isinstance(df, list) and len(df) > 0:
                df = pd.concat(df, ignore_index=True)
            if not isinstance(df, pd.DataFrame) or df.empty:
                return []
            for col in ["_value", "_measurement", "distinct"]:
                if col in df.columns:
                    return sorted(df[col].dropna().astype(str).unique().tolist())
            return []

        f1 = _or_eq("sensor", filter_sensors)
        f2 = _or_eq("device", filter_sensors)
        flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => ({f1}) or ({f2}))
  |> keep(columns: ["_measurement"])
  |> group()
  |> distinct(column: "_measurement")
'''
        df = client.query_api().query_data_frame(flux)
        if isinstance(df, list) and len(df) > 0:
            df = pd.concat(df, ignore_index=True)
        if not isinstance(df, pd.DataFrame) or df.empty:
            return []
        for col in ["_measurement", "_value", "distinct"]:
            if col in df.columns:
                return sorted(df[col].dropna().astype(str).unique().tolist())
        return []
    finally:
        client.close()


@st.cache_data(ttl=30)
def get_data(
    sensors: list[str],
    measurements: list[str],
    start_time: dt.datetime,
    end_time: dt.datetime,
) -> pd.DataFrame:
    """
    Récupère les données selon:
      - sensors: liste de capteurs (tags 'sensor' OU 'device'); si vide -> tous
      - measurements: liste de _measurement ; si vide -> tous
      - start_time / end_time: bornes absolues (naïf = UTC)
    Retourne un DataFrame *long* (timestamp, sensor_id, sensor, _measurement, sensor_type, value).
    """
    sensors = _normalize_list(sensors)
    measurements = _normalize_list(measurements)

    # Filtres Flux
    sensors_filter = None
    if sensors:
        f1 = _or_eq("sensor", sensors)
        f2 = _or_eq("device", sensors)
        sensors_filter = f"({f1}) or ({f2})"

    meas_filter = _or_eq("_measurement", measurements) if measurements else None

    filter_block = ""
    if sensors_filter:
        filter_block += f"  |> filter(fn: (r) => {sensors_filter})\n"
    if meas_filter:
        filter_block += f"  |> filter(fn: (r) => {meas_filter})\n"

    flux = f'''
import "influxdata/influxdb/schema"

from(bucket: "{INFLUX_BUCKET}")
  |> {_time_clause_from_bounds(start_time, end_time)}
  |> filter(fn: (r) => r._measurement =~ /.*/ )
{filter_block}  |> schema.fieldsAsCols()
'''
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    try:
        df = client.query_api().query_data_frame(flux)
        if isinstance(df, list) and len(df) > 0:
            df = pd.concat(df, ignore_index=True)

        if not isinstance(df, pd.DataFrame) or df.empty:
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "sensor_id",
                    "sensor",
                    "_measurement",
                    "sensor_type",
                    "value",
                ]
            )

        # Harmonisation
        df = df.rename(columns={"_time": "timestamp", "device": "sensor_id"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(None)
        if "sensor_id" in df.columns and "sensor" in df.columns:
            df["sensor_id"] = df["sensor_id"].fillna(df["sensor"])

        # Détection dynamique des colonnes de valeur (numériques, non-méta)
        meta_cols = {
            "result",
            "table",
            "_start",
            "_stop",
            "timestamp",
            "_measurement",
            "sensor",
            "sensor_id",
            "device",
        }
        candidates = [
            c for c in df.columns if c not in meta_cols and not c.startswith("_")
        ]
        value_cols = [c for c in candidates if pd.api.types.is_numeric_dtype(df[c])]

        if not value_cols:
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "sensor_id",
                    "sensor",
                    "_measurement",
                    "sensor_type",
                    "value",
                ]
            )

        df_long = df.melt(
            id_vars=["timestamp", "sensor_id", "sensor", "_measurement"],
            value_vars=value_cols,
            var_name="sensor_type",
            value_name="value",
        ).dropna(subset=["value"])

        return df_long.sort_values("timestamp").reset_index(drop=True)
    finally:
        client.close()
