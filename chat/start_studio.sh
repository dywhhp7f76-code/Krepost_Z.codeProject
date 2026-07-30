#!/usr/bin/env bash
# Запуск Крепости на Mac Studio (локально + доступ с Air по Tailscale).
#
#   cd ~/Krepost-V3
#   bash chat/start_studio.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
cd "$REPO"

HOST="${KREPOST_API_HOST:-0.0.0.0}"
PORT="${KREPOST_API_PORT:-8000}"
HUB_PORT="${CHAT_PORT:-8765}"

if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "python3 не найден" >&2
  exit 1
fi

mkdir -p "$ROOT/data"
API_LOG="$ROOT/data/api.log"
HUB_LOG="$ROOT/data/hub.log"

kill_port() {
  local port="$1"
  # без lsof/xcode — через python
  "$PY" - "$port" <<'PY' 2>/dev/null || true
import os, signal, sys
port = int(sys.argv[1])
try:
    import subprocess
    out = subprocess.check_output(["netstat", "-anv"], text=True, stderr=subprocess.DEVNULL)
except Exception:
    out = ""
# мягкий вариант: pkill по известным командам
for pat in ("krepost.api.server", "chat/server.py", f":{port}"):
    os.system(f"pkill -f '{pat}' >/dev/null 2>&1 || true")
PY
  pkill -f "krepost.api.server" >/dev/null 2>&1 || true
  pkill -f "chat/server.py" >/dev/null 2>&1 || true
  sleep 1
}

echo "→ API на ${HOST}:${PORT}"
kill_port "$PORT"

if [[ -n "${KREPOST_API_CMD:-}" ]]; then
  nohup bash -c "$KREPOST_API_CMD" >"$API_LOG" 2>&1 &
else
  nohup env KREPOST_API_HOST="$HOST" KREPOST_API_PORT="$PORT" \
    "$PY" -m krepost.api.server >"$API_LOG" 2>&1 &
fi
echo "  API pid=$!  log=$API_LOG"

ok=0
for _ in $(seq 1 20); do
  if curl -sf --max-time 1 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 0.5
done
if [[ "$ok" != "1" ]]; then
  echo "API не поднялся. Хвост лога:" >&2
  tail -40 "$API_LOG" >&2 || true
  exit 1
fi
echo "  health localhost: OK"

echo "→ Hub на 127.0.0.1:${HUB_PORT}"
kill_port "$HUB_PORT"
if [[ -f "$ROOT/agents.defaults.json" ]]; then
  cp "$ROOT/agents.defaults.json" "$ROOT/data/agents.json"
fi
export KREPOST_URL="http://127.0.0.1:${PORT}"
export CHAT_PORT="$HUB_PORT"
nohup env KREPOST_URL="$KREPOST_URL" CHAT_PORT="$HUB_PORT" \
  "$PY" "$ROOT/server.py" >"$HUB_LOG" 2>&1 &
echo "  Hub pid=$!  log=$HUB_LOG"
sleep 1
curl -sf --max-time 2 "http://127.0.0.1:${HUB_PORT}/api/agents/use-local" >/dev/null 2>&1 || true

echo ""
echo "Готово на Studio:"
echo "  хаб (наш):     http://127.0.0.1:${HUB_PORT}"
echo "  API local:     http://127.0.0.1:${PORT}/health"
echo "  боевой чат:    http://10.0.0.1:${PORT}/chat"
echo "  с Air health:  curl -m 5 http://10.0.0.1:${PORT}/health"
