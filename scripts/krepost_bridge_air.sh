#!/usr/bin/env bash
# Клиентская сторона моста — MacBook Air (другая сеть / не тот же Wi‑Fi).
#   ./scripts/krepost_bridge_air.sh
#   ./scripts/krepost_bridge_air.sh 100.x.x.x   # IP Studio вручную

set -euo pipefail

PORT="${KREPOST_API_PORT:-8000}"
HINT_IP="${1:-}"

TS=""
for c in \
  /Applications/Tailscale.app/Contents/MacOS/Tailscale \
  /usr/local/bin/tailscale \
  /opt/homebrew/bin/tailscale \
  "$(command -v tailscale 2>/dev/null || true)"
do
  if [[ -n "$c" && -x "$c" ]]; then TS="$c"; break; fi
done

echo "=== Krepost remote bridge (Air) ==="
if [[ -z "$TS" ]]; then
  echo "❌ Поставь Tailscale: https://tailscale.com/download/mac"
  echo "   Войди в ТОТ ЖЕ аккаунт, что на Studio."
  exit 1
fi

ME="$("$TS" ip -4 2>/dev/null | head -1 || true)"
echo "✓ Air Tailscale IP: ${ME:-—}"

STUDIO_IP="$HINT_IP"
if [[ -z "$STUDIO_IP" && -f "${HOME}/.krepost/chat_bridge.json" ]]; then
  STUDIO_IP="$(python3 -c "import json;print(json.load(open('${HOME}/.krepost/chat_bridge.json')).get('studio_tailscale_ip',''))" 2>/dev/null || true)"
fi

if [[ -z "$STUDIO_IP" ]]; then
  echo "Ищу пир Studio в Tailscale…"
  # Prefer hostnames containing studio/krepost
  STUDIO_IP="$(
    "$TS" status --json 2>/dev/null | python3 -c '
import json,sys
st=json.load(sys.stdin)
cands=[]
for p in (st.get("Peer") or {}).values():
    host=(p.get("HostName") or "").lower()
    ips=p.get("TailscaleIPs") or []
    online=p.get("Online")
    ip4=next((i for i in ips if isinstance(i,str) and i.startswith("100.")), None)
    if not ip4: continue
    score=0
    for k in ("studio","krepost","mac-studio","macstudio"):
        if k in host: score+=10
    if online: score+=1
    cands.append((score, host, ip4, online))
cands.sort(reverse=True)
if cands:
    print(cands[0][2])
' || true
  )"
fi

if [[ -z "$STUDIO_IP" ]]; then
  echo "❌ Не нашёл Studio. Запусти на Studio: ./scripts/krepost_bridge_studio.sh"
  echo "   и передай IP: ./scripts/krepost_bridge_air.sh 100.x.x.x"
  exit 1
fi

URL="http://${STUDIO_IP}:${PORT}"
echo "✓ Studio URL: $URL"

mkdir -p "${HOME}/.krepost"
python3 - <<PY
import json
from pathlib import Path
p = Path.home() / ".krepost" / "chat_bridge.json"
cur = {}
if p.exists():
    try: cur = json.loads(p.read_text())
    except Exception: cur = {}
cur["studio_tailscale_ip"] = "$STUDIO_IP"
cur["studio_url"] = "$URL"
cur["role"] = "air"
p.write_text(json.dumps(cur, ensure_ascii=False, indent=2))
print(f"✓ записано {p}")
PY

echo "Проверка /health…"
if curl -sf --max-time 8 "$URL/health"; then
  echo ""
  echo "✅ Мост жив. В Krepost Chat API = $URL"
else
  echo ""
  echo "⚠ Не достучались до $URL"
  echo "  • Tailscale online на обоих Mac?"
  echo "  • Крепость запущена на Studio?"
  echo "  • KREPOST_OPERATOR_PASSWORD задан?"
  exit 1
fi
