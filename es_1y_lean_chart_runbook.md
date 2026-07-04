# ES 1Y LEAN Chart Runbook (PyLEAN + Docker + ClickHouse)

This runbook captures the reproducible setup and command used to generate a 1-year ES chart with LEAN charting classes.

Primary script:

- `es_1y_lean_chart.py`

## Goal

Generate and export these artifacts for the last 1 year of ES daily bars:

- `es_1y_lean_chart.json` (LEAN chart payload with candle and SMA series points)
- `es_1y_lean_chart.png` (rendered visual chart)
- `es_1y_lean_chart_data.csv` (underlying data used for plotting)

## Runtime Preconditions

- Host OS: Linux
- Docker access: `sudo -n docker ...`
- Working image: `my-pylean-jupyter:latest`
- LEAN runtime directory in container: `/Lean/Launcher/bin/Debug`
- Bootstrap file with `System.Drawing.Common` preload in repo: `Research/start.py`

## Why This Flow Works

1. The script uses `runpy.run_path("Research/start.py")` to bootstrap LEAN and QuantConnect assemblies.
2. The process runs from `/Lean/Launcher/bin/Debug` so LEAN composer handlers/exports resolve correctly.
3. The container uses `--network host`, so `localhost:9000` reaches host ClickHouse.
4. Artifacts are copied from container runtime directory back to mounted host repo path.

## Script Interface

`es_1y_lean_chart.py` supports:

- `--host` (default: `localhost`)
- `--port` (default: `9000`)
- `--database` (default: `market`)
- `--symbol` (default: `es`)
- `--timeframe` (default: `1d`)
- `--sma` (default: `50`)

## Reproducible Command (Known Good)

Run from repo root:

```bash
cd /home/jyck613/dev/my-pylean

sudo -n docker run --rm --network host \
  -v "$PWD":/src:rw \
  my-pylean-jupyter \
  bash -lc '
    set -euo pipefail

    python3 -m pip install --break-system-packages --no-cache-dir clickhouse-driver pandas matplotlib >/tmp/pip_chart.log 2>&1 || true

    RUNROOT=/tmp/pylean_run_chart
    rm -rf "$RUNROOT"
    mkdir -p "$RUNROOT/Research"

    cp /src/es_1y_lean_chart.py "$RUNROOT/"
    cp /src/Research/start.py "$RUNROOT/Research/start.py"
    cp /src/Research/QuantConnect.Lean.Launcher.runtimeconfig.json "$RUNROOT/Research/"

    cd /Lean/Launcher/bin/Debug
    export PYTHONPATH=/Lean/Launcher/bin/Debug:${PYTHONPATH:-}

    python3 "$RUNROOT/es_1y_lean_chart.py" \
      --symbol es --timeframe 1d --sma 50 \
      --host localhost --port 9000 --database market

    cp -f /Lean/Launcher/bin/Debug/es_1y_lean_chart.json /src/es_1y_lean_chart.json
    cp -f /Lean/Launcher/bin/Debug/es_1y_lean_chart.png /src/es_1y_lean_chart.png
    cp -f /Lean/Launcher/bin/Debug/es_1y_lean_chart_data.csv /src/es_1y_lean_chart_data.csv
  '
```

## Observed Successful Output Snapshot

From successful run logs:

- `Bars`: `253`
- `Range`: `2025-05-22T00:00:00+00:00 -> 2026-05-22T00:00:00+00:00`

## Output Validation

```bash
ls -l --time-style=long-iso es_1y_lean_chart.json es_1y_lean_chart.png es_1y_lean_chart_data.csv
sed -n '1,60p' es_1y_lean_chart.json
```

Expected JSON shape:

- `chartName`
- `bars`
- `start`
- `end`
- `series.ES.type = Candle`
- `series.SMA50.type = Line`

## Failure Signatures and Fixes

1. `No module named 'System.Drawing'`

- Ensure `Research/start.py` contains the `AddReference("System.Drawing.Common")` preload block.

2. `Unable to locate any exports matching ... CompositeLogHandler`

- Ensure container working directory is `/Lean/Launcher/bin/Debug` before script execution.

3. `No module named 'clickhouse_driver'`

- Ensure in-container install line includes `clickhouse-driver` before running script.

4. `No data returned for requested symbol/timeframe`

- Verify ClickHouse connectivity and table contents for `market_bars`, `instruments`, and `timeframes`.

## Notes

- The chart JSON is a plain serialized payload built from LEAN chart objects so it is easy to inspect and reuse.
- The PNG is generated from the same data and LEAN SMA values for quick visual review.
