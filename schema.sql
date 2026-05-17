-- ============================================================
-- Local Quant Research Database — v1 Schema
-- Engine: ClickHouse 25.x
-- Scope:  raw market data only (yfinance OHLCV)
-- ============================================================

CREATE DATABASE IF NOT EXISTS market;

-- ------------------------------------------------------------
-- Dimension: instruments
-- One row per logical instrument (e.g. "es", "vix", "btc")
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market.instruments (
    instrument_id   UInt16,
    symbol          String,      -- short key: "es", "vix", "btc"
    yf_ticker       String,      -- yfinance ticker: "ES=F", "^VIX"
    asset_class     String,      -- "futures", "fx", "crypto", "etf", "index"
    description     String DEFAULT ''
) ENGINE = ReplacingMergeTree()
ORDER BY instrument_id;

-- ------------------------------------------------------------
-- Dimension: timeframes
-- One row per interval label used in file names
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market.timeframes (
    timeframe_id    UInt8,
    label           String,      -- "5m", "1h", "1d", "1wk", "1mo", "3mo"
    seconds         UInt32,      -- bar duration in seconds (0 = calendar-based)
    is_intraday     UInt8        -- 1 = limited lookback, 0 = full history
) ENGINE = ReplacingMergeTree()
ORDER BY timeframe_id;

-- ------------------------------------------------------------
-- Dimension: data_sources
-- One row per upstream source (yfinance, FRED, …)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market.data_sources (
    source_id       UInt8,
    name            String,      -- "yfinance"
    description     String DEFAULT ''
) ENGINE = ReplacingMergeTree()
ORDER BY source_id;

-- ------------------------------------------------------------
-- Fact: market_bars
-- Core OHLCV table.  ReplacingMergeTree deduplicates on the
-- natural key (instrument, timeframe, timestamp) so re-running
-- the loader never inflates the table.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market.market_bars (
    instrument_id   UInt16,
    timeframe_id    UInt8,
    timestamp       DateTime64(3, 'UTC'),  -- always UTC
    session_date    Date,                  -- calendar date of bar open (for partitioning)
    open            Float64,
    high            Float64,
    low             Float64,
    close           Float64,
    volume          Float64,
    ingestion_run   UInt64 DEFAULT 0       -- FK → ingestion_runs.run_id
) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(session_date)
ORDER BY (instrument_id, timeframe_id, timestamp);

-- ------------------------------------------------------------
-- Operational: ingestion_runs
-- One row per loader execution; used for lineage and audit.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market.ingestion_runs (
    run_id          UInt64,                          -- epoch-ms at run start
    started_at      DateTime64(3, 'UTC'),
    finished_at     DateTime64(3, 'UTC') DEFAULT toDateTime64(0, 3),
    source_id       UInt8,
    status          String DEFAULT 'running',        -- running | done | error
    rows_inserted   UInt64 DEFAULT 0,
    notes           String DEFAULT ''
) ENGINE = ReplacingMergeTree(finished_at)
ORDER BY run_id;

-- ------------------------------------------------------------
-- Operational: data_coverage
-- Tracks which (instrument, timeframe) combos are loaded and
-- whether the history is full or a limited intraday window.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS market.data_coverage (
    instrument_id   UInt16,
    timeframe_id    UInt8,
    source_id       UInt8,
    earliest_ts     DateTime64(3, 'UTC'),
    latest_ts       DateTime64(3, 'UTC'),
    total_bars      UInt64,
    is_partial      UInt8,   -- 1 = limited lookback (5m/1h), 0 = full history
    last_updated    DateTime64(3, 'UTC')
) ENGINE = ReplacingMergeTree(last_updated)
ORDER BY (instrument_id, timeframe_id, source_id);

-- ============================================================
-- Seed dimension tables
-- ============================================================

INSERT INTO market.data_sources (source_id, name, description) VALUES
    (1, 'yfinance', 'Yahoo Finance via yfinance Python library');

INSERT INTO market.timeframes (timeframe_id, label, seconds, is_intraday) VALUES
    (1,  '5m',  300,    1),
    (2,  '1h',  3600,   1),
    (3,  '1d',  86400,  0),
    (4,  '1wk', 604800, 0),
    (5,  '1mo', 0,      0),
    (6,  '3mo', 0,      0);

INSERT INTO market.instruments (instrument_id, symbol, yf_ticker, asset_class) VALUES
    (1,  'vix',    '^VIX',     'index'),
    (2,  'es',     'ES=F',     'futures'),
    (3,  'nq',     'NQ=F',     'futures'),
    (4,  'ym',     'YM=F',     'futures'),
    (5,  'rty',    'RTY=F',    'futures'),
    (6,  'cl',     'CL=F',     'futures'),
    (7,  'gc',     'GC=F',     'futures'),
    (8,  'eurusd', 'EURUSD=X', 'fx'),
    (9,  'gbpusd', 'GBPUSD=X', 'fx'),
    (10, 'usdjpy', 'JPY=X',    'fx'),
    (11, 'btc',    'BTC-USD',  'crypto'),
    (12, 'eth',    'ETH-USD',  'crypto'),
    (13, 'tlt',    'TLT',      'etf'),
    (14, 'ief',    'IEF',      'etf'),
    (15, 'shy',    'SHY',      'etf'),
    (16, 'tnx',    '^TNX',     'index'),
    (17, 'fvx',    '^FVX',     'index'),
    (18, 'nikkei', '^N225',    'index'),
    (19, 'ftse',   '^FTSE',    'index'),
    (20, 'dax',    '^GDAXI',   'index'),
    (21, 'hsi',    '^HSI',     'index');
