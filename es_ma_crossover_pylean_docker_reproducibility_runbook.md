# System.Drawing + LEAN Docker Runbook (PyLEAN ClickHouse Backtest)

This document captures the exact setup and commands that produced a successful run for:

- `es_ma_crossover_clickhouse_backtest_pylean.py`

It also records what failed and why, so future agents can reproduce without repeating dead ends.

## Scope

This runbook is for running a Python script that bootstraps LEAN via `Research/start.py`, computes indicators through LEAN assemblies, and reads data from ClickHouse.

Primary script:

- `es_ma_crossover_clickhouse_backtest_pylean.py`

Related charting script:

- `es_1y_lean_chart.py` (documented in a dedicated runbook)

Bootstrap file changed in this work:

- `Research/start.py`

## Environment Summary

- Host OS: Linux
- Docker required
- Docker access in this environment: `sudo -n docker ...`
- Working image used for successful run: `my-pylean-jupyter:latest`
- Critical in-container LEAN runtime directory: `/Lean/Launcher/bin/Debug`

## Docker Images Used and Runtime Usage

### Image Inventory used during investigation

- `my-pylean-jupyter:latest` (final successful path)
- `quantconnect/lean:latest` (tested; did not work with this bootstrap path as-is)
- `quantconnect/research:latest` (tested for compatibility)

### Runtime role of each image

1. `my-pylean-jupyter:latest`

- This is the execution image for the final run.
- It contains a usable LEAN launcher runtime under `/Lean/Launcher/bin/Debug`.
- The final command runs the Python script while current working directory is `/Lean/Launcher/bin/Debug` so LEAN Composer can resolve handlers and assemblies.

2. `quantconnect/lean:latest`

- Useful as a baseline official engine image.
- Not directly suitable for this script path without additional bootstrap/runtime adjustments in this environment.

3. `quantconnect/research:latest`

- Useful for compatibility probing and older config behavior checks.
- Not selected as final execution image for this runbook.

### How image is used at runtime in the final flow

- Host repo is mounted to `/src`.
- Script and patched bootstrap/runtimeconfig are copied to `/tmp/pylean_run`.
- Process then runs from `/Lean/Launcher/bin/Debug` (inside image) to preserve LEAN runtime composition.
- Outputs are copied back from container path to mounted host repo files.

### Runtime sequence (step-by-step)

1. Host starts container with `--network host` and repo mounted at `/src`.
2. Container prepares transient run folder at `/tmp/pylean_run` and copies:
  - script: `es_ma_crossover_clickhouse_backtest_pylean.py`
  - bootstrap: `Research/start.py`
  - runtime config: `Research/QuantConnect.Lean.Launcher.runtimeconfig.json`
3. Container changes directory to `/Lean/Launcher/bin/Debug`.
4. `PYTHONPATH` is set to include `/Lean/Launcher/bin/Debug` so LEAN runtime modules are resolvable.
5. Script executes and calls `runpy.run_path(...)` on copied `start.py`.
6. LEAN bootstraps CoreCLR, imports `AlgorithmImports`, initializes handlers/composer.
7. Backtest code queries ClickHouse, computes LEAN SMA indicators, writes outputs.
8. CSV/JSON outputs are copied to host-mounted `/src` files.

### Why working directory matters at runtime

`Initializer.Start()` relies on LEAN composition/exports being discoverable from runtime assembly paths. In this setup, the stable path is `/Lean/Launcher/bin/Debug`. Running from a random temp folder can break handler discovery (for example `CompositeLogHandler` resolution failures).

## LEAN Libraries Loaded at Runtime

`Research/start.py` does the following:

1. Loads CoreCLR runtime via `clr_loader.get_coreclr(...)` using `Research/QuantConnect.Lean.Launcher.runtimeconfig.json`.
2. Preloads `System.Drawing.Common` (new fix).
3. Imports `AlgorithmImports`.
4. Adds reference to `Fasterflect`.
5. Calls LEAN initialization pipeline:
   - `Config.Reset()`
   - `Initializer.Start()`
   - `Initializer.GetSystemHandlers()`
   - `Initializer.GetAlgorithmHandlers(researchMode=True)`
   - `PythonInitializer.Initialize(False)`

`AlgorithmImports.py` then loads LEAN assemblies by scanning for DLLs matching `QuantConnect.*` and importing large API surfaces.

Common LEAN namespaces loaded include (non-exhaustive):

- `QuantConnect`
- `QuantConnect.Api`
- `QuantConnect.Data`
- `QuantConnect.Algorithm`
- `QuantConnect.Indicators`
- `QuantConnect.Securities`
- `QuantConnect.Configuration`
- `QuantConnect.Research`
- `QuantConnect.Lean.Engine`
- plus many sub-namespaces under data/securities/framework/orders.

### LEAN assembly load mechanism used here

1. `Research/start.py` sets .NET runtime via runtimeconfig.
2. `AlgorithmImports.py` executes `AddReference("System")`.
3. `AlgorithmImports.py` enumerates files in its own directory and calls `AddReference(...)` for each DLL that matches `QuantConnect.*`.
4. Namespace imports expose LEAN API surfaces to Python code.

Practical implication: the folder that `AlgorithmImports.py` resolves from must contain the expected `QuantConnect.*.dll` set.

## Libraries Used in This Backtesting Script

### Python-level libraries used directly by `es_ma_crossover_clickhouse_backtest_pylean.py`

- Standard library:
  - `argparse`, `json`, `math`, `runpy`, `dataclasses`, `pathlib`
- Third-party:
  - `pandas`
  - `clickhouse_driver` (imported inside `load_daily_bars`)

### LEAN/.NET libraries used indirectly through PythonNet

- Indicators used:
  - `QuantConnect.Indicators.SimpleMovingAverage`
  - `QuantConnect.Indicators.IndicatorDataPoint`
- Engine/runtime used through bootstrap:
  - LEAN initialization classes exposed by `AlgorithmImports` and startup sequence

### Data/service dependencies

- ClickHouse server reachable from container network namespace (host mode in this runbook).
- Database/table assumptions in SQL query:
  - `market_bars`, `instruments`, `timeframes`

### Dependency matrix (who uses what)

1. Bootstrap/runtime layer
- `clr_loader`, `pythonnet`, `System.Drawing.Common`, LEAN assemblies.

2. Data access layer
- `clickhouse_driver` for SQL access to ClickHouse.

3. Computation layer
- LEAN indicators (`SimpleMovingAverage`, `IndicatorDataPoint`).
- `pandas` for tabular handling, returns, equity, drawdown.

4. Reporting/output layer
- Python stdlib `json` for summary.
- CSV output via `pandas.to_csv`.

## What Else To Add (Recommended Next Sections)

To make this runbook even more future-proof for any agent/session, add the following:

1. Version pinning snapshot

- Capture image digest (`docker inspect --format='{{index .RepoDigests 0}}' ...`) for final image.
- Capture `python3 --version` and `dotnet --version` from inside container.

2. Preflight checks script

- Verify Docker access (`sudo -n docker ps`).
- Verify ClickHouse reachability from container.
- Verify required files exist before run.

3. Troubleshooting decision tree

- If error contains `System.Drawing`: check preload block.
- If error contains `CompositeLogHandler`: check working directory `/Lean/Launcher/bin/Debug`.
- If error contains `QuantConnect` import issues: check `PYTHONPATH` and runtime folder.

4. Determinism and drift notes

- Note that metrics can change with new market data rows.
- Record date window and row count (`DataPoints`) expected at time of run.

5. Security/ops notes

- Document reason for `--network host`.
- Document least-privilege alternative if host networking is disallowed.

6. Image/assembly manifest snapshot

- Record `docker image inspect` output for final image tag/digest.
- Record `ls /Lean/Launcher/bin/Debug/QuantConnect*.dll` from inside container.
- Record `pip show clr-loader pythonnet pandas clickhouse-driver` versions used at run time.

7. Runtime smoke-test block

- Add a 10-second sanity check command before full backtest:
  - start runtime
  - import `QuantConnect`
  - import `System.Drawing`
  - create one `SimpleMovingAverage`

8. Failure signature index

- A small map from error text to immediate fix action:
  - `No module named 'System.Drawing'` -> preload block missing/not executed.
  - `No module named 'QuantConnect'` -> wrong `PYTHONPATH` or runtime directory.
  - `CompositeLogHandler` export error -> wrong working directory for LEAN composer.

## Root Cause

`Research/start.py` loads CoreCLR and then imports `AlgorithmImports`.

`AlgorithmImports.py` imports `System.Drawing`:

```python
from System.Drawing import *
```

On Linux/.NET runtime combinations used here, `System.Drawing` is not always auto-loaded, causing:

- `No module named 'System.Drawing'`

## Code Change Applied

File changed:

- `Research/start.py`

Change: preload `System.Drawing.Common` before importing `AlgorithmImports`.

```python
# On Linux/.NET, System.Drawing may not be auto-loaded; preload if available.
try:
    from clr import AddReference
    AddReference("System.Drawing.Common")
except Exception:
    # Keep startup resilient across images where this assembly is absent.
    pass
```

Placement: immediately after `set_runtime(...)` and before `from AlgorithmImports import *`.

## Script Interface (Parameters)

`es_ma_crossover_clickhouse_backtest_pylean.py` supports:

- `--host` (default: `localhost`)
- `--port` (default: `9000`)
- `--database` (default: `market`)
- `--symbol` (default: `es`)
- `--timeframe` (default: `1d`)
- `--fast` (default: `50`)
- `--slow` (default: `200`)
- `--initial-cash` (default: `100000.0`)

Validation in script:

- `fast < slow` must hold, else script raises `ValueError`.

## Why the Final Command Works

Two key requirements must both be true:

1. `System.Drawing.Common` is preloaded (handled by the change in `Research/start.py`).
2. LEAN composition/assemblies resolve from a directory containing full launcher runtime artifacts (handlers/config), not an arbitrary temp folder.

Running from `/Lean/Launcher/bin/Debug` inside the container satisfies (2).

## Reproducible Command (Known Good)

Run from repo root on host:

```bash
cd /home/jyck613/dev/my-pylean

sudo -n docker run --rm --network host \
  -v "$PWD":/src:rw \
  my-pylean-jupyter \
  bash -lc '
    set -euo pipefail

    python3 -m pip install --break-system-packages --no-cache-dir clickhouse-driver pandas >/tmp/pip_backtest.log 2>&1 || true

    RUNROOT=/tmp/pylean_run
    rm -rf "$RUNROOT"
    mkdir -p "$RUNROOT/Research"

    cp /src/es_ma_crossover_clickhouse_backtest_pylean.py "$RUNROOT/"
    cp /src/Research/start.py "$RUNROOT/Research/start.py"
    cp /src/Research/QuantConnect.Lean.Launcher.runtimeconfig.json "$RUNROOT/Research/"

    cd /Lean/Launcher/bin/Debug
    export PYTHONPATH=/Lean/Launcher/bin/Debug:${PYTHONPATH:-}

    python3 "$RUNROOT/es_ma_crossover_clickhouse_backtest_pylean.py"

    cp -f /Lean/Launcher/bin/Debug/es_ma_crossover_equity_curve.csv /src/es_ma_crossover_equity_curve.csv
    cp -f /Lean/Launcher/bin/Debug/es_ma_crossover_results.json /src/es_ma_crossover_results.json
  '
```

### Optional Parameterized Variant

Append script args after script path in the `python3` line, for example:

```bash
python3 "$RUNROOT/es_ma_crossover_clickhouse_backtest_pylean.py" \
  --symbol es --timeframe 1d --fast 50 --slow 200 --initial-cash 100000 \
  --host localhost --port 9000 --database market
```

## Run Result (Successful)

Successful run emitted LEAN startup logs and completed summary metrics.

Output files updated on host:

- `es_ma_crossover_equity_curve.csv`
- `es_ma_crossover_results.json`

Observed result snapshot:

- `Engine`: `LEAN Indicators`
- `Symbol`: `es`
- `Timeframe`: `1d`
- `DataPoints`: `6484`
- `FinalEquity`: `522977.46116315544`
- `TotalNetProfitPct`: `422.9774611631554`
- `CagrPct`: `6.640891632394452`
- `MaxDrawdownPct`: `-34.445346520038335`

## Failure Matrix (What Was Tried and Failed)

### 1) Direct run in mounted `/src` without bootstrap fix

Command pattern:

- run script in container from `/src`

Failure:

- `No module named 'System.Drawing'`

Reason:

- `System.Drawing` not auto-loaded in this runtime path.

### 2) Switching image only to `quantconnect/lean:latest`

Failure patterns encountered:

- entrypoint conflict (`dotnet QuantConnect.Lean.Launcher.dll` consumes args unless `--entrypoint` overridden)
- missing Python package (`No module named 'clr_loader'`) until installed
- still `No module named 'System.Drawing'` with unchanged bootstrap

Reason:

- image swap alone did not satisfy bootstrap import sequence.

### 3) Building solution in container (`dotnet build QuantConnect.Lean.sln`)

Failures observed:

- missing project path in solution in this workspace copy (`Tests/QuantConnect.Tests.csproj` not found)
- large C# compile failures related to Python types (`PyObject`, `Python`, etc.) and language/version mismatch

Reason:

- this repo state does not cleanly build full LEAN solution in this container path.

### 4) Running from temporary folder without LEAN launcher working directory

Failure:

- `Unable to locate any exports matching ... CompositeLogHandler`

Reason:

- LEAN Composer resolves handlers/assemblies from current runtime directory; temp folder lacked expected runtime composition context.

## Caveats and Guardrails

1. Keep container working directory as `/Lean/Launcher/bin/Debug` when running this script.
2. Ensure `Research/start.py` includes the `System.Drawing.Common` preload block.
3. Keep `--network host` if using `--host localhost` for ClickHouse.
4. If not using host network, use `host.docker.internal` where appropriate for host services.
5. Do not rely on full repo build in this environment for this workflow; use container's prebuilt launcher runtime.

## Quick Validation Checklist

1. `sudo -n docker images | grep my-pylean-jupyter`
2. Confirm preload block exists in `Research/start.py`.
3. Run known-good command above.
4. Confirm host artifacts updated timestamps:

```bash
ls -l --time-style=long-iso es_ma_crossover_results.json es_ma_crossover_equity_curve.csv
sed -n '1,80p' es_ma_crossover_results.json
```

## Optional Wrapper Script Template

If you want a reusable runner shell script, use this template:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${IMAGE:-my-pylean-jupyter}"

SCRIPT_ARGS=("$@")
if [[ ${#SCRIPT_ARGS[@]} -eq 0 ]]; then
  SCRIPT_ARGS=(--symbol es --timeframe 1d --fast 50 --slow 200 --initial-cash 100000)
fi

sudo -n docker run --rm --network host \
  -v "${ROOT_DIR}":/src:rw \
  "${IMAGE}" \
  bash -lc '
    set -euo pipefail
    python3 -m pip install --break-system-packages --no-cache-dir clickhouse-driver pandas >/tmp/pip_backtest.log 2>&1 || true
    RUNROOT=/tmp/pylean_run
    rm -rf "$RUNROOT"
    mkdir -p "$RUNROOT/Research"
    cp /src/es_ma_crossover_clickhouse_backtest_pylean.py "$RUNROOT/"
    cp /src/Research/start.py "$RUNROOT/Research/start.py"
    cp /src/Research/QuantConnect.Lean.Launcher.runtimeconfig.json "$RUNROOT/Research/"
    cd /Lean/Launcher/bin/Debug
    export PYTHONPATH=/Lean/Launcher/bin/Debug:${PYTHONPATH:-}
    python3 "$RUNROOT/es_ma_crossover_clickhouse_backtest_pylean.py" "$@"
    cp -f /Lean/Launcher/bin/Debug/es_ma_crossover_equity_curve.csv /src/es_ma_crossover_equity_curve.csv
    cp -f /Lean/Launcher/bin/Debug/es_ma_crossover_results.json /src/es_ma_crossover_results.json
  ' _ "${SCRIPT_ARGS[@]}"

echo "Done. Outputs:"
echo "- ${ROOT_DIR}/es_ma_crossover_results.json"
echo "- ${ROOT_DIR}/es_ma_crossover_equity_curve.csv"
```

## Change Log

- Added preload block to `Research/start.py` for `System.Drawing.Common` before `AlgorithmImports`.
- No other repo files modified as part of the fix itself.
- Added related charting workflow script `es_1y_lean_chart.py` and its dedicated runbook `es_1y_lean_chart_runbook.md`.
