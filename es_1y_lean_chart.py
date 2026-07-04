#!/usr/bin/env python3
"""Create a 1-year ES chart using LEAN charting classes.

Outputs (in current working directory):
- es_1y_lean_chart.json
- es_1y_lean_chart.png
- es_1y_lean_chart_data.csv
"""

from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 1-year ES chart with LEAN charting")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--database", default="market")
    parser.add_argument("--symbol", default="es")
    parser.add_argument("--timeframe", default="1d")
    parser.add_argument("--sma", type=int, default=50)
    return parser.parse_args()


def bootstrap_lean(repo_root: Path) -> None:
    start_py = repo_root / "Research" / "start.py"
    if not start_py.exists():
        raise FileNotFoundError(f"LEAN bootstrap file not found: {start_py}")
    runpy.run_path(str(start_py), run_name="__main__")


def load_es_bars(host: str, port: int, database: str, symbol: str, timeframe: str) -> pd.DataFrame:
    from clickhouse_driver import Client

    client = Client(host=host, port=port, database=database)
    sql = """
        SELECT
            mb.timestamp AS ts,
            mb.open,
            mb.high,
            mb.low,
            mb.close,
            mb.volume
        FROM market_bars mb
        INNER JOIN instruments i ON i.instrument_id = mb.instrument_id
        INNER JOIN timeframes tf ON tf.timeframe_id = mb.timeframe_id
        WHERE i.symbol = %(symbol)s
          AND tf.label = %(timeframe)s
        ORDER BY mb.timestamp ASC
    """
    rows = client.execute(sql, {"symbol": symbol, "timeframe": timeframe})
    if not rows:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts", "close"]).drop_duplicates(subset=["ts"]).sort_values("ts")

    end_ts = df["ts"].iloc[-1]
    start_ts = end_ts - pd.Timedelta(days=365)
    df = df[df["ts"] >= start_ts].copy()
    df.reset_index(drop=True, inplace=True)
    return df


def build_lean_chart(df: pd.DataFrame, sma_period: int):
    from QuantConnect import CandlestickSeries, Chart, Series, SeriesType
    from QuantConnect.Indicators import IndicatorDataPoint, SimpleMovingAverage

    chart = Chart("ES 1Y")
    candles = CandlestickSeries("ES", 0, "$")
    sma_series = Series(f"SMA{sma_period}", SeriesType.Line, 0, "$")
    chart.AddSeries(candles)
    chart.AddSeries(sma_series)

    sma = SimpleMovingAverage(sma_period)
    sma_values = []

    for row in df.itertuples(index=False):
        ts = row.ts.to_pydatetime().replace(tzinfo=None)
        o = float(row.open)
        h = float(row.high)
        l = float(row.low)
        c = float(row.close)

        candles.AddPoint(ts, o, h, l, c)
        sma.Update(IndicatorDataPoint(ts, c))
        if sma.IsReady:
            sma_v = float(sma.Current.Value)
            sma_series.AddPoint(ts, sma_v)
            sma_values.append(sma_v)
        else:
            sma_values.append(float("nan"))

    candles_payload = []
    for p in candles.Values:
        candles_payload.append(
            {
                "x": int(p.LongTime),
                "open": float(p.Open) if p.Open is not None else None,
                "high": float(p.High) if p.High is not None else None,
                "low": float(p.Low) if p.Low is not None else None,
                "close": float(p.Close) if p.Close is not None else None,
            }
        )

    sma_payload = []
    for p in sma_series.Values:
        sma_payload.append(
            {
                "x": int(p.x),
                "y": float(p.y) if p.y is not None else None,
            }
        )

    payload = {
        "chartName": "ES 1Y",
        "bars": int(len(df)),
        "start": df["ts"].iloc[0].isoformat(),
        "end": df["ts"].iloc[-1].isoformat(),
        "series": {
            "ES": {
                "type": "Candle",
                "points": candles_payload,
            },
            f"SMA{sma_period}": {
                "type": "Line",
                "points": sma_payload,
            },
        },
    }
    chart_json = json.dumps(payload, indent=2)
    return chart_json, sma_values


def save_png(df: pd.DataFrame, sma_values: list[float], out_path: Path, sma_period: int) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df["ts"], df["close"], label="ES Close", linewidth=1.2)
    ax.plot(df["ts"], sma_values, label=f"SMA{sma_period}", linewidth=1.4)
    ax.set_title("ES 1-Year Chart (LEAN data + LEAN SMA)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent

    try:
        bootstrap_lean(repo_root)
    except Exception as exc:
        print(f"LEAN bootstrap failed: {exc}")
        return 2

    try:
        df = load_es_bars(args.host, args.port, args.database, args.symbol, args.timeframe)
    except Exception as exc:
        print(f"ClickHouse read failed: {exc}")
        return 3

    if df.empty:
        print("No data returned for requested symbol/timeframe")
        return 4

    try:
        chart_json, sma_values = build_lean_chart(df, args.sma)
    except Exception as exc:
        print(f"LEAN chart creation failed: {exc}")
        return 5

    out_dir = Path.cwd()
    json_path = out_dir / "es_1y_lean_chart.json"
    png_path = out_dir / "es_1y_lean_chart.png"
    csv_path = out_dir / "es_1y_lean_chart_data.csv"

    json_path.write_text(chart_json, encoding="utf-8")
    df_out = df.copy()
    df_out[f"sma_{args.sma}"] = sma_values
    df_out.to_csv(csv_path, index=False)

    try:
        save_png(df_out, sma_values, png_path, args.sma)
    except Exception as exc:
        print(f"PNG export warning: {exc}")

    print("Created LEAN chart artifacts:")
    print(f"- {json_path}")
    print(f"- {png_path}")
    print(f"- {csv_path}")
    print(f"Bars: {len(df_out)}")
    print(f"Range: {df_out['ts'].iloc[0].isoformat()} -> {df_out['ts'].iloc[-1].isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
