import datetime as dt
import math

import pandas as pd
import plotly.express as px
import streamlit as st
from data_analysis import data_analysis
from data_selector import data_selector
from utils import get_data

st.set_page_config(page_title="ESP32 Multi-Dashboard", page_icon="📊", layout="wide")
st.title("ESP32 Sensor Dashboard")

# Optional: SciPy for a true IIR Butterworth (otherwise fallback to rolling mean)
try:
    from scipy.signal import butter, filtfilt  # type: ignore

    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False


def _series_fs_from_timestamps(ts: pd.Series) -> float | None:
    if ts is None or ts.empty:
        return None
    ts = pd.to_datetime(ts, errors="coerce").dropna().sort_values().drop_duplicates()
    dts = ts.diff().dt.total_seconds()
    dts = dts[dts > 0]  # ignore 0s (duplicates) and negatives
    if dts.empty:
        return None
    dt_s = dts.median()
    return 1.0 / dt_s if dt_s > 0 else None


def _butter_filter_1d(
    x: pd.Series, fs_hz: float, cutoff_hz: float, order: int, btype: str
) -> pd.Series:
    if not HAS_SCIPY or fs_hz is None or fs_hz <= 0:
        return x

    # Numeric series + light interpolation (filtfilt dislikes internal NaNs)
    x_num = pd.to_numeric(x, errors="coerce").astype(float)
    if x_num.isna().all():
        return x
    mask_nan = x_num.isna()
    x_filled = x_num.interpolate(limit_direction="both")

    # Clamp cutoff into (0, Nyquist) to avoid unchanged returns
    nyq = 0.5 * fs_hz
    cut = float(cutoff_hz)
    if not math.isfinite(cut) or cut <= 0:
        return x
    cut = min(cut, 0.99 * nyq)

    try:
        # Use API with fs= (no need to normalize manually)
        b, a = butter(order, cut, btype=btype, fs=fs_hz)
        n = max(len(a), len(b))
        padlen = 3 * (n - 1)
        if len(x_filled) <= max(padlen, 10):
            return x
        y = filtfilt(b, a, x_filled.to_numpy(), method="pad")
        y = pd.Series(y, index=x.index)
        # (optional) re-inject NaNs where the original had them
        y[mask_nan] = float("nan")
        return y
    except Exception:
        return x


def _apply_global_rolling(df: pd.DataFrame) -> pd.DataFrame:
    """Global rolling mean (if enabled)."""
    if df is None or df.empty or not st.session_state.get("rolling_enabled", False):
        return df

    window = int(st.session_state.get("rolling_window", 10))
    center = bool(st.session_state.get("rolling_center", True))
    min_periods = int(st.session_state.get("rolling_min_periods", 1))

    group_cols = [
        c
        for c in ["sensor_id", "sensor", "measurement", "sensor_type"]
        if c in df.columns
    ]
    df = df.sort_values(group_cols + ["timestamp"]).copy()

    def _roll(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("timestamp").copy()
        if "value" in g.columns:
            g["value"] = (
                g["value"]
                .rolling(window=window, center=center, min_periods=min_periods)
                .mean()
            )
        return g

    return (
        df.groupby(group_cols, group_keys=False).apply(_roll)
        if group_cols
        else _roll(df)
    )


def _apply_lowpass(df: pd.DataFrame) -> pd.DataFrame:
    """Global low-pass (Butterworth if SciPy available, otherwise rolling mean)."""
    if df is None or df.empty or not st.session_state.get("lp_enabled", False):
        return df

    group_cols = [
        c
        for c in ["sensor_id", "sensor", "measurement", "sensor_type"]
        if c in df.columns
    ]
    df = df.sort_values(group_cols + ["timestamp"]).copy()

    if HAS_SCIPY:
        cutoff_hz = float(st.session_state.get("lp_cutoff_hz", 5.0))
        order = int(st.session_state.get("lp_order", 3))

        def _lp_butter(g: pd.DataFrame) -> pd.DataFrame:
            g = g.sort_values("timestamp").copy()
            fs = _series_fs_from_timestamps(g["timestamp"])
            if "value" in g.columns and fs:
                g["value"] = _butter_filter_1d(g["value"], fs, cutoff_hz, order, "low")
            return g

        return (
            df.groupby(group_cols, group_keys=False).apply(_lp_butter)
            if group_cols
            else _lp_butter(df)
        )

    # Fallback: rolling mean as low-pass
    lp_window = int(st.session_state.get("lp_window_points", 25))
    center = bool(st.session_state.get("rolling_center", True))
    minp = min(int(st.session_state.get("rolling_min_periods", 1)), lp_window)

    def _lp_roll(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("timestamp").copy()
        if "value" in g.columns:
            g["value"] = (
                g["value"]
                .rolling(window=lp_window, center=center, min_periods=minp)
                .mean()
            )
        return g

    return (
        df.groupby(group_cols, group_keys=False).apply(_lp_roll)
        if group_cols
        else _lp_roll(df)
    )


def _apply_highpass(df: pd.DataFrame) -> pd.DataFrame:
    """Global high-pass (Butterworth if SciPy available, otherwise x - rolling_mean(x))."""
    if df is None or df.empty or not st.session_state.get("hp_enabled", False):
        return df

    group_cols = [
        c
        for c in ["sensor_id", "sensor", "measurement", "sensor_type"]
        if c in df.columns
    ]
    df = df.sort_values(group_cols + ["timestamp"]).copy()

    if HAS_SCIPY:
        cutoff_hz = float(st.session_state.get("hp_cutoff_hz", 5.0))
        order = int(st.session_state.get("hp_order", 3))

        def _hp_butter(g: pd.DataFrame) -> pd.DataFrame:
            g = g.sort_values("timestamp").copy()
            fs = _series_fs_from_timestamps(g["timestamp"])
            if "value" in g.columns and fs:
                g["value"] = _butter_filter_1d(g["value"], fs, cutoff_hz, order, "high")
            return g

        return (
            df.groupby(group_cols, group_keys=False).apply(_hp_butter)
            if group_cols
            else _hp_butter(df)
        )

    # Fallback: x - rolling_mean(x)
    hp_window = int(st.session_state.get("hp_window_points", 25))
    center = bool(st.session_state.get("rolling_center", True))
    minp = min(int(st.session_state.get("rolling_min_periods", 1)), hp_window)

    def _hp_roll(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values("timestamp").copy()
        if "value" in g.columns:
            baseline = (
                g["value"]
                .rolling(window=hp_window, center=center, min_periods=minp)
                .mean()
            )
            g["value"] = g["value"] - baseline
        return g

    return (
        df.groupby(group_cols, group_keys=False).apply(_hp_roll)
        if group_cols
        else _hp_roll(df)
    )


with st.container(border=True):
    st.sidebar.subheader("Settings")

    data = None

    data_source = st.sidebar.radio(
        "Data source",
        ["Database", "CSV"],
        captions=["InfluxDB", "CSV import"],
        key="data_source_radio",
    )

    if data_source == "CSV":
        uploaded_file = st.sidebar.file_uploader(
            "Upload CSV file", type=["csv"], key="csv_uploader"
        )
        if uploaded_file is not None:
            data = pd.read_csv(uploaded_file, parse_dates=["timestamp"])
            st.sidebar.success("File uploaded successfully")
            st.badge("Using imported data", icon=":material/check:", color="blue")
        else:
            st.sidebar.warning("Please upload a CSV file")
            st.stop()

    st.sidebar.divider()

    # ---------- INIT default values BEFORE widgets ----------
    if "filters__init_done" not in st.session_state:
        # Rolling
        st.session_state["rolling_enabled"] = False
        st.session_state["rolling_window"] = 10
        st.session_state["rolling_center"] = True
        st.session_state["rolling_min_periods"] = 1
        # Low-pass
        st.session_state["lp_enabled"] = False
        st.session_state["lp_order"] = 3
        st.session_state["lp_cutoff_hz"] = 5.0
        st.session_state["lp_window_points"] = 25  # pandas fallback
        # High-pass
        st.session_state["hp_enabled"] = False
        st.session_state["hp_order"] = 3
        st.session_state["hp_cutoff_hz"] = 5.0
        st.session_state["hp_window_points"] = 25  # pandas fallback
        st.session_state["filters__init_done"] = True

    # ---------- Filters & Smoothing ----------
    with st.sidebar.expander("Filters & Smoothing", expanded=False):
        # Rolling mean (always available)
        st.checkbox("Enable Rolling mean", key="rolling_enabled")
        st.slider(
            "Rolling window (points)",
            min_value=2,
            max_value=500,
            step=1,
            key="rolling_window",
        )
        st.checkbox("Centered window (rolling)", key="rolling_center")
        current_window = int(st.session_state.get("rolling_window", 10))
        default_minp = min(
            int(st.session_state.get("rolling_min_periods", 1)), current_window
        )
        st.slider(
            "min_periods (rolling)",
            min_value=1,
            max_value=current_window,
            value=default_minp,
            step=1,
            key="rolling_min_periods",
        )

        st.divider()

        # Low-pass
        st.checkbox("Enable Low-pass", key="lp_enabled")
        if HAS_SCIPY:
            st.number_input(
                "Low-pass cutoff (period in Hz)",
                min_value=0.01,
                step=0.1,
                key="lp_cutoff_hz",
                help="Larger = slower filter (lower cutoff frequency).",
            )
            st.slider(
                "Low-pass order (Butterworth)",
                min_value=1,
                max_value=8,
                value=int(st.session_state["lp_order"]),
                key="lp_order",
            )
        else:
            st.slider(
                "Low-pass window (points)",
                min_value=2,
                max_value=1000,
                value=int(st.session_state["lp_window_points"]),
                key="lp_window_points",
            )

        st.divider()

        # High-pass
        st.checkbox("Enable High-pass", key="hp_enabled")
        if HAS_SCIPY:
            st.number_input(
                "High-pass cutoff (period in Hz)",
                min_value=0.01,
                step=0.1,
                key="hp_cutoff_hz",
                help="Smaller = stronger cutoff of low frequencies.",
            )
            st.slider(
                "High-pass order (Butterworth)",
                min_value=1,
                max_value=8,
                value=int(st.session_state["hp_order"]),
                key="hp_order",
            )
        else:
            st.slider(
                "High-pass window (points)",
                min_value=2,
                max_value=1000,
                value=int(st.session_state["hp_window_points"]),
                key="hp_window_points",
            )

        st.info(
            "Filters order: **Rolling → Low-pass → High-pass**.\n"
            "If Low-pass **and** High-pass are enabled, the effect is a **Band-pass**."
        )

    # ---------- Sensor / measurement selection ----------
    selected_sensors, selected_measurements = data_selector(data=data)

    # ---------- Data retrieval ----------
    selected_data = get_data(
        data=data,
        sensors=selected_sensors,
        measurements=selected_measurements,
        start_time=dt.datetime.fromtimestamp(0),
        end_time=dt.datetime.now(dt.timezone.utc),
    )

    # ---------- Filter pipeline ----------
    selected_data = _apply_global_rolling(selected_data)
    selected_data = _apply_lowpass(selected_data)
    selected_data = _apply_highpass(selected_data)

    # ---------- Main graph ----------
    if not selected_data.empty:
        fig = px.line(
            selected_data,
            x="timestamp",
            y="value",
            color="sensor_type",
            line_group="sensor",
            hover_data=[
                "timestamp",
                "sensor_id",
                "sensor",
                "measurement",
                "sensor_type",
                "value",
            ],
            markers=True,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data to display with the current selection.")

    # ---------- Detailed analysis ----------
    data_analysis(selected_data)
