#!/usr/bin/env python3
"""Ingest market data directly from yfinance into ClickHouse.

Usage:
    python3 ingest_to_clickhouse.py                  # ingest all symbols/timeframes
    python3 ingest_to_clickhouse.py --verify         # verification only
    python3 ingest_to_clickhouse.py --dry-run        # fetch + parse, skip DB writes
    python3 ingest_to_clickhouse.py --symbols es,nq --timeframes 1d,1wk

The loader is idempotent at natural key level and incremental by watermark:
- Natural key: (instrument_id, timeframe_id, timestamp)
- Incremental filter: insert rows where timestamp > max(existing timestamp)
"""

from __future__ import annotations

import argparse
import time
from datetime import timezone

import pandas as pd
from clickhouse_driver import Client
from clickhouse_driver.errors import ServerException

# -- Config -----------------------------------------------------------------
CH_HOST = "localhost"
CH_PORT = 9000
CH_DATABASE = "market"
SOURCE_ID = 1  # yfinance

TIMEFRAME_TO_YF_INTERVAL: dict[str, str] = {
    "5m": "5m",
    "1h": "60m",
    "1d": "1d",
    "1wk": "1wk",
    "1mo": "1mo",
    "3mo": "3mo",
}

# yfinance limits intraday history; period is chosen to maximize reliable history.
TIMEFRAME_TO_YF_PERIOD: dict[str, str] = {
    "5m": "60d",
    "1h": "730d",
    "1d": "max",
    "1wk": "max",
    "1mo": "max",
    "3mo": "max",
}

INTRADAY_LABELS = {"5m", "1h"}


# -- Helpers ----------------------------------------------------------------

def connect() -> Client:
    return Client(host=CH_HOST, port=CH_PORT, database=CH_DATABASE)


def load_instruments(client: Client) -> dict[str, dict[str, object]]:
    rows = client.execute(
        "SELECT instrument_id, symbol, yf_ticker FROM instruments ORDER BY instrument_id"
    )
    return {
        row[1]: {
            "instrument_id": int(row[0]),
            "yf_ticker": str(row[2]),
        }
        for row in rows
    }


def load_timeframes(client: Client) -> dict[str, int]:
    rows = client.execute("SELECT label, timeframe_id FROM timeframes")
    return {str(label): int(tf_id) for label, tf_id in rows}


def _normalise_yf_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["timestamp", "session_date", "open", "high", "low", "close", "volume"])

    data = df.copy()

    # yfinance can return MultiIndex columns depending on ticker shape.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [str(c[0]).lower() if c[0] else str(c[-1]).lower() for c in data.columns]
    else:
        data.columns = [str(c).lower() for c in data.columns]

    data = data.reset_index()
    data.columns = [str(c).lower() for c in data.columns]

    if "datetime" in data.columns and "timestamp" not in data.columns:
        data = data.rename(columns={"datetime": "timestamp"})
    if "date" in data.columns and "timestamp" not in data.columns:
        data = data.rename(columns={"date": "timestamp"})

    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"yfinance frame missing expected columns: {sorted(missing)}")

    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    data = data.dropna(subset=["timestamp", "open", "high", "low", "close"])

    for col in ["open", "high", "low", "close", "volume"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["open", "high", "low", "close"])
    data["volume"] = data["volume"].fillna(0.0)
    data["session_date"] = data["timestamp"].dt.date

    data = data.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return data[["timestamp", "session_date", "open", "high", "low", "close", "volume"]]


def fetch_yfinance(symbol: str, yf_ticker: str, tf_label: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is not installed. Install with: pip install yfinance") from exc

    interval = TIMEFRAME_TO_YF_INTERVAL.get(tf_label)
    period = TIMEFRAME_TO_YF_PERIOD.get(tf_label)
    if interval is None or period is None:
        raise ValueError(f"Unsupported timeframe label for yfinance mapping: {tf_label}")

    raw = yf.download(
        tickers=yf_ticker,
        interval=interval,
        period=period,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    frame = _normalise_yf_frame(raw)
    if frame.empty:
        print(f"  [no-data] {symbol}/{tf_label} ({yf_ticker})")
    return frame


def get_max_ts(client: Client, instrument_id: int, timeframe_id: int):
    row = client.execute(
        "SELECT max(timestamp) FROM market_bars WHERE instrument_id = %(iid)s AND timeframe_id = %(tid)s",
        {"iid": instrument_id, "tid": timeframe_id},
    )
    max_ts = row[0][0] if row and row[0][0] else None
    if max_ts is None:
        return None
    ts = pd.Timestamp(max_ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def start_run(client: Client) -> int:
    run_id = int(time.time() * 1000)
    now = pd.Timestamp.now("UTC").to_pydatetime()
    client.execute(
        "INSERT INTO ingestion_runs (run_id, started_at, source_id, status) VALUES",
        [{"run_id": run_id, "started_at": now, "source_id": SOURCE_ID, "status": "running"}],
    )
    return run_id


def finish_run(client: Client, run_id: int, rows_inserted: int, status: str = "done") -> None:
    now = pd.Timestamp.now("UTC").to_pydatetime()
    client.execute(
        "INSERT INTO ingestion_runs (run_id, started_at, finished_at, source_id, status, rows_inserted) VALUES",
        [{
            "run_id": run_id,
            "started_at": now,
            "finished_at": now,
            "source_id": SOURCE_ID,
            "status": status,
            "rows_inserted": rows_inserted,
        }],
    )


def refresh_coverage_from_table(
    client: Client,
    instrument_id: int,
    timeframe_id: int,
    tf_label: str,
) -> None:
    row = client.execute(
        """
        SELECT min(timestamp), max(timestamp), count()
        FROM market_bars
        WHERE instrument_id = %(iid)s AND timeframe_id = %(tid)s
        """,
        {"iid": instrument_id, "tid": timeframe_id},
    )[0]

    earliest, latest, total = row
    if earliest is None or latest is None:
        return

    now = pd.Timestamp.now("UTC").to_pydatetime()
    client.execute(
        """
        INSERT INTO data_coverage
        (instrument_id, timeframe_id, source_id, earliest_ts, latest_ts, total_bars, is_partial, last_updated)
        VALUES
        """,
        [{
            "instrument_id": instrument_id,
            "timeframe_id": timeframe_id,
            "source_id": SOURCE_ID,
            "earliest_ts": pd.Timestamp(earliest).to_pydatetime().replace(tzinfo=timezone.utc),
            "latest_ts": pd.Timestamp(latest).to_pydatetime().replace(tzinfo=timezone.utc),
            "total_bars": int(total),
            "is_partial": 1 if tf_label in INTRADAY_LABELS else 0,
            "last_updated": now,
        }],
    )


def ingest_symbol_timeframe(
    client: Client,
    symbol: str,
    instrument_id: int,
    yf_ticker: str,
    tf_label: str,
    timeframe_id: int,
    run_id: int,
    dry_run: bool,
) -> int:
    try:
        df = fetch_yfinance(symbol, yf_ticker, tf_label)
    except Exception as exc:
        print(f"  [error] {symbol}/{tf_label}: yfinance fetch failed: {exc}")
        return 0

    if df.empty:
        return 0

    max_ts = get_max_ts(client, instrument_id, timeframe_id)
    if max_ts is not None:
        new_rows = df[df["timestamp"] > max_ts]
    else:
        new_rows = df

    if new_rows.empty:
        print(f"  [up-to-date] {symbol}/{tf_label}")
        if not dry_run:
            refresh_coverage_from_table(client, instrument_id, timeframe_id, tf_label)
        return 0

    if dry_run:
        print(f"  [dry-run] {symbol}/{tf_label}: fetched={len(df):,}, new={len(new_rows):,}")
        return 0

    records = [
        {
            "instrument_id": instrument_id,
            "timeframe_id": timeframe_id,
            "timestamp": row.timestamp.to_pydatetime().replace(tzinfo=timezone.utc),
            "session_date": row.session_date,
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
            "ingestion_run": run_id,
        }
        for row in new_rows.itertuples(index=False)
    ]

    for attempt in range(3):
        try:
            client.execute(
                "INSERT INTO market_bars VALUES",
                records,
                settings={"max_partitions_per_insert_block": 1000},
            )
            break
        except ServerException as exc:
            if "CPU is overloaded" in str(exc) and attempt < 2:
                wait = 10 * (attempt + 1)
                print(f"  [retry in {wait}s] CPU overload on {symbol}/{tf_label} (attempt {attempt + 1})")
                time.sleep(wait)
            else:
                raise

    refresh_coverage_from_table(client, instrument_id, timeframe_id, tf_label)
    print(f"  [inserted] {symbol}/{tf_label}: {len(records):,} new rows")
    return len(records)


def verify(client: Client) -> None:
    print("\n-- Verification ----------------------------------------")
    rows = client.execute(
        """
        SELECT
            i.symbol,
            t.label,
            dc.total_bars,
            dc.earliest_ts,
            dc.latest_ts,
            dc.is_partial
        FROM data_coverage dc
        JOIN instruments i ON i.instrument_id = dc.instrument_id
        JOIN timeframes t ON t.timeframe_id = dc.timeframe_id
        ORDER BY i.symbol, t.timeframe_id
        """,
        settings={"max_threads": 1},
    )
    print(f"{'symbol':<10} {'tf':<5} {'bars':>9}  {'earliest':<12} {'latest':<12} {'partial'}")
    print("-" * 66)
    for symbol, tf, bars, earliest, latest, partial in rows:
        print(f"{symbol:<10} {tf:<5} {int(bars):>9,}  {str(earliest)[:10]:<12} {str(latest)[:10]:<12} {'yes' if partial else 'no'}")

    total = client.execute("SELECT count() FROM market_bars", settings={"max_threads": 1})[0][0]
    print(f"\nTotal rows in market_bars: {int(total):,}")


def parse_csv_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


# -- Main -------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Direct yfinance-to-ClickHouse ingestion")
    parser.add_argument("--verify", action="store_true", help="Print coverage summary after ingestion")
    parser.add_argument("--ingest", action="store_true", help="Force ingestion even when --verify is set")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse data, skip DB writes")
    parser.add_argument("--symbols", default="", help="Comma-separated symbols (default: all from instruments)")
    parser.add_argument("--timeframes", default="", help="Comma-separated timeframe labels (default: all mapped labels)")
    args = parser.parse_args()

    client = connect()

    if args.verify and not args.ingest and not args.dry_run:
        verify(client)
        return

    instruments = load_instruments(client)
    timeframe_map = load_timeframes(client)

    symbols = parse_csv_list(args.symbols) if args.symbols else sorted(instruments.keys())
    timeframes = parse_csv_list(args.timeframes) if args.timeframes else sorted(TIMEFRAME_TO_YF_INTERVAL.keys())

    unknown_symbols = [s for s in symbols if s not in instruments]
    if unknown_symbols:
        raise ValueError(f"Unknown symbols (missing from instruments table): {unknown_symbols}")

    unknown_timeframes = [tf for tf in timeframes if tf not in timeframe_map or tf not in TIMEFRAME_TO_YF_INTERVAL]
    if unknown_timeframes:
        raise ValueError(f"Unsupported or unknown timeframes: {unknown_timeframes}")

    combos = [(s, tf) for s in symbols for tf in timeframes]
    print(f"Processing {len(combos)} symbol/timeframe combos")

    run_id = 0 if args.dry_run else start_run(client)
    total_inserted = 0

    for symbol, tf_label in combos:
        inst = instruments[symbol]
        n = ingest_symbol_timeframe(
            client=client,
            symbol=symbol,
            instrument_id=int(inst["instrument_id"]),
            yf_ticker=str(inst["yf_ticker"]),
            tf_label=tf_label,
            timeframe_id=timeframe_map[tf_label],
            run_id=run_id,
            dry_run=args.dry_run,
        )
        total_inserted += n

        if not args.dry_run:
            time.sleep(0.25)

    if not args.dry_run:
        finish_run(client, run_id, total_inserted)
        print(f"\nDone: inserted {total_inserted:,} rows (run_id={run_id})")

    if args.verify or not args.dry_run:
        verify(client)


if __name__ == "__main__":
    main()
