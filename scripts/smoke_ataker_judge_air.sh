#!/usr/bin/env bash
# Smoke: песочница :8010 + JUDGE через Dolphin на LM Studio :1234.
# Только Air. Studio :8000 не трогает.
#
# Предусловия:
#   - Dolphin Q4_K_M на AtakerDirty (scripts/download_dolphin_air.sh)
#   - LM Studio Local Server с этой моделью
#   - в другом терминале: ./scripts/serve_sandbox_air.sh
#
#   JUDGE=1 LIMIT=5 ./scripts/smoke_ataker_judge_air.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SANDBOX="${KREPOST_SANDBOX_URL:-http://127.0.0.1:8010}"
LMS="${ATAKER_JUDGE_URL:-http://127.0.0.1:1234}"

echo "== health sandbox ${SANDBOX} =="
if ! curl -sf --max-time 5 "${SANDBOX}/health" -o /tmp/ataker_sandbox_health.json; then
  echo "FAIL: песочница не отвечает. Запусти ./scripts/serve_sandbox_air.sh" >&2
  exit 1
fi
head -c 400 /tmp/ataker_sandbox_health.json; echo ""

echo "== LM Studio models ${LMS} =="
if ! curl -sf --max-time 5 "${LMS}/v1/models" -o /tmp/ataker_lms_models.json; then
  echo "FAIL: LM Studio :1234 не отвечает. Load Dolphin + Start Server." >&2
  exit 1
fi
head -c 800 /tmp/ataker_lms_models.json; echo ""

if [[ -z "${ATAKER_JUDGE_MODEL:-}" ]]; then
  echo "WARN: ATAKER_JUDGE_MODEL не задан — hit-скрипт возьмёт дефолт/первый id."
  echo "  export ATAKER_JUDGE_MODEL=<id из вывода models>"
fi

export ATAKER_JUDGE_URL="${LMS}"
LIMIT="${LIMIT:-5}"
JUDGE="${JUDGE:-1}"
echo "== ataker JUDGE=${JUDGE} LIMIT=${LIMIT} → ${SANDBOX} =="
JUDGE="$JUDGE" LIMIT="$LIMIT" "$ROOT/scripts/ataker_sandbox_air.sh"

echo "OK smoke. Отчёт: data/ataker_sandbox/ или \$SSD/reports"
