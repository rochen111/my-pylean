## Plan: Local Quant Research Database

Build a Python-first platform around ClickHouse as the primary local analytical database. Keep LEAN out of scope for v1. V1 focuses exclusively on ingesting and storing raw multi-asset, multi-timeframe market data produced by `get_sp500_all_timeframes_yfinance.py` into a canonical ClickHouse schema. Feature research, optimization, and Monte Carlo support are deferred to later stages. ClickHouse is the right foundation because it stays local, handles concurrent readers/writers better than lighter embedded options, and is far better suited than flat files for multi-asset, multi-timeframe analytical queries.

**Steps**
1. Lock the scope: v1 is raw market data ingestion only — no features, optimization, or simulation yet. LEAN integration is explicitly out of scope.
2. Standardize the stack: ClickHouse for core storage/querying, Python for ETL/orchestration, Parquet for export/archive, optional DuckDB later for notebook-only ad hoc analysis.
3. Run `get_sp500_all_timeframes_yfinance.py` to produce the per-instrument, per-timeframe CSV files that feed the ClickHouse ingestion pipeline.
4. Build a source registry keyed by source, symbol, timeframe, filename pattern, schema version, timestamp semantics, and provenance.
5. Design canonical tables for `instruments`, `timeframes`, `data_sources`, `market_bars`, `market_closes`, `ingestion_runs`, `data_coverage`, `data_quality_events`, and proxy/provenance metadata.
6. Design the ClickHouse physical layout with MergeTree tables partitioned by time and ordered by `(instrument_id, timeframe_id, timestamp)`.
7. Add versioned/idempotent ingestion so reruns do not duplicate logical bars, but restated bars can replace stale ones.
8. Implement Python loaders for the yfinance CSV outputs and normalize naming quirks (`60m` stored as `1h` in filenames, timezone-aware intraday timestamps vs date-only daily/weekly/monthly timestamps) into the canonical schema. Reference `get_sp500_all_timeframes_yfinance.py` for exact filename patterns and interval rules.
9. Run the ingestion pipeline for all instruments and timeframes and confirm the DB is queryable end-to-end.

**Later Stages (v2+)**
- Add background job orchestration for scheduled ingestion, backfill, and safe concurrency across multiple Python workers.
- Create derived feature layers for indicators, rolling windows, regimes, and multi-timeframe joins with versioned computation metadata.
- Design experiment/result tables for optimization runs, walk-forward windows, parameter sets, trades, fills, positions, equity curves, drawdowns, and portfolio snapshots.
- Model walk-forward optimization with persisted train/validate/test windows and separate in-sample vs out-of-sample results.
- Model Monte Carlo with simulation definitions, random seeds, perturbation methods, and output distribution storage.
- Expose a Python query layer for bar retrieval, multi-timeframe alignment, trade drilldown, portfolio reconstruction, and experiment comparison.

**Relevant files**
- [get_sp500_all_timeframes_yfinance.py](/home/jyck613/dev/my-pylean/get_sp500_all_timeframes_yfinance.py) — current multi-instrument incremental yfinance source and naming rules.

**Verification (v1)**
1. Verify that row counts, timestamp ranges, and OHLCV values written to ClickHouse match the output of running `get_sp500_all_timeframes_yfinance.py` for a representative instrument/timeframe pair.
2. Benchmark single-symbol full-history range reads, multi-asset daily cross-sectional scans, and a multi-timeframe join against the loaded schema.
3. Rerun the ingestion pipeline on already-loaded data and confirm no duplicate rows are created.
4. Confirm coverage metadata correctly flags partial intraday history (`5m`, `1h`) vs full-history intervals (`1d`, `1wk`, `1mo`, `3mo`).

**Verification (v2)**
5. Load one strategy result sample and verify both trade-level drilldown and portfolio/equity reconstruction are queryable.
6. Stress-test multiple Python workers reading and writing concurrently against the same local ClickHouse instance.
7. Export a subset to Parquet, reload it, and confirm counts and version markers match.

**Decisions**
- Recommended database: ClickHouse.
- Recommended orchestration: Python-first.
- Included in v1: raw market data ingestion from yfinance into ClickHouse only.
- Excluded from v1: feature research, optimization metadata, Monte Carlo outputs, drilldown-friendly strategy results, LEAN integration, live trading, and a full UI/dashboard.
- Design principle: raw data should be immutable or logically versioned; derived indicators and experiments must be reproducible.

**Next steps**
- Produce the target ClickHouse schema design for v1 (tables, partition keys, MergeTree engine settings).
- Write the Python ingestion loader that reads yfinance CSV outputs and bulk-inserts into ClickHouse.
