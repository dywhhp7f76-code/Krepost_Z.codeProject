#!/usr/bin/env bash
# Ataker → песочница Крепости на Air (localhost:8010), НЕ Studio :8000.
#
# Требует: песочница уже запущена (./scripts/serve_sandbox_air.sh)
# Опц.: SEED=Ataker-boop/seed_attacks.example.jsonl LIMIT=20
#
#   ./scripts/ataker_sandbox_air.sh
#   KREPOST_SANDBOX_URL=http://127.0.0.1:8010 LIMIT=5 ./scripts/ataker_sandbox_air.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

URL="${KREPOST_SANDBOX_URL:-http://127.0.0.1:8010}"
SEED="${SEED:-$ROOT/Ataker-boop/seed_attacks.example.jsonl}"
LIMIT="${LIMIT:-20}"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY="$(command -v python3)"

echo "🎯 Ataker → sandbox $URL (Studio :8000 не трогаем)"
echo "   seed=$SEED limit=$LIMIT"

# health
if ! curl -sf --max-time 5 "$URL/health" >/dev/null; then
  echo "❌ $URL/health недоступен. Сначала: ./scripts/serve_sandbox_air.sh" >&2
  exit 1
fi

exec "$PY" "$ROOT/scripts/ataker_hit_http.py" \
  --url "$URL" \
  --seed "$SEED" \
  --limit "$LIMIT"
