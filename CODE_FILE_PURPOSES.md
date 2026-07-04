# Code File Purposes

This document outlines what each non-PyLean, repo-owned code file in this repository is used for.
It excludes files under `pylean/` (virtual environment and third-party site-packages).

Source list used:
- non_lean_code_files_clean.txt

## Core Pipeline and Backtesting

- [ingest_to_clickhouse.py](ingest_to_clickhouse.py): Direct yfinance to ClickHouse ingestion script with incremental watermark logic, coverage refresh, and verify mode.


- [direct_lean_clickhouse_probe.py](direct_lean_clickhouse_probe.py): Boots LEAN runtime from Python, pulls ClickHouse bars, and validates LEAN indicator updates as a probe.
- [es_ma_crossover_clickhouse_backtest.py](es_ma_crossover_clickhouse_backtest.py): ES 50/200 MA crossover backtest on ClickHouse data; outputs summary JSON and equity CSV.
- [es_ma_crossover_clickhouse_backtest_pylean.py](es_ma_crossover_clickhouse_backtest_pylean.py): PyLEAN-oriented ES 50/200 MA crossover backtest that bootstraps LEAN from `Research/start.py`, queries ClickHouse bars, computes LEAN SMA signals, and writes equity/results artifacts.
- [es_1y_lean_chart.py](es_1y_lean_chart.py): Standalone PyLEAN charting script that bootstraps LEAN, pulls 1-year ES daily bars from ClickHouse, builds LEAN candle/SMA series, and exports JSON/PNG/CSV chart artifacts.

- [es_ma_backtest_full_report.py](es_ma_backtest_full_report.py): Full engine-style report generator (HTML + charts + metrics) for MA crossover results.
- [run_probe_in_docker.sh](run_probe_in_docker.sh): Docker wrapper that prepares LEAN runtime artifacts in-container and runs the direct probe script.
        It is a smoke test for LEAN + ClickHouse integration, not the strategy backtest pipeline.
        It runs `direct_lean_clickhouse_probe.py` in Docker to confirm data query, LEAN bootstrap, and indicator updates.
        It prepares runtime bits needed by the probe (copies `start.py`, runtimeconfig, `AlgorithmImports`, QuantConnect DLLs) and then executes the probe script.


- [run_es_ma_backtest_in_docker.sh](run_es_ma_backtest_in_docker.sh): Docker wrapper for the non-pylean ES MA backtest path (`es_ma_crossover_clickhouse_backtest.py`) that copies result artifacts back to host.
- [es_ma_crossover_pylean_docker_reproducibility_runbook.md](es_ma_crossover_pylean_docker_reproducibility_runbook.md): End-to-end technical runbook for the pylean Docker execution path, including required bootstrap change (`System.Drawing.Common` preload), known-good runtime command, parameter usage, failure matrix, and caveats.
- [es_1y_lean_chart_runbook.md](es_1y_lean_chart_runbook.md): Dedicated reproducibility runbook for generating the 1-year ES chart via `es_1y_lean_chart.py`, including Docker command, validation steps, and troubleshooting signatures.

## Data Collection Scripts

- [get_sp500_daily_yfinance.py](get_sp500_daily_yfinance.py): Downloads max historical daily S&P 500 index data from yfinance and writes normalized CSV.
- [get_sp500_all_timeframes_yfinance.py](get_sp500_all_timeframes_yfinance.py): Incrementally downloads multi-instrument, multi-timeframe yfinance data to CSV outputs.
- [get_fred_market_data.py](get_fred_market_data.py): Downloads configured FRED series, updates CSV incrementally, and generates plots.
- [get_es_futures_actual_data.py](get_es_futures_actual_data.py): Pulls ES proxy market data (FRED-first workflow) with plotting and fallback handling.
- [get_es_futures_actual_data_fred.py](get_es_futures_actual_data_fred.py): Backward-compatible wrapper that calls the FRED downloader entrypoint.
- [get_es_futures_daily_data.py](get_es_futures_daily_data.py): Scrapes full ES daily history from Stooq with paginated fetch and cache.
- [get_es_futures_data.py](get_es_futures_data.py): Generates/simulates ES hourly OHLCV-style data and visualizes recent period.

## Analysis and Research Utilities

- [analyze_es_volatility.py](analyze_es_volatility.py): Year-by-year ES volatility and price range analysis.
- [explain_drawdown.py](explain_drawdown.py): Educational walkthrough script explaining max drawdown vs total return differences.
- [view_market_conditions.py](view_market_conditions.py): Interactive condition scanner for SMA hierarchy states; exports HTML and condition CSVs.
- [trading_journal.py](trading_journal.py): Comprehensive trading journal system with notes, review workflow, metrics, and persistence.
- [risk_management_demo_standalone.py](risk_management_demo_standalone.py): Standalone risk/trade management simulation demo without requiring LEAN engine runtime.
- [analyze_trade_5.py](analyze_trade_5.py): Deep-dive diagnostic script for one specific demo trade scenario.

## LEAN and Environment Support

- [AlgorithmImports.py](AlgorithmImports.py): Root-level LEAN Python imports bootstrap file used by local/container scripts.
- [ESFuturesDemo/main.py](ESFuturesDemo/main.py): QCAlgorithm-based ES futures risk-management demo algorithm.
- [ESFuturesDemo/research.ipynb](ESFuturesDemo/research.ipynb): Notebook for exploratory research related to the ES futures demo.
- [test_pylean.py](test_pylean.py): Environment validation script for pylean and key Python dependencies.
- [run_syntax_check.py](run_syntax_check.py): Batch mypy/syntax-check helper across Algorithm.Python files with filtering/normalization.

## Build, Benchmark, and Repo Ops

- [run_benchmarks.py](run_benchmarks.py): Executes LEAN launcher benchmark algorithms and writes benchmark_results.json.
- [compare_benchmarks.py](compare_benchmarks.py): Compares new benchmark results to a reference with pass/fail thresholds.
- [ci_build_stubs.sh](ci_build_stubs.sh): CI helper to generate/publish QuantConnect Python stubs.
- [rebase_organization_branches.sh](rebase_organization_branches.sh): Rebases org-* branches onto master and force-pushes, now with destructive-clean confirmation guard.

## Notes

- The list above is intentionally scoped to non-PyLean repo code only.
- Files in `pylean/` and other environment-managed third-party directories are intentionally excluded.
- Some scripts are experimental utilities and may use simulated data or proxy data sources.
