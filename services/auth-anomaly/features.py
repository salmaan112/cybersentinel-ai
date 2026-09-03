"""
Feature engineering for auth-anomaly detection. Converts raw login events into
per-event features that capture the behavioral signals that actually indicate
an attack — this is the same kind of windowed/velocity logic as SQL
ROW_NUMBER()/LAG() queries, just expressed in pandas.
"""
import pandas as pd
from math import radians, sin, cos, sqrt, atan2

EARTH_RADIUS_KM = 6371


def haversine_km(lat1, lon1, lat2, lon2):
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * atan2(sqrt(a), sqrt(1 - a))


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)

    # --- Per-user velocity features (LAG-style: compare to this user's previous login) ---
    df["prev_ts_user"] = df.groupby("user_id")["timestamp"].shift(1)
    df["seconds_since_last_login_user"] = (
        (df["timestamp"] - df["prev_ts_user"]).dt.total_seconds().fillna(999999)
    )

    df["prev_lat"] = df.groupby("user_id")["lat"].shift(1)
    df["prev_lon"] = df.groupby("user_id")["lon"].shift(1)
    df["distance_km_from_prev"] = df.apply(
        lambda r: haversine_km(r["prev_lat"], r["prev_lon"], r["lat"], r["lon"])
        if pd.notnull(r["prev_lat"]) else 0.0,
        axis=1,
    )
    # Impossible-travel signal: km per hour required to have made this trip.
    # Anything above ~900 km/h (commercial flight speed) is physically implausible.
    hours_elapsed = (df["seconds_since_last_login_user"] / 3600).clip(lower=0.01)
    df["implied_travel_speed_kmh"] = df["distance_km_from_prev"] / hours_elapsed

    # --- Per-IP velocity features (credential stuffing / brute force signal) ---
    df["prev_ts_ip"] = df.groupby("ip")["timestamp"].shift(1)
    df["seconds_since_last_login_ip"] = (
        (df["timestamp"] - df["prev_ts_ip"]).dt.total_seconds().fillna(999999)
    )

    # Rolling window (last 5 min) per IP: distinct users targeted, failure count.
    # This mirrors a SQL window function: PARTITION BY ip ORDER BY timestamp
    # RANGE BETWEEN INTERVAL 5 MIN PRECEDING AND CURRENT ROW.
    df = df.sort_values("timestamp").reset_index(drop=True)
    distinct_users_5min = []
    failed_attempts_5min = []
    for i, row in df.iterrows():
        window = df[
            (df["ip"] == row["ip"]) &
            (df["timestamp"] <= row["timestamp"]) &
            (df["timestamp"] > row["timestamp"] - pd.Timedelta(minutes=5))
        ]
        distinct_users_5min.append(window["user_id"].nunique())
        failed_attempts_5min.append((window["success"] == 0).sum())
    df["distinct_users_from_ip_5min"] = distinct_users_5min
    df["failed_attempts_from_ip_5min"] = failed_attempts_5min

    feature_cols = [
        "seconds_since_last_login_user", "distance_km_from_prev",
        "implied_travel_speed_kmh", "seconds_since_last_login_ip",
        "distinct_users_from_ip_5min", "failed_attempts_from_ip_5min",
        "success",
    ]
    return df, feature_cols
