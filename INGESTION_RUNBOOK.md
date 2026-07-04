# Ingestion Runbook

This runbook is the repeatable operations guide for keeping ClickHouse market data current using:
- [ingest_to_clickhouse.py](ingest_to_clickhouse.py)

Scope:
- Direct yfinance -> ClickHouse ingestion
- Full refresh and targeted refresh
- Verification and freshness checks
- Common issue handling

## 1) Preconditions

1. ClickHouse server is running and reachable.
2. Database and schema exist (market + core tables from [schema.sql](schema.sql)).
3. Python deps are installed in your active environment:

```bash
python3 -m pip install clickhouse-driver pandas yfinance
```

4. You are in repo root:

```bash
cd /home/jyck613/dev/my-pylean
```

## 2) What the Ingestion Script Does

[ingest_to_clickhouse.py](ingest_to_clickhouse.py) performs:
- Pull bars directly from yfinance (no CSV staging)
- Normalize columns/timestamps
- Insert only new bars by watermark (max timestamp per symbol/timeframe)
- Update coverage metadata (earliest/latest/count)

Supported timeframes:
- 5m, 1h, 1d, 1wk, 1mo, 3mo

yfinance interval mapping:
- 5m -> 5m
- 1h -> 60m
- 1d -> 1d
- 1wk -> 1wk
- 1mo -> 1mo
- 3mo -> 3mo

## 3) Standard Operating Procedures

### 3.1 Full Daily Refresh (all instruments, all timeframes)

```bash
python3 ingest_to_clickhouse.py
```

Use this as your default daily run.

### 3.2 Verify Coverage Only (read-only)

```bash
python3 ingest_to_clickhouse.py --verify
```

Shows:
- symbol
- timeframe
- total bars
- earliest
- latest
- partial flag (intraday windows)

### 3.3 Dry Run (no writes)

```bash
python3 ingest_to_clickhouse.py --dry-run
```

Useful before large refreshes or script changes.

### 3.4 Targeted Refresh (specific symbols/timeframes)

```bash
python3 ingest_to_clickhouse.py --symbols es,nq,sp500,djia --timeframes 1d,1wk
```

Examples:

```bash
python3 ingest_to_clickhouse.py --symbols es --timeframes 5m,1h,1d
python3 ingest_to_clickhouse.py --symbols btc,eth --timeframes 5m,1h,1d,1wk
python3 ingest_to_clickhouse.py --symbols sp500,djia --timeframes 1d,1wk,1mo
```

## 4) Freshness Verification Queries

Connect:

```bash
clickhouse-client --host localhost --port 9000 --database market
```

### 4.1 Coverage by Symbol/Timeframe

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

### 4.2 Daily Freshness Check (latest per symbol)

```sql
SELECT
    i.symbol,
    max(mb.timestamp) AS latest_1d
FROM market_bars mb
JOIN instruments i ON i.instrument_id = mb.instrument_id
JOIN timeframes tf ON tf.timeframe_id = mb.timeframe_id
WHERE tf.label = '1d'
GROUP BY i.symbol
ORDER BY i.symbol;
```

### 4.3 Timeframe Freshness Summary

```sql
SELECT
    tf.label,
    min(mb.timestamp) AS earliest,
    max(mb.timestamp) AS latest,
    count() AS bars
FROM market_bars mb
JOIN timeframes tf ON tf.timeframe_id = mb.timeframe_id
GROUP BY tf.label
ORDER BY tf.label;
```

## 5) Instrument Management

List configured instruments:

```sql
SELECT instrument_id, symbol, yf_ticker, asset_class
FROM instruments
ORDER BY instrument_id;
```

Add a new instrument:

```sql
INSERT INTO instruments (instrument_id, symbol, yf_ticker, asset_class, description)
VALUES (24, 'new_symbol', 'TICKER', 'index', 'optional note');
```

After insert, run targeted ingestion:

```bash
python3 ingest_to_clickhouse.py --symbols new_symbol --timeframes 1d,1wk,1mo
```

## 6) Scheduling (Repeatable Ops)

### 6.1 Cron Example (daily at 18:30 local)

```cron
30 18 * * * cd /home/jyck613/dev/my-pylean && /usr/bin/python3 ingest_to_clickhouse.py >> /home/jyck613/dev/my-pylean/ingestion.log 2>&1
```

### 6.2 Suggested cadence

1. Daily full refresh: once after market close.
2. Optional intraday refresh: every 30-60 minutes for 5m/1h if needed.
3. Daily verify: run --verify and alert on stale latest dates.

## 7) Troubleshooting Playbook

### 7.1 "No data returned"

Checks:
1. Instrument exists in instruments table.
2. yfinance ticker is correct.
3. Timeframe label is one of supported labels.
4. Network/proxy access to Yahoo is available.

### 7.2 Data seems stale

1. Run targeted refresh for affected symbol/timeframe.
2. Check latest timestamp with SQL in section 4.
3. Confirm market calendar reality (week/month/quarter bars update on boundary).

### 7.3 Duplicate-looking coverage rows

The coverage table uses ReplacingMergeTree semantics. Temporary duplicate-looking rows can appear before merges collapse versions.

Operational note:
- Treat latest values as authoritative after merges.
- Base analytics on market_bars, not raw duplicate rows in coverage snapshots.

### 7.4 Intraday limits on yfinance

Expected behavior:
- 5m and 1h are limited lookback windows.
- This is why is_partial is set for intraday labels.

### 7.5 CPU overload errors from ClickHouse

The ingestion script retries on overload.
If persistent:
1. Run in smaller targeted batches.
2. Reduce concurrent load on server.
3. Retry after background merges settle.

## 8) Recovery and Re-run Strategy

If a run fails mid-way:
1. Re-run the same command.
2. Watermark logic prevents duplicate inserts.
3. Run --verify after completion.

If a symbol needs full rebuild:
1. Delete symbol/timeframe bars from market_bars.
2. Re-run targeted ingestion for that symbol/timeframe.

## 9) Operator Checklist

Daily checklist:
1. Run full ingestion.
2. Run verify.
3. Confirm latest daily bars are current for critical symbols (es, nq, sp500, djia, tnx, fvx).
4. Investigate any symbol/timeframe lagging unexpectedly.

Weekly checklist:
1. Review total row growth.
2. Confirm new instruments are represented in coverage.
3. Validate backtest-critical symbols freshness before strategy runs.

## 10) Quick Commands Reference

```bash
# Full refresh
python3 ingest_to_clickhouse.py

# Verify only
python3 ingest_to_clickhouse.py --verify

# Dry-run
python3 ingest_to_clickhouse.py --dry-run

# Targeted refresh
python3 ingest_to_clickhouse.py --symbols es,nq,sp500,djia --timeframes 1d,1wk,1mo

# Intraday-focused refresh
python3 ingest_to_clickhouse.py --symbols es,nq,cl,gc --timeframes 5m,1h
```
