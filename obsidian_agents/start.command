#!/bin/bash
# Удобный запуск агентов Obsidian (Air) — UI в браузере, без VS Code
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
PROJECT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT" || exit 1

PY="$PROJECT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  /usr/bin/python3 -m venv "$PROJECT/.venv"
  "$PROJECT/.venv/bin/pip" install -q -r "$PROJECT/requirements.txt"
  PY="$PROJECT/.venv/bin/python"
fi

PORT=$(python3 -c "import json; print(json.load(open('config.json')).get('port',8765))" 2>/dev/null || echo 8765)

# если уже слушает — просто откроем UI
if curl -sf "http://127.0.0.1:${PORT}/api/config" >/dev/null 2>&1; then
  open "http://127.0.0.1:${PORT}/"
  exit 0
fi

# старт сервера в фоне + открыть браузер
nohup "$PY" "$PROJECT/app.py" >"$PROJECT/run.log" 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10 12 15; do
  if curl -sf "http://127.0.0.1:${PORT}/api/config" >/dev/null 2>&1; then
    open "http://127.0.0.1:${PORT}/"
    exit 0
  fi
  sleep 0.5
done

osascript -e 'display dialog "Не поднялся UI. Смотри run.log в obsidian_agents." buttons {"OK"}' || true
exit 1
