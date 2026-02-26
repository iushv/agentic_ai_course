#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PWD}/src${PYTHONPATH:+:$PYTHONPATH}"

echo "[1/5] Compile Python modules..."
uv run python -m compileall src tests

echo "[2/5] Run unit/integration tests..."
uv run python -m pytest tests/ -q

echo "[3/5] Validate notebook JSON files..."
uv run python - <<'PY'
import json
from pathlib import Path

nb_paths = [
    p
    for p in sorted(Path("notebooks").glob("[0-9][0-9]_*.ipynb"))
    if not p.name.endswith(".executed.ipynb")
]
if not nb_paths:
    raise SystemExit("No canonical lesson notebooks found")

for p in nb_paths:
    json.loads(p.read_text())
print(f"Validated {len(nb_paths)} notebook files.")
PY

echo "[4/5] Execute masterclass notebook..."
mkdir -p .artifacts/notebooks
uv run jupyter nbconvert \
  --to notebook \
  --execute notebooks/09_sota_masterclass.ipynb \
  --output 09_sota_masterclass.executed.ipynb \
  --output-dir .artifacts/notebooks \
  --ExecutePreprocessor.timeout=240
echo "Masterclass execution artifact: .artifacts/notebooks/09_sota_masterclass.executed.ipynb"

echo "[5/5] Import smoke check..."
uv run python - <<'PY'
from analyst import DataAnalystAgent
from analyst.api import app

assert DataAnalystAgent is not None
paths = [r.path for r in app.routes if hasattr(r, "path")]
assert "/health" in paths
assert "/analyze" in paths
print("Import smoke check passed.")
PY

echo "Preflight checks passed."
