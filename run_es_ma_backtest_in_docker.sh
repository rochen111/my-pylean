#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-my-pylean-jupyter}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  BACKTEST_ARGS=(--symbol es --timeframe 1d --fast 50 --slow 200 --initial-cash 100000)
else
  BACKTEST_ARGS=("$@")
fi

sudo docker run --rm --network host -v "${ROOT_DIR}":/src:rw "${IMAGE}" bash -s -- "${BACKTEST_ARGS[@]}" <<'CONTAINER_SCRIPT'
set -euo pipefail

cp -a /src /tmp/work
cd /tmp/work

python3 -m pip install --break-system-packages --no-cache-dir clickhouse-driver pandas >/tmp/pip_backtest.log 2>&1 || true
python3 es_ma_crossover_clickhouse_backtest.py "$@"

cp -f es_ma_crossover_equity_curve.csv /src/es_ma_crossover_equity_curve.csv
cp -f es_ma_crossover_results.json /src/es_ma_crossover_results.json
CONTAINER_SCRIPT

echo "Backtest complete. Outputs:"
echo "- ${ROOT_DIR}/es_ma_crossover_results.json"
echo "- ${ROOT_DIR}/es_ma_crossover_equity_curve.csv"
