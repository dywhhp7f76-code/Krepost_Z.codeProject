#!/bin/bash
# Установка автозапуска Крепости на Mac Studio (launchd).
set -euo pipefail
PROJECT="${HOME}/ZCodeProject/Krepost_Z.codeProject"
PLIST="${HOME}/Library/LaunchAgents/com.hervam.krepost.serve.plist"
LABEL="com.hervam.krepost.serve"
PY="${PROJECT}/.venv/bin/python"

mkdir -p "${HOME}/Library/LaunchAgents" "${PROJECT}/data/logs"

cat > "${PLIST}" <<EOF
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
    <key>KREPOST_ENABLE_MEMORY</key>
    <string>1</string>
    <key>KREPOST_ENABLE_AGENT</key>
    <string>1</string>
    <key>KREPOST_ENABLE_EPISODIC</key>
    <string>1</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${PROJECT}/data/logs/serve_launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>${PROJECT}/data/logs/serve_launchd.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
pkill -f "uvicorn serve_lmstudio" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$(id -u)" "${PLIST}"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}"
echo "launchd installed: ${LABEL}"
sleep 15
curl -s --max-time 20 http://127.0.0.1:8000/health || echo "health pending (BGE loading?)"
