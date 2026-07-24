#!/usr/bin/env bash
# Round Table UI + DebriefBroker на Air — порт 8011, localhost.
# Не трогает Studio :8000 и sandbox :8010.
# Канон: _handoff/ROUNDTABLE_DEBRIEF_SPEC.md
#
# По умолчанию DebriefMode (attack_locked=1).
# Combat: ROUNDTABLE_ATTACK_LOCKED=0 ROUNDTABLE_POISON_MARKER=/path/to/marker

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${ROUNDTABLE_PORT:-8011}"
HOST="${ROUNDTABLE_HOST:-127.0.0.1}"
export ROUNDTABLE_ATTACK_LOCKED="${ROUNDTABLE_ATTACK_LOCKED:-1}"
export ROUNDTABLE_POISON_MARKER="${ROUNDTABLE_POISON_MARKER:-}"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

UVICORN="${ROOT}/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN" ]]; then
  UVICORN="$(command -v uvicorn || true)"
fi
if [[ -z "${UVICORN}" ]]; then
  echo "❌ uvicorn не найден. Активируй .venv в $ROOT" >&2
  exit 1
fi

echo "🪑 RoundTable (Air)"
echo "   host=$HOST port=$PORT"
echo "   attack_locked=$ROUNDTABLE_ATTACK_LOCKED"
echo "   poison_marker=${ROUNDTABLE_POISON_MARKER:-<none>}"
echo "   UI → http://${HOST}:${PORT}/roundtable"

exec "$UVICORN" "krepost.roundtable.app:create_roundtable_app" --factory \
  --host "$HOST" --port "$PORT"
