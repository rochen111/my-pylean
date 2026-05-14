#!/usr/bin/env python3
"""Download and incrementally update raw FRED market series to CSV files.

This script supports multiple instruments and frequencies. It preserves existing
CSV data and appends only new timestamps on each run.
"""

from __future__ import annotations

from io import StringIO
import os

import matplotlib.pyplot as plt
import pandas as pd
import requests


FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
DEFAULT_TIMEFRAME = "max"

SERIES_CONFIG = [
    {"instrument": "sp500", "series_id": "SP500", "frequency": "daily", "timeframe": "max"},
    {"instrument": "djia", "series_id": "DJIA", "frequency": "daily", "timeframe": "max"},
    # Legacy monthly DJIA history available without API key (1914-1968).
    {"instrument": "djia", "series_id": "M1109BUSM293NNBR", "frequency": "monthly", "timeframe": "max"},
    {"instrument": "vixcls", "series_id": "VIXCLS", "frequency": "daily", "timeframe": "max"},
    {"instrument": "nikkei225", "series_id": "NIKKEI225", "frequency": "daily", "timeframe": "max"},
    {"instrument": "dexjpus", "series_id": "DEXJPUS", "frequency": "daily", "timeframe": "max"},
    {"instrument": "dexusuk", "series_id": "DEXUSUK", "frequency": "daily", "timeframe": "max"},
    {"instrument": "dexuseu", "series_id": "DEXUSEU", "frequency": "daily", "timeframe": "max"},
]


def _build_proxies() -> dict[str, str] | None:
    user = os.getenv("WAM_PROXY_USER")
    password = os.getenv("WAM_PROXY_PASS")
    host = os.getenv("WAM_PROXY_HOST", "proxy.westernasset.com")
    port = os.getenv("WAM_PROXY_PORT", "8080")

    if user and password:
        proxy = f"http://{user}:{password}@{host}:{port}"
        return {"http": proxy, "https": proxy}
    return None


def output_csv(instrument: str, frequency: str, timeframe: str) -> str:
    return f"{instrument}_{frequency}_{timeframe}_fred_data.csv"


def output_png(instrument: str, frequency: str, timeframe: str) -> str:
    return f"{instrument}_{frequency}_{timeframe}_fred.png"


def legacy_output_csv(instrument: str, frequency: str) -> str:
    """Previous filename pattern kept for backward compatibility."""
    return f"{instrument}_{frequency}_fred_data.csv"


def _api_frequency_code(frequency: str) -> str | None:
    mapping = {"daily": None, "monthly": "m"}
    return mapping.get(frequency)


def fetch_fred_series(series_id: str, frequency: str, proxies: dict[str, str] | None) -> pd.DataFrame:
    """Fetch one raw FRED series into [timestamp, close]."""
    api_key = os.getenv("FRED_API_KEY")
    print(f"Downloading {series_id} ({frequency})")

    if api_key:
        params: dict[str, str | int] = {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": "1900-01-01",
            "sort_order": "asc",
            "limit": 100000,
        }
        freq_code = _api_frequency_code(frequency)
        if freq_code:
            params["frequency"] = freq_code
            params["aggregation_method"] = "eop"

        response = requests.get(FRED_API_URL, timeout=30, proxies=proxies, params=params)
        response.raise_for_status()
        payload = response.json()

        observations = payload.get("observations", [])
        if not observations:
            raise RuntimeError(f"FRED API returned no observations for {series_id}")

        df = pd.DataFrame(observations)
        if "date" not in df.columns or "value" not in df.columns:
            raise RuntimeError(f"Unexpected API schema for {series_id}: {list(df.columns)}")
        df = df.rename(columns={"date": "timestamp", "value": "close"})
    else:
        params: dict[str, str] = {"id": series_id}
        # Graph endpoint is typically capped around recent years for some series.
        if frequency == "monthly":
            params["fq"] = "Monthly"

        response = requests.get(FRED_GRAPH_URL, timeout=30, proxies=proxies, params=params)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))

        if "observation_date" in df.columns:
            date_col = "observation_date"
        elif "DATE" in df.columns:
            date_col = "DATE"
        else:
            raise RuntimeError(f"Unexpected graph schema for {series_id}: {list(df.columns)}")

        if series_id in df.columns:
            value_col = series_id
        elif len(df.columns) >= 2:
            value_col = df.columns[1]
        else:
            raise RuntimeError(f"No value column found for {series_id}")

        df = df.rename(columns={date_col: "timestamp", value_col: "close"})

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["timestamp", "close"])
    df = df[["timestamp", "close"]].sort_values("timestamp").reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f"No valid numeric rows for {series_id}")
    return df


def load_existing(path: str, legacy_path: str | None = None) -> pd.DataFrame:
    source_path = path
    if not os.path.exists(source_path) and legacy_path and os.path.exists(legacy_path):
        source_path = legacy_path
        print(f"Using legacy file for incremental merge: {legacy_path}")

    if not os.path.exists(source_path):
        return pd.DataFrame(columns=["timestamp", "close"])

    existing = pd.read_csv(source_path)
    if "close" not in existing.columns and "value" in existing.columns:
        existing = existing.rename(columns={"value": "close"})

    if not {"timestamp", "close"}.issubset(existing.columns):
        raise RuntimeError(f"Invalid existing schema in {path}; expected timestamp,close")

    existing["timestamp"] = pd.to_datetime(existing["timestamp"], errors="coerce")
    existing["close"] = pd.to_numeric(existing["close"], errors="coerce")
    existing = existing.dropna(subset=["timestamp", "close"])
    return existing[["timestamp", "close"]].sort_values("timestamp").reset_index(drop=True)


def merge_incremental(existing: pd.DataFrame, latest: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if existing.empty:
        merged = latest.sort_values("timestamp").reset_index(drop=True)
        return merged, len(merged)

    existing_ts = set(existing["timestamp"])
    new_rows = latest[~latest["timestamp"].isin(existing_ts)]
    inserted = len(new_rows)

    merged = pd.concat([existing, new_rows], ignore_index=True)
    merged = merged.drop_duplicates(subset=["timestamp"], keep="first")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    return merged, inserted


def plot_series(df: pd.DataFrame, instrument: str, frequency: str, timeframe: str) -> None:
    png_path = output_png(instrument, frequency, timeframe)
    plt.figure(figsize=(12, 6))
    plt.plot(df["timestamp"], df["close"], linewidth=1.2)
    plt.title(f"FRED {instrument.upper()} ({frequency}, {timeframe})")
    plt.xlabel("Date")
    plt.ylabel("Close")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_path, dpi=140)
    print(f"Chart saved: {png_path}")


def update_one(config: dict[str, str], proxies: dict[str, str] | None) -> None:
    instrument = config["instrument"]
    series_id = config["series_id"]
    frequency = config["frequency"]
    timeframe = config.get("timeframe", DEFAULT_TIMEFRAME)

    csv_path = output_csv(instrument, frequency, timeframe)
    legacy_csv_path = legacy_output_csv(instrument, frequency)
    latest = fetch_fred_series(series_id, frequency, proxies)
    existing = load_existing(csv_path, legacy_csv_path)
    merged, inserted = merge_incremental(existing, latest)

    merged.to_csv(csv_path, index=False)
    print(f"Saved: {len(merged):,} rows -> {csv_path}")
    print(f"New rows inserted this run: {inserted:,}")
    print(f"Range: {merged['timestamp'].min().date()} -> {merged['timestamp'].max().date()}")
    plot_series(merged, instrument, frequency, timeframe)


def main() -> None:
    print("=" * 72)
    print("FRED Multi-Series Incremental Downloader")
    print("=" * 72)

    if not os.getenv("FRED_API_KEY"):
        print("FRED_API_KEY not set: using no-key graph CSV endpoint (some series are capped).")

    proxies = _build_proxies()
    failures: list[str] = []

    for cfg in SERIES_CONFIG:
        print("-" * 72)
        try:
            update_one(cfg, proxies)
        except Exception as exc:
            failures.append(f"{cfg['series_id']} ({cfg['frequency']}): {exc}")
            print(f"ERROR: {failures[-1]}")

    print("=" * 72)
    if failures:
        print("Completed with errors:")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)

    print("All series updated successfully.")


if __name__ == "__main__":
    main()
