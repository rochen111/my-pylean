#!/usr/bin/env python3
"""Run an ES daily 50/200 MA crossover backtest from ClickHouse data using LEAN indicators.

Outputs:
- es_ma_crossover_equity_curve.csv
- es_ma_crossover_results.json
"""

from __future__ import annotations

import argparse
import json
import math
import runpy
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class BacktestConfig:
    host: str
    port: int
    database: str
    symbol: str
    timeframe: str
    fast: int
    slow: int
    initial_cash: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ES MA crossover backtest from ClickHouse (LEAN indicators)")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--database", default="market")
    parser.add_argument("--symbol", default="es")
    parser.add_argument("--timeframe", default="1d")
    parser.add_argument("--fast", type=int, default=50)
    parser.add_argument("--slow", type=int, default=200)
    parser.add_argument("--initial-cash", type=float, default=100000.0)
    return parser.parse_args()


def bootstrap_lean(repo_root: Path) -> None:
    """Load LEAN runtime and imports via Research/start.py."""
    start_py = repo_root / "Research" / "start.py"
    if not start_py.exists():
        raise FileNotFoundError(f"LEAN bootstrap file not found: {start_py}")

    # start.py configures pythonnet runtime and imports AlgorithmImports symbols.
    runpy.run_path(str(start_py), run_name="__main__")


def load_daily_bars(cfg: BacktestConfig) -> pd.DataFrame:
    from clickhouse_driver import Client

    client = Client(host=cfg.host, port=cfg.port, database=cfg.database)
    sql = """
        SELECT
            mb.timestamp AS ts,
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
          AND tf.label = %(timeframe)s
        ORDER BY mb.timestamp ASC
    """
    rows = client.execute(sql, {"symbol": cfg.symbol, "timeframe": cfg.timeframe})

    if not rows:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts", "close"]).drop_duplicates(subset=["ts"]).sort_values("ts")
    df = df.reset_index(drop=True)
    return df


def compute_lean_mas(data: pd.DataFrame, fast: int, slow: int) -> tuple[pd.Series, pd.Series]:
    """Compute moving averages by feeding close prices into LEAN SMA indicators."""
    from QuantConnect.Indicators import IndicatorDataPoint, SimpleMovingAverage

    fast_sma = SimpleMovingAverage(fast)
    slow_sma = SimpleMovingAverage(slow)

    fast_values: list[float] = []
    slow_values: list[float] = []

    for row in data.itertuples(index=False):
        point = IndicatorDataPoint(row.ts.to_pydatetime(), float(row.close))
        fast_sma.Update(point)
        slow_sma.Update(point)

        fast_values.append(float(fast_sma.Current.Value) if fast_sma.IsReady else math.nan)
        slow_values.append(float(slow_sma.Current.Value) if slow_sma.IsReady else math.nan)

    return pd.Series(fast_values), pd.Series(slow_values)


def build_equity_curve(df: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    data = df.copy()
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna(subset=["close"]).reset_index(drop=True)

    fast_ma, slow_ma = compute_lean_mas(data, cfg.fast, cfg.slow)
    data["fast_ma"] = fast_ma
    data["slow_ma"] = slow_ma

    raw_signal = (data["fast_ma"] > data["slow_ma"]).astype(int)
    data["position"] = raw_signal.shift(1).fillna(0)

    data["asset_return"] = data["close"].pct_change().fillna(0.0)
    data["strategy_return"] = data["position"] * data["asset_return"]

    data["equity"] = cfg.initial_cash * (1.0 + data["strategy_return"]).cumprod()
    data["benchmark_equity"] = cfg.initial_cash * (1.0 + data["asset_return"]).cumprod()
    data["drawdown"] = data["equity"] / data["equity"].cummax() - 1.0

    return data


def annualized_return(total_return: float, periods: int) -> float:
    years = periods / 252.0
    if years <= 0:
        return 0.0
    return (1.0 + total_return) ** (1.0 / years) - 1.0


def summarize(data: pd.DataFrame, cfg: BacktestConfig) -> dict[str, float | int | str]:
    if data.empty:
        return {}

    strategy_rets = data["strategy_return"]

    total_return = float(data["equity"].iloc[-1] / cfg.initial_cash - 1.0)
    bench_total_return = float(data["benchmark_equity"].iloc[-1] / cfg.initial_cash - 1.0)

    cagr = annualized_return(total_return, len(data))
    bench_cagr = annualized_return(bench_total_return, len(data))

    vol = float(strategy_rets.std(ddof=0) * math.sqrt(252.0)) if len(strategy_rets) > 1 else 0.0
    downside = strategy_rets[strategy_rets < 0]
    downside_vol = float(downside.std(ddof=0) * math.sqrt(252.0)) if len(downside) > 1 else 0.0

    mean_daily = float(strategy_rets.mean()) if len(strategy_rets) else 0.0
    sharpe = (mean_daily * 252.0 / vol) if vol > 0 else 0.0
    sortino = (mean_daily * 252.0 / downside_vol) if downside_vol > 0 else 0.0

    max_dd = float(data["drawdown"].min())
    exposure = float(data["position"].mean())

    turnover = data["position"].diff().abs().fillna(0)
    entries = int((turnover == 1).sum())
    exits = int(((data["position"].shift(1) == 1) & (data["position"] == 0)).sum())

    wins = float(strategy_rets[strategy_rets > 0].sum())
    losses = float(strategy_rets[strategy_rets < 0].sum())
    profit_factor = (wins / abs(losses)) if losses < 0 else 0.0

    return {
        "Engine": "LEAN Indicators",
        "Symbol": cfg.symbol,
        "Timeframe": cfg.timeframe,
        "Start": data["ts"].iloc[0].isoformat(),
        "End": data["ts"].iloc[-1].isoformat(),
        "DataPoints": int(len(data)),
        "InitialCapital": cfg.initial_cash,
        "FinalEquity": float(data["equity"].iloc[-1]),
        "TotalNetProfitPct": total_return * 100.0,
        "CagrPct": cagr * 100.0,
        "BenchmarkReturnPct": bench_total_return * 100.0,
        "BenchmarkCagrPct": bench_cagr * 100.0,
        "MaxDrawdownPct": max_dd * 100.0,
        "VolatilityPct": vol * 100.0,
        "SharpeRatio": sharpe,
        "SortinoRatio": sortino,
        "ExposurePct": exposure * 100.0,
        "ProfitFactor": profit_factor,
        "WinningDaysPct": float((strategy_rets > 0).mean() * 100.0),
        "LosingDaysPct": float((strategy_rets < 0).mean() * 100.0),
        "TradeEntries": entries,
        "TradeExits": exits,
        "MaFast": cfg.fast,
        "MaSlow": cfg.slow,
    }


def main() -> int:
    args = parse_args()
    cfg = BacktestConfig(
        host=args.host,
        port=args.port,
        database=args.database,
        symbol=args.symbol,
        timeframe=args.timeframe,
        fast=args.fast,
        slow=args.slow,
        initial_cash=args.initial_cash,
    )

    if cfg.fast >= cfg.slow:
        raise ValueError("fast MA period must be smaller than slow MA period")

    repo_root = Path(__file__).resolve().parent

    try:
        bootstrap_lean(repo_root)
    except Exception as exc:
        print("LEAN bootstrap failed.")
        print(f"Reason: {exc}")
        print("Hint: build LEAN and ensure Research/start.py is available in your runtime image.")
        return 2

    try:
        df = load_daily_bars(cfg)
    except Exception as exc:
        print("ClickHouse query failed.")
        print(f"Reason: {exc}")
        return 3

    if df.empty:
        print("No rows returned from ClickHouse for requested symbol/timeframe")
        return 4

    try:
        data = build_equity_curve(df, cfg)
    except Exception as exc:
        print("LEAN indicator backtest execution failed.")
        print(f"Reason: {exc}")
        return 5

    summary = summarize(data, cfg)

    out_dir = Path.cwd()
    curve_path = out_dir / "es_ma_crossover_equity_curve.csv"
    summary_path = out_dir / "es_ma_crossover_results.json"

    data[["ts", "close", "fast_ma", "slow_ma", "position", "equity", "benchmark_equity", "drawdown"]].to_csv(curve_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("== LEAN-indicator Backtest Rundown ==")
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:.6f}")
        else:
            print(f"{key}: {value}")

    print(f"\nSaved: {curve_path}")
    print(f"Saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
