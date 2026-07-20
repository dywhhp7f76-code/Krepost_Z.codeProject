#!/bin/bash
# Установка автозапуска Крепости на Mac Studio (launchd LaunchAgent).
#
# Label:  com.hervam.krepost.serve
# Port:   8000 (uvicorn serve_lmstudio:app)
# Logs:   $PROJECT/data/logs/serve_launchd.{out,err}.log
#
# Идемпотентно и безопасно: можно гонять повторно — перезапишет plist,
# мягко unload → bootstrap → kickstart. Не трогает Air / sandbox :8010.
#
# На Studio (после rsync кода):
#   cd ~/ZCodeProject/Krepost_Z.codeProject
#   bash scripts/install_launchd_studio.sh
#   curl -s http://127.0.0.1:8000/health
#
# Опции:
#   --dry-run   только показать пути и env, plist не писать / launchctl не трогать
#   --unload    только выгрузить агент (не удаляет plist)
#
# Переопределение корня: KREPOST_PROJECT=/path bash scripts/install_launchd_studio.sh
set -euo pipefail

LABEL="com.hervam.krepost.serve"
PROJECT="${KREPOST_PROJECT:-${HOME}/ZCodeProject/Krepost_Z.codeProject}"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
PY="${PROJECT}/.venv/bin/python"
LOG_DIR="${PROJECT}/data/logs"
DOMAIN="gui/$(id -u)"
DRY_RUN=0
UNLOAD_ONLY=0

for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=1 ;;
    --unload)  UNLOAD_ONLY=1 ;;
    -h|--help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "unknown option: ${arg}" >&2
      exit 2
      ;;
  esac
done

preflight() {
  if [[ ! -d "${PROJECT}" ]]; then
    echo "ERROR: project dir missing: ${PROJECT}" >&2
    exit 1
  fi
  if [[ ! -f "${PROJECT}/serve_lmstudio.py" ]]; then
    echo "ERROR: serve_lmstudio.py not found in ${PROJECT}" >&2
    exit 1
  fi
  if [[ ! -x "${PY}" ]]; then
    echo "ERROR: venv python missing/not executable: ${PY}" >&2
    echo "  Create venv on Studio first, then re-run this script." >&2
    exit 1
  fi
}

unload_agent() {
  # Идемпотентно: отсутствие агента — не ошибка.
  if launchctl print "${DOMAIN}/${LABEL}" &>/dev/null; then
    launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
  fi
  # Наследие launchctl load/unload (старые macOS) — ignore.
  launchctl unload "${PLIST}" 2>/dev/null || true
}

write_plist() {
  mkdir -p "${HOME}/Library/LaunchAgents" \
           "${LOG_DIR}" \
           "${PROJECT}/data/memory" \
           "${PROJECT}/data/chroma"

  local tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/${LABEL}.plist.XXXXXX")"

  # HF offline: BGE-M3 уже в локальном HF/transformers cache на Studio;
  # без offline SentenceTransformer может висеть на Hub (см. serve_lmstudio.py).
  cat > "${tmp}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>WorkingDirectory</key>
  <string>${PROJECT}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PY}</string>
    <string>-m</string>
    <string>uvicorn</string>
    <string>serve_lmstudio:app</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>8000</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>${HOME}</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/bin:/bin</string>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
    <key>KREPOST_ENABLE_MEMORY</key>
    <string>1</string>
    <key>KREPOST_ENABLE_AGENT</key>
    <string>1</string>
    <key>KREPOST_ENABLE_EPISODIC</key>
    <string>1</string>
    <key>KREPOST_ENABLE_MEMORY_ROUTER</key>
    <string>1</string>
    <key>KREPOST_ENABLE_HYBRID</key>
    <string>1</string>
    <key>KREPOST_ENABLE_HIERARCHICAL_RAG</key>
    <string>1</string>
    <key>KREPOST_ENABLE_HEALTHCLAW</key>
    <string>1</string>
    <key>KREPOST_MAIN_MODEL</key>
    <string>qwen/qwen3.6-35b-a3b</string>
    <key>KREPOST_GUARD_MODEL</key>
    <string>qwen3guard-gen-4b</string>
    <key>KREPOST_LMSTUDIO_URL</key>
    <string>http://127.0.0.1:1234/v1</string>
    <key>KREPOST_VAULT</key>
    <string>${PROJECT}/vault</string>
    <key>KREPOST_CHROMA_DIR</key>
    <string>${PROJECT}/data/chroma</string>
    <key>KREPOST_EPISODIC_DIR</key>
    <string>${PROJECT}/data/memory</string>
    <key>HF_HUB_OFFLINE</key>
    <string>1</string>
    <key>TRANSFORMERS_OFFLINE</key>
    <string>1</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/serve_launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/serve_launchd.err.log</string>
</dict>
</plist>
EOF

  # Атомарная замена — повторный запуск не оставляет битый plist.
  mv -f "${tmp}" "${PLIST}"
  chmod 644 "${PLIST}"
}

stop_orphan_uvicorn() {
  # Только процесс боевого serve_lmstudio на :8000, не sandbox Air.
  # Не падаем, если ничего нет.
  if pgrep -f "uvicorn serve_lmstudio:app" >/dev/null 2>&1; then
    pkill -f "uvicorn serve_lmstudio:app" 2>/dev/null || true
    sleep 1
  fi
}

load_agent() {
  unload_agent
  stop_orphan_uvicorn
  launchctl bootstrap "${DOMAIN}" "${PLIST}"
  launchctl enable "${DOMAIN}/${LABEL}" 2>/dev/null || true
  launchctl kickstart -k "${DOMAIN}/${LABEL}"
}

probe_health() {
  # BGE cold-start может занять десятки секунд — не fail скрипт.
  local i
  for i in 1 2 3 4 5 6; do
    if curl -sf --max-time 5 "http://127.0.0.1:8000/health" >/tmp/krepost_health.$$ 2>/dev/null; then
      echo "health ok:"
      cat /tmp/krepost_health.$$
      rm -f /tmp/krepost_health.$$
      return 0
    fi
    sleep 5
  done
  rm -f /tmp/krepost_health.$$
  echo "health pending (BGE loading? check ${LOG_DIR}/serve_launchd.err.log)"
  return 0
}

echo "=== Krepost LaunchAgent ==="
echo "label:   ${LABEL}"
echo "project: ${PROJECT}"
echo "plist:   ${PLIST}"
echo "python:  ${PY}"
echo "logs:    ${LOG_DIR}/serve_launchd.{out,err}.log"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "(dry-run) skip write/bootstrap"
  exit 0
fi

preflight

if [[ "${UNLOAD_ONLY}" -eq 1 ]]; then
  unload_agent
  echo "unloaded: ${LABEL}"
  exit 0
fi

write_plist
load_agent
echo "launchd installed: ${LABEL}"
probe_health
