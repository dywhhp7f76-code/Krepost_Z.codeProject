#!/usr/bin/env bash
# Ataker → песочница Крепости на Air (localhost:8010), НЕ Studio :8000.
#
# Требует: песочница уже запущена (./scripts/serve_sandbox_air.sh)
#
#   ./scripts/ataker_sandbox_air.sh
#   LIMIT=5 ./scripts/ataker_sandbox_air.sh
#
# SSD (если смонтирован AtakerDirty):
#   SEED/ATAKER_VAULT/ATAKER_REPORT_DIR подхватываются из ~/Ataker-SSD

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

URL="${KREPOST_SANDBOX_URL:-http://127.0.0.1:8010}"
SSD="${HOME}/Ataker-SSD"
if [[ -z "${SEED:-}" ]]; then
  if [[ -f "${SSD}/seeds/seed_attacks.local.jsonl" ]]; then
    SEED="${SSD}/seeds/seed_attacks.local.jsonl"
  else
    SEED="$ROOT/Ataker-boop/seed_attacks.local.jsonl"
  fi
fi
[[ -f "$SEED" ]] || SEED="$ROOT/Ataker-boop/seed_attacks.example.jsonl"

LIMIT="${LIMIT:-20}"
TIMEOUT="${TIMEOUT:-90}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

# SSD paths
if [[ -d "$SSD" ]]; then
  export ATAKER_VAULT="${ATAKER_VAULT:-$SSD/ataker_vault/attacks.db}"
  export ATAKER_REPORT_DIR="${ATAKER_REPORT_DIR:-$SSD/reports}"
fi
REPORT_DIR="${ATAKER_REPORT_DIR:-$ROOT/data/ataker_sandbox}"
mkdir -p "$REPORT_DIR"
[[ -n "${ATAKER_VAULT:-}" ]] && mkdir -p "$(dirname "$ATAKER_VAULT")"

echo "🎯 Ataker → sandbox $URL (Studio :8000 не трогаем)"
echo "   seed=$SEED limit=$LIMIT"
echo "   reports=$REPORT_DIR"
[[ -n "${ATAKER_VAULT:-}" ]] && echo "   vault=$ATAKER_VAULT"

if ! curl -sf --max-time 5 "$URL/health" >/dev/null; then
  echo "❌ $URL/health недоступен. Сначала: ./scripts/serve_sandbox_air.sh" >&2
  exit 1
fi

HIT=(
  "$PY" "$ROOT/scripts/ataker_hit_http.py"
  --url "$URL"
  --seed "$SEED"
  --limit "$LIMIT"
  --timeout "$TIMEOUT"
  --report-dir "$REPORT_DIR"
)
[[ "${JUDGE:-0}" == "1" ]] && HIT+=(--judge)
exec "${HIT[@]}"
