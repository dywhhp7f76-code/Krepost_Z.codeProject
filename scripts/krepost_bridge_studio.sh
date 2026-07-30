#!/usr/bin/env bash
# Межсетевой мост Крепости через Tailscale (не тот же Wi‑Fi).
# Запуск на Mac Studio:
#   ./scripts/krepost_bridge_studio.sh
#
# Не открывает порты в интернет. Доступ только устройствам твоего Tailscale.

set -euo pipefail

PORT="${KREPOST_API_PORT:-8000}"
TS=""
for c in \
  /Applications/Tailscale.app/Contents/MacOS/Tailscale \
  /usr/local/bin/tailscale \
  /opt/homebrew/bin/tailscale \
  "$(command -v tailscale 2>/dev/null || true)"
do
  if [[ -n "$c" && -x "$c" ]]; then TS="$c"; break; fi
done

echo "=== Krepost remote bridge (Studio) ==="
if [[ -z "$TS" ]]; then
  echo "❌ Tailscale не найден."
  echo "   Установи: https://tailscale.com/download/mac"
  echo "   Войди в свой аккаунт → Run at startup."
  exit 1
fi

echo "✓ Tailscale: $TS"
IP="$("$TS" ip -4 2>/dev/null | head -1 || true)"
if [[ -z "$IP" ]]; then
  echo "❌ Нет Tailscale IP — открой приложение Tailscale и войди в аккаунт."
  exit 1
fi
echo "✓ Studio Tailscale IP: $IP"
echo "✓ URL для Krepost Chat (с любой сети): http://${IP}:${PORT}"

# Save for operator
mkdir -p "${HOME}/.krepost"
python3 - <<PY
import json
from pathlib import Path
p = Path.home() / ".krepost" / "chat_bridge.json"
cur = {}
if p.exists():
    try:
        cur = json.loads(p.read_text())
    except Exception:
        cur = {}
cur["studio_tailscale_ip"] = "$IP"
cur["studio_url"] = "http://${IP}:${PORT}"
cur["role"] = "studio"
p.write_text(json.dumps(cur, ensure_ascii=False, indent=2))
print(f"✓ записано {p}")
PY

echo ""
echo "Проверка API на localhost:${PORT}…"
if curl -sf --max-time 3 "http://127.0.0.1:${PORT}/health" >/dev/null; then
  echo "✓ Крепость отвечает на :${PORT}"
else
  echo "⚠ Крепость не отвечает на :${PORT} — запусти serve_lmstudio / launchd."
fi

echo ""
echo "Обязательно на Studio:"
echo "  export KREPOST_OPERATOR_PASSWORD='…'   # иначе чат снаружи опасен"
echo "  API слушает 0.0.0.0:${PORT} (как в serve_lmstudio) — доступен по Tailscale IP"
echo ""
echo "На Air: ./scripts/krepost_bridge_air.sh"
echo "  или в Krepost Chat нажми «Мост Tailscale»"
