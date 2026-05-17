# My-PyLEAN Technical Stack

This document describes the current working stack for:
- yfinance data extraction and injection into ClickHouse
- ClickHouse schema and high-value queries
- LEAN container runtime specs
- Direct LEAN engine-library backtesting/probing from Python
- Full engine-style rendering pipeline

## 1) End-to-End Architecture

1. Market data is pulled directly from yfinance for each symbol/timeframe.
2. Bars are written directly into ClickHouse database market.
3. Backtest/probe scripts query market.market_bars joined with instruments and timeframes.
4. LEAN runtime is loaded from container binaries in /Lean/Launcher/bin/Debug.
5. Strategy metrics and visuals are rendered into:
   - es_ma_crossover_results.json
   - es_ma_crossover_equity_curve.csv
   - es_backtest_report.html

## 2) yfinance Direct Inject

Source implementation:
- ingest_to_clickhouse.py

Supported timeframe labels:
- 5m, 1h, 1d, 1wk, 1mo, 3mo

Internal yfinance interval mapping:
- 5m -> 5m
- 1h -> 60m
- 1d -> 1d
- 1wk -> 1wk
- 1mo -> 1mo
- 3mo -> 3mo

### 2.1 Injection Commands

```bash
python3 ingest_to_clickhouse.py
python3 ingest_to_clickhouse.py --verify
python3 ingest_to_clickhouse.py --dry-run
python3 ingest_to_clickhouse.py --symbols es,nq --timeframes 1d,1wk
```

Implementation details:
- Data is fetched directly from yfinance, then normalized in-memory.
- Ingest is append-only by watermark (max existing timestamp per symbol/timeframe).
- Storage uses ReplacingMergeTree, keyed by:
  - instrument_id, timeframe_id, timestamp
- data_coverage is refreshed from actual table state (min/max/count after ingest).
- ingestion_runs records lineage/observability for each run.

## 3) ClickHouse Tables

Schema file:
- schema.sql

Primary tables:
- market.instruments
  - symbol to instrument_id mapping
- market.timeframes
  - timeframe labels and metadata
- market.data_sources
  - source registry (yfinance source_id=1)
- market.market_bars
  - OHLCV fact table in UTC
- market.ingestion_runs
  - loader audit/log table
- market.data_coverage
  - earliest/latest coverage per symbol/timeframe/source

## 4) Queries to Use

### 4.1 Coverage by Symbol and Timeframe

```sql
SELECT
    tf.label,
    count(*) AS cnt,
    min(mb.timestamp) AS earliest,
    max(mb.timestamp) AS latest
FROM market_bars mb
JOIN instruments i ON i.instrument_id = mb.instrument_id
JOIN timeframes tf ON tf.timeframe_id = mb.timeframe_id
WHERE i.symbol = 'es'
GROUP BY tf.label
ORDER BY tf.label;
```

### 4.2 Earliest/Latest for ES Daily

```sql
SELECT
    min(mb.timestamp) AS earliest,
    max(mb.timestamp) AS latest,
    count(*) AS bars
FROM market_bars mb
JOIN instruments i ON i.instrument_id = mb.instrument_id
JOIN timeframes tf ON tf.timeframe_id = mb.timeframe_id
WHERE i.symbol = 'es'
  AND tf.label = '1d';
```

### 4.3 Backtest Input Query Pattern

```sql
SELECT
    mb.timestamp AS ts,
    mb.open,
    mb.high,
    mb.low,
    mb.close,
    mb.volume
FROM market_bars mb
JOIN instruments i ON i.instrument_id = mb.instrument_id
JOIN timeframes tf ON tf.timeframe_id = mb.timeframe_id
WHERE i.symbol = %(symbol)s
  AND tf.label = %(timeframe)s
ORDER BY mb.timestamp ASC;
```

## 5) LEAN Container Specs

Current image:
- my-pylean-jupyter

Base image and build source:
- DockerfileJupyter
- FROM quantconnect/lean:latest

Important runtime facts:
- LEAN runtime binaries: /Lean/Launcher/bin/Debug
- start.py bootstrap source: /Lean/Launcher/bin/Debug/start.py
- Runtime config: QuantConnect.Lean.Launcher.runtimeconfig.json
- .NET runtime in container is aligned to LEAN base image (currently .NET 10 in this setup).

Operational wrapper scripts:
- run_probe_in_docker.sh
  - Runs direct LEAN library probe + ClickHouse query feed
- run_es_ma_backtest_in_docker.sh
  - Runs MA crossover backtest and copies output artifacts back to host

Common run patterns:

```bash
./run_probe_in_docker.sh --limit 50
./run_es_ma_backtest_in_docker.sh
```

## 6) Sample Code: Backtesting with LEAN Engine Libraries

This project has two useful modes:

1) Direct LEAN library probe (pythonnet + indicator update):
- direct_lean_clickhouse_probe.py

Minimal LEAN indicator feed example:

```python
from QuantConnect.Indicators import IndicatorDataPoint, ExponentialMovingAverage, SimpleMovingAverage

ema20 = ExponentialMovingAverage(20)
sma20 = SimpleMovingAverage(20)

for row in bars_df.itertuples(index=False):
    point = IndicatorDataPoint(row.ts.to_pydatetime(), float(row.close))
    ema20.Update(point)
    sma20.Update(point)

print(ema20.IsReady, ema20.Current.Value)
print(sma20.IsReady, sma20.Current.Value)
```

2) Strategy-style backtest engine in Python against ClickHouse bars:
- es_ma_crossover_clickhouse_backtest.py
- es_ma_backtest_full_report.py

Core strategy mechanics:
- MA50/MA200 crossover
- Signal:
  - fast_ma > slow_ma => long
- Execution:
  - position is signal shifted by 1 bar (next-bar execution assumption)
- Returns:
  - strategy_return = position * close_pct_change

## 7) Final Rendering Stack

Renderer script:
- es_ma_backtest_full_report.py

Rendering libraries:
- pandas
- numpy
- matplotlib (Agg backend)
- HTML/CSS assembled as single file with embedded base64 PNG charts

Generated report:
- es_backtest_report.html

Report sections:
- Equity curve (strategy vs buy-and-hold with entry/exit markers)
- Drawdown chart
- Price + moving averages chart
- Performance summary table (CAGR, Sharpe, Sortino, Calmar, Alpha, Profit Factor, Exposure)
- Annual returns chart
- Monthly returns heatmap
- Annual returns table

Run command:

```bash
python3 es_ma_backtest_full_report.py --symbol es --timeframe 1d --fast 50 --slow 200 --initial-cash 100000
```

## 8) Current Known Data Reality (ES Daily)

At present, ES daily bars in ClickHouse are:
- earliest: 2000-09-18
- latest: 2026-05-15
- count: 6479

If pre-2000 ES history is desired, ingest additional source history and rerun ingestion.

## 9) Dependency Set

Python packages used by ingestion/backtest/report:
- clickhouse-driver
- pandas
- numpy
- matplotlib
- yfinance (direct ingestion stage)

Container notes:
- pythonnet/clr-loader behavior depends on LEAN base image runtime alignment.
- Existing wrapper scripts already patch/bootstrap required LEAN startup components for probe workflows.
