#!/usr/bin/env python3
"""Download raw multi-instrument market data from yfinance incrementally.

Notes:
- Yahoo limits intraday lookback windows.
- Each run appends only unseen timestamps to the per-file CSVs.
"""

from __future__ import annotations

import os

import pandas as pd
import yfinance as yf


DEFAULT_INTERVALS = [
    "5m",
    "60m",
    "1d",
    "1wk",
    "1mo",
    "3mo",
]

REDUCED_INTERVALS = ["1d", "1wk", "1mo"]

INSTRUMENTS: dict[str, str] = {
    "vix": "^VIX",
    "es": "ES=F",
    "nq": "NQ=F",
    "ym": "YM=F",
    "rty": "RTY=F",
    "cl": "CL=F",
    "gc": "GC=F",
    "eurusd": "EURUSD=X",
    "gbpusd": "GBPUSD=X",
    "usdjpy": "JPY=X",
    "btc": "BTC-USD",
    "eth": "ETH-USD",
    "tlt": "TLT",
    "ief": "IEF",
    "shy": "SHY",
    "tnx": "^TNX",
    "fvx": "^FVX",
    "nikkei": "^N225",
    "ftse": "^FTSE",
    "dax": "^GDAXI",
    "hsi": "^HSI",
}

# Per user request: no 5m, 1h, quarterly for these instruments.
REDUCED_INTERVAL_INSTRUMENTS = {"vix", "tnx", "fvx", "nikkei", "ftse", "dax", "hsi"}

# Yahoo lookback constraints: intraday intervals are limited.
PERIOD_BY_INTERVAL = {
    "5m": "60d",
    "60m": "60d",
    "1d": "max",
    "1wk": "max",
    "1mo": "max",
    "3mo": "max",
}

OUTPUT_INTERVAL_LABEL = {
    "60m": "1h",
}


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    out = df.reset_index()
    date_col = "Datetime" if "Datetime" in out.columns else "Date"
    out = out.rename(columns={date_col: "timestamp"})

    keep_cols = ["timestamp", "Open", "High", "Low", "Close", "Volume"]
    keep_cols = [c for c in keep_cols if c in out.columns]
    out = out[keep_cols].copy()

    out = out.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return out


def load_existing_csv(filename: str) -> pd.DataFrame:
    if not os.path.exists(filename):
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    existing = pd.read_csv(filename)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(existing.columns):
        raise RuntimeError(f"Existing file {filename} does not match expected schema: {sorted(required)}")

    existing["timestamp"] = pd.to_datetime(existing["timestamp"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        existing[col] = pd.to_numeric(existing[col], errors="coerce")

    existing = existing.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return existing[["timestamp", "open", "high", "low", "close", "volume"]]


def merge_incremental(existing: pd.DataFrame, latest: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if existing.empty:
        merged = latest.sort_values("timestamp").reset_index(drop=True)
        return merged, len(merged)

    existing_ts = set(existing["timestamp"])
    new_rows = latest[~latest["timestamp"].isin(existing_ts)]
    inserted_count = len(new_rows)

    merged = pd.concat([existing, new_rows], ignore_index=True)
    merged = merged.drop_duplicates(subset=["timestamp"], keep="first")
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    return merged, inserted_count


def fetch_data(ticker: str, interval: str) -> pd.DataFrame:
    period = PERIOD_BY_INTERVAL[interval]
    df = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        group_by="column",
    )

    if df is None or df.empty:
        return pd.DataFrame()

    return _normalize_frame(df)


def output_filename(instrument: str, interval: str) -> str:
    interval_label = OUTPUT_INTERVAL_LABEL.get(interval, interval)
    return f"{instrument}_{interval_label}_yfinance_data.csv"


def main() -> None:
    summaries: list[dict[str, str | int]] = []

    for instrument, ticker in INSTRUMENTS.items():
        intervals = REDUCED_INTERVALS if instrument in REDUCED_INTERVAL_INSTRUMENTS else DEFAULT_INTERVALS

        for interval in intervals:
            filename = output_filename(instrument, interval)
            period = PERIOD_BY_INTERVAL[interval]

            try:
                latest = fetch_data(ticker, interval)
                if latest.empty:
                    summaries.append(
                        {
                            "instrument": instrument,
                            "ticker": ticker,
                            "interval": interval,
                            "period": period,
                            "status": "empty",
                            "rows": 0,
                            "inserted": 0,
                            "start": "",
                            "end": "",
                            "file": "",
                        }
                    )
                    continue

                existing = load_existing_csv(filename)
                merged, inserted = merge_incremental(existing, latest)
                merged.to_csv(filename, index=False)

                summaries.append(
                    {
                        "instrument": instrument,
                        "ticker": ticker,
                        "interval": interval,
                        "period": period,
                        "status": "ok",
                        "rows": len(merged),
                        "inserted": inserted,
                        "start": str(merged["timestamp"].min()),
                        "end": str(merged["timestamp"].max()),
                        "file": filename,
                    }
                )
            except Exception as exc:
                summaries.append(
                    {
                        "instrument": instrument,
                        "ticker": ticker,
                        "interval": interval,
                        "period": period,
                        "status": f"error: {exc}",
                        "rows": 0,
                        "inserted": 0,
                        "start": "",
                        "end": "",
                        "file": "",
                    }
                )

    summary_df = pd.DataFrame(summaries)
    print(summary_df.to_string(index=False))
    print("Updated per-file CSVs incrementally.")


if __name__ == "__main__":
    main()
