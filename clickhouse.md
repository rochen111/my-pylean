# ClickHouse Technical Specification

## 1) Purpose in This Project

ClickHouse is the market data backbone for this pipeline:
- yfinance -> ClickHouse (direct ingestion)
- ClickHouse -> LEAN probe/backtest scripts
- ClickHouse -> analytics and reporting queries

In this repository, ClickHouse stores normalized OHLCV bars in the market database and serves all historical queries used by:
- ingest_to_clickhouse.py
- direct_lean_clickhouse_probe.py
- es_ma_crossover_clickhouse_backtest.py
- es_ma_backtest_full_report.py

## 2) Installation

### 2.1 Debian/Ubuntu (native install)

```bash
sudo apt update
sudo apt install -y clickhouse-server clickhouse-client
```

Validate binaries:

```bash
which clickhouse-server
which clickhouse-client
```

Expected paths on this machine:
- server: /usr/bin/clickhouse-server
- client: /usr/bin/clickhouse-client
- config: /etc/clickhouse-server/config.xml
- data root: /var/lib/clickhouse
- logs: /var/log/clickhouse-server

### 2.2 Python client dependencies

```bash
python3 -m pip install clickhouse-driver pandas yfinance
```

## 3) Running and Service Operations

Start and enable service:

```bash
sudo systemctl enable clickhouse-server
sudo systemctl start clickhouse-server
```

Check status:

```bash
sudo systemctl status clickhouse-server
```

Tail logs:

```bash
sudo tail -f /var/log/clickhouse-server/clickhouse-server.log
```

Connect using native client:

```bash
clickhouse-client --host localhost --port 9000 --database market
```

## 4) Schema and Data Model

Schema source:
- schema.sql

Main tables in market:
- instruments: symbol metadata and yfinance ticker mapping
- timeframes: bar interval definitions
- data_sources: source catalog (yfinance)
- market_bars: OHLCV fact table (UTC timestamps)
- ingestion_runs: ingestion lineage and run metadata
- data_coverage: min/max/count coverage by symbol and timeframe

Storage engine notes:
- market_bars uses ReplacingMergeTree
- ORDER BY key: instrument_id, timeframe_id, timestamp
- Partition key: toYYYYMM(session_date)

This layout supports high-performance point/range scans by symbol + timeframe + time window.

## 5) Ingestion in Current Scenario

Current ingestion mode is direct (no CSV stage):
- yfinance fetch in memory
- normalization to canonical OHLCV schema
- incremental insert by watermark (max timestamp in market_bars)

Script:
- ingest_to_clickhouse.py

Typical commands:

```bash
python3 ingest_to_clickhouse.py
python3 ingest_to_clickhouse.py --verify
python3 ingest_to_clickhouse.py --dry-run
python3 ingest_to_clickhouse.py --symbols es,nq --timeframes 1d,1wk
```

## 6) Querying Patterns

### 6.1 Coverage and health

```sql
SELECT
    i.symbol,
    tf.label,
    dc.total_bars,
    dc.earliest_ts,
    dc.latest_ts,
    dc.is_partial
FROM data_coverage dc
JOIN instruments i ON i.instrument_id = dc.instrument_id
JOIN timeframes tf ON tf.timeframe_id = dc.timeframe_id
ORDER BY i.symbol, tf.timeframe_id;
```

### 6.2 ES daily range verification

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

### 6.3 Backtest feed query

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
WHERE i.symbol = 'es'
  AND tf.label = '1d'
ORDER BY mb.timestamp ASC;
```

## 7) Real-Time Analytics Approaches

This project currently runs primarily historical and near-real-time batch analytics. For real-time expansion, use these ClickHouse patterns.

### 7.1 Sliding-window analytics on latest bars

Example: intraday rolling return and volatility.

```sql
SELECT
    mb.timestamp,
    mb.close,
    (mb.close / lagInFrame(mb.close, 1) OVER w - 1) AS ret_1,
    stddevPop((mb.close / lagInFrame(mb.close, 1) OVER w - 1)) OVER w AS rolling_vol
FROM market_bars mb
JOIN instruments i ON i.instrument_id = mb.instrument_id
JOIN timeframes tf ON tf.timeframe_id = mb.timeframe_id
WHERE i.symbol = 'es'
  AND tf.label = '5m'
WINDOW w AS (ORDER BY mb.timestamp ROWS BETWEEN 100 PRECEDING AND CURRENT ROW)
ORDER BY mb.timestamp DESC
LIMIT 500;
```

### 7.2 Materialized views for pre-aggregation

Use Materialized Views for low-latency aggregates, for example:
- per symbol/timeframe latest bar snapshot
- per symbol daily return aggregates
- per hour liquidity/volume summaries

Recommended target engines:
- SummingMergeTree for additive metrics
- AggregatingMergeTree for aggregate states

### 7.3 Stream ingestion option

If you need continuous market feed ingestion, integrate:
- Kafka/RabbitMQ -> ClickHouse Kafka engine table -> Materialized View -> market_bars or aggregate table

## 8) Performance and Operational Guidelines

Query and storage best practices:
- Always filter by symbol and timeframe in joins.
- Keep timestamp filters explicit for large scans.
- Use ascending ORDER BY for backtests, descending for latest-data dashboards.
- Prefer typed joins via instrument_id/timeframe_id over string-only filters in large workloads.

MergeTree and maintenance:
- Avoid frequent tiny inserts where possible; batch inserts by symbol/timeframe.
- Monitor part counts and background merges.
- Keep partitions aligned to query patterns (monthly partition is suitable for this dataset).

Monitoring checks:

```sql
SELECT database, table, sum(rows) AS rows, sum(bytes_on_disk) AS bytes
FROM system.parts
WHERE active
  AND database = 'market'
GROUP BY database, table
ORDER BY bytes DESC;
```

```sql
SELECT event_time, query_duration_ms, read_rows, result_rows, query
FROM system.query_log
WHERE type = 'QueryFinish'
  AND event_time > now() - INTERVAL 15 MINUTE
ORDER BY event_time DESC
LIMIT 50;
```

## 9) How ClickHouse Is Used Right Now

Current scenario in this repository:
1. Direct yfinance ingestion updates market_bars.
2. data_coverage is refreshed to track earliest/latest/bars.
3. LEAN probe script reads bars and updates LEAN indicators via pythonnet.
4. MA crossover backtest reads the full ES daily history from ClickHouse.
5. Full engine-style report is rendered from query results and computed metrics.

Practical outcome:
- ClickHouse is the single source of truth for market history.
- LEAN-related strategy research is decoupled from raw data acquisition.
- Backtest reproducibility depends on database state, not local CSV artifacts.

## 10) Quick Troubleshooting

Connection issues:
- Verify service is running with systemctl status.
- Verify native port 9000 is reachable.
- Verify database exists: SHOW DATABASES.

No data returned:
- Check instrument symbol exists in instruments table.
- Check timeframe label exists in timeframes table.
- Validate ingestion with --verify and coverage queries.

Slow queries:
- Add symbol/timeframe/time range filters.
- Confirm query is using ORDER BY-aligned predicates.
- Inspect query_log and active parts.
