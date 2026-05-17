#!/usr/bin/env python3
"""Direct LEAN library probe using ClickHouse multi-timeframe ES data.

What this script does:
1. Bootstraps LEAN .NET libraries from Research/start.py (pythonnet path).
2. Queries ClickHouse market.market_bars for one symbol across timeframes.
3. Feeds close prices into LEAN indicators per timeframe.
4. Prints indicator readiness and latest values as a sanity test.

This is a direct library call test, not a full LEAN backtest run.
"""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe direct LEAN lib calls with ClickHouse ES multi-timeframe data"
    )
    parser.add_argument("--host", default="localhost", help="ClickHouse host")
    parser.add_argument("--port", type=int, default=9000, help="ClickHouse native TCP port")
    parser.add_argument("--database", default="market", help="ClickHouse database")
    parser.add_argument("--symbol", default="es", help="Instrument symbol in market.instruments")
    parser.add_argument(
        "--timeframes",
        default="5m,1h,1d",
        help="Comma-separated timeframe labels (market.timeframes.label)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3000,
        help="Row limit for the combined result set",
    )
    return parser.parse_args()


def bootstrap_lean(repo_root: Path) -> None:
    """Load LEAN runtime and imports via Research/start.py."""
    start_py = repo_root / "Research" / "start.py"
    if not start_py.exists():
        raise FileNotFoundError(f"LEAN bootstrap file not found: {start_py}")

    # start.py configures pythonnet runtime and imports AlgorithmImports symbols.
    runpy.run_path(str(start_py), run_name="__main__")


def query_clickhouse(
    host: str,
    port: int,
    database: str,
    symbol: str,
    timeframes: Iterable[str],
    limit: int,
) -> pd.DataFrame:
    try:
        from clickhouse_driver import Client
    except ImportError as exc:
        raise RuntimeError(
            "clickhouse-driver is not installed. Install with: pip install clickhouse-driver"
        ) from exc

    tf_tuple = tuple(tf.strip() for tf in timeframes if tf.strip())
    if not tf_tuple:
        raise ValueError("At least one timeframe is required")

    client = Client(host=host, port=port, database=database)
    sql = """
        SELECT
            mb.timestamp AS ts,
            tf.label AS timeframe,
            mb.open,
            mb.high,
            mb.low,
            mb.close,
            mb.volume
        FROM market_bars mb
        INNER JOIN instruments i
            ON i.instrument_id = mb.instrument_id
        INNER JOIN timeframes tf
            ON tf.timeframe_id = mb.timeframe_id
        WHERE i.symbol = %(symbol)s
          AND tf.label IN %(timeframes)s
        ORDER BY mb.timestamp DESC
        LIMIT %(limit)s
    """

    rows = client.execute(
        sql,
        {
            "symbol": symbol,
            "timeframes": tf_tuple,
            "limit": limit,
        },
    )

    if not rows:
        return pd.DataFrame(columns=["ts", "timeframe", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(
        rows,
        columns=["ts", "timeframe", "open", "high", "low", "close", "volume"],
    )
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts", "close"]).sort_values(["timeframe", "ts"]).reset_index(drop=True)
    return df


def run_lean_indicator_test(df: pd.DataFrame) -> list[dict[str, object]]:
    """Feed fetched data into LEAN indicators and report state."""
    if df.empty:
        return []

    # Imported only after bootstrap_lean() has configured pythonnet and LEAN assemblies.
    from QuantConnect.Indicators import IndicatorDataPoint, ExponentialMovingAverage, SimpleMovingAverage

    results: list[dict[str, object]] = []

    for timeframe, tf_df in df.groupby("timeframe"):
        ema20 = ExponentialMovingAverage(20)
        sma20 = SimpleMovingAverage(20)

        for row in tf_df.itertuples(index=False):
            # .NET indicator update with timestamp + close price.
            point = IndicatorDataPoint(row.ts.to_pydatetime(), float(row.close))
            ema20.Update(point)
            sma20.Update(point)

        latest_close = float(tf_df.iloc[-1]["close"])
        results.append(
            {
                "timeframe": timeframe,
                "samples": int(len(tf_df)),
                "latest_close": latest_close,
                "ema20_ready": bool(ema20.IsReady),
                "sma20_ready": bool(sma20.IsReady),
                "ema20": float(ema20.Current.Value) if ema20.IsReady else None,
                "sma20": float(sma20.Current.Value) if sma20.IsReady else None,
            }
        )

    return results


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    timeframes = [tf.strip() for tf in args.timeframes.split(",") if tf.strip()]

    print("== Direct LEAN + ClickHouse Probe ==")
    print(f"Repo root: {repo_root}")
    print(f"DB: {args.database}@{args.host}:{args.port} | symbol={args.symbol} | timeframes={timeframes}")

    try:
        bootstrap_lean(repo_root)
    except Exception as exc:
        print("LEAN bootstrap failed.")
        print(f"Reason: {exc}")
        print("Hint: Build LEAN first so runtimeconfig and assemblies are available.")
        return 2

    try:
        df = query_clickhouse(
            host=args.host,
            port=args.port,
            database=args.database,
            symbol=args.symbol,
            timeframes=timeframes,
            limit=args.limit,
        )
    except Exception as exc:
        print("ClickHouse query failed.")
        print(f"Reason: {exc}")
        return 3

    if df.empty:
        print("No rows returned. Check symbol/timeframes and data coverage.")
        return 4

    print(f"Fetched rows: {len(df)}")
    print(
        "Time span: "
        f"{df['ts'].min().isoformat()} -> {df['ts'].max().isoformat()}"
    )

    try:
        test_results = run_lean_indicator_test(df)
    except Exception as exc:
        print("LEAN indicator test failed.")
        print(f"Reason: {exc}")
        return 5

    print("\nLEAN indicator results:")
    for item in sorted(test_results, key=lambda x: str(x["timeframe"])):
        print(
            f"- tf={item['timeframe']} samples={item['samples']} "
            f"ready(ema/sma)=({item['ema20_ready']}/{item['sma20_ready']}) "
            f"close={item['latest_close']:.4f} "
            f"ema20={item['ema20']} sma20={item['sma20']}"
        )

    print("\nProbe successful: Python directly called LEAN libs with ClickHouse-sourced data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
