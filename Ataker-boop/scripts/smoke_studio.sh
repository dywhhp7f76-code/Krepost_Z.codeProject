#!/usr/bin/env bash
# Seed smoke → Studio over Thunderbolt. No LLM / no judge.
#   source /Volumes/AtakerDirty/Ataker/env.fortress.sh
#   bash Ataker-boop/scripts/smoke_studio.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source /Volumes/AtakerDirty/Ataker/env.fortress.sh
URL="${KREPOST_STUDIO_URL:-http://10.0.0.1:8000}"
LIMIT="${LIMIT:-8}"
SEED="${SEED:-$ROOT/Ataker-boop/seed_attacks.local.jsonl}"
REPORTS="${ATAKER_REPORTS:-/Volumes/AtakerDirty/Ataker/reports}"
PY="${ROOT}/Ataker-boop/.venv/bin/python"

echo "health $URL"
curl -sf --max-time 5 "$URL/health" | tee /dev/stderr >/dev/null
echo
mkdir -p "$REPORTS"
export FORCE_STUDIO=1
exec "$PY" "$ROOT/scripts/ataker_hit_http.py" \
  --url "$URL" \
  --seed "$SEED" \
  --limit "$LIMIT" \
  --timeout 90 \
  --report-dir "$REPORTS"
