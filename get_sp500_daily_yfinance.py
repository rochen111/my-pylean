#!/usr/bin/env python3
"""Download maximum historical daily S&P 500 data from yfinance."""

from __future__ import annotations

import sys

import pandas as pd

try:
    import yfinance as yf
except Exception as exc:
    print("Missing dependency: yfinance")
    print("Install it with: pip install yfinance")
    raise SystemExit(1) from exc


TICKER = "^GSPC"
INTERVAL = "1d"
PERIOD = "max"
OUTPUT_CSV = "sp500_daily_max_yfinance_data.csv"


def download_sp500_daily_max() -> pd.DataFrame:
    """Fetch full available daily history for S&P 500 index from Yahoo Finance."""
    df = yf.download(
        tickers=TICKER,
        period=PERIOD,
        interval=INTERVAL,
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if df is None or df.empty:
        raise RuntimeError("No data returned from yfinance for ^GSPC.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    df = df.rename(columns={date_col: "timestamp"})

    keep_cols = [
        "timestamp",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].copy()

    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    df = df.rename(columns=rename_map)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def main() -> None:
    print("Downloading S&P 500 daily max history from yfinance...")

    try:
        df = download_sp500_daily_max()
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from None

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Ticker: {TICKER}")
    print(f"Saved: {len(df):,} rows -> {OUTPUT_CSV}")
    print(f"Range: {df['timestamp'].min().date()} -> {df['timestamp'].max().date()}")


if __name__ == "__main__":
    main()
