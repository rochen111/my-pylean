#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-my-pylean-jupyter}"

if [[ $# -eq 0 ]]; then
  PROBE_ARGS=(--limit 50)
else
  PROBE_ARGS=("$@")
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo docker run --rm --network host -v "${ROOT_DIR}":/src:ro "${IMAGE}" bash -s -- "${PROBE_ARGS[@]}" <<'CONTAINER_SCRIPT'
set -euo pipefail

cp -a /src /tmp/work
cd /tmp/work

python3 -m pip install --break-system-packages --no-cache-dir clickhouse-driver pandas >/tmp/pip_probe.log 2>&1 || true

cp /Lean/Launcher/bin/Debug/start.py Research/start.py
cp /Lean/Launcher/bin/Debug/QuantConnect.Lean.Launcher.runtimeconfig.json Research/QuantConnect.Lean.Launcher.runtimeconfig.json
cp /Lean/Launcher/bin/Debug/AlgorithmImports.py AlgorithmImports.py

sed -i "s/^from System\.Drawing import \*/try:\\n    from System.Drawing import *\\nexcept:\\n    pass/" AlgorithmImports.py

cp /Lean/Launcher/bin/Debug/QuantConnect*.dll .

python3 direct_lean_clickhouse_probe.py "$@"
CONTAINER_SCRIPT
