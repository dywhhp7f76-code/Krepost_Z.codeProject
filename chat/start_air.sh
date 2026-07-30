#!/usr/bin/env bash
# Чат на MacBook Air → API на Mac Studio по Tailscale.
#
# Сначала на Studio:  bash chat/start_studio.sh
# Потом на Air:
#   cd /path/to/Krepost-V3
#   bash chat/start_air.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
cd "$REPO"

STUDIO_URL="${KREPOST_STUDIO_URL:-http://10.0.0.1:8000}"
HUB_PORT="${CHAT_PORT:-8765}"

if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
else
  PY="$(command -v python3)"
fi

echo "→ Проверка Studio API: $STUDIO_URL/health  (UI: $STUDIO_URL/chat)"
if ! curl -sf --max-time 5 "$STUDIO_URL/health" >/dev/null; then
  echo "Studio недоступна с Air по $STUDIO_URL" >&2
  echo "Открой в браузере: $STUDIO_URL/chat" >&2
  echo "На Studio API должен слушать 0.0.0.0:8000 (bash chat/start_studio.sh)." >&2
  exit 1
fi
echo "  Studio OK → $STUDIO_URL/chat"

mkdir -p "$ROOT/data"
cp "$ROOT/agents.defaults.json" "$ROOT/data/agents.json" 2>/dev/null || true

if lsof -tiTCP:"$HUB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  lsof -tiTCP:"$HUB_PORT" -sTCP:LISTEN | xargs kill 2>/dev/null || true
  sleep 1
fi

export KREPOST_URL="$STUDIO_URL"
export KREPOST_STUDIO_URL="$STUDIO_URL"
export CHAT_PORT="$HUB_PORT"

HUB_LOG="$ROOT/data/hub.log"
nohup env KREPOST_URL="$KREPOST_URL" KREPOST_STUDIO_URL="$STUDIO_URL" CHAT_PORT="$HUB_PORT" \
  "$PY" "$ROOT/server.py" >"$HUB_LOG" 2>&1 &
echo "  Hub pid=$!"

sleep 1
curl -sf --max-time 2 "http://127.0.0.1:${HUB_PORT}/api/agents/use-studio" >/dev/null || true

echo ""
echo "Готово на Air: http://127.0.0.1:${HUB_PORT}"
open "http://127.0.0.1:${HUB_PORT}" 2>/dev/null || true
