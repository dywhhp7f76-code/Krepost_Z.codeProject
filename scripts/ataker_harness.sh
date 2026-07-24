#!/usr/bin/env bash
# Stub harness Ataker → песочница :8010 (не Studio :8000).
#
#   ./scripts/ataker_harness.sh
#   BATCH=10 MAX_ITER=5 ./scripts/ataker_harness.sh
#   DRY=1 ./scripts/ataker_harness.sh          # без сети
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
URL="${KREPOST_SANDBOX_URL:-http://127.0.0.1:8010}"
BATCH="${BATCH:-5}"
MAX_ITER="${MAX_ITER:-3}"
REPORT_DIR="${ATAKER_REPORT_DIR:-$ROOT/data/ataker_sandbox}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

export PYTHONPATH="${ROOT}/Ataker-boop${PYTHONPATH:+:$PYTHONPATH}"
args=( -m ataker.harness --url "$URL" --batch "$BATCH" --max-iter "$MAX_ITER" --report-dir "$REPORT_DIR" )
if [[ "${DRY:-0}" == "1" ]]; then
  args+=( --dry-run )
fi
exec "$PY" "${args[@]}"
