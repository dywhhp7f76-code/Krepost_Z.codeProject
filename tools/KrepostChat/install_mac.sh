#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HERE/KrepostChat.app"
RES="$APP/Contents/Resources"
MACOS="$APP/Contents/MacOS"
DEST_DIR="${HOME}/Applications"
DEST_APP="${DEST_DIR}/Krepost Chat.app"

mkdir -p "$RES" "$MACOS" "$DEST_DIR" "$APP/Contents"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleName</key><string>KrepostChat</string>
	<key>CFBundleDisplayName</key><string>Krepost Chat</string>
	<key>CFBundleIdentifier</key><string>com.hervam.krepost.chat</string>
	<key>CFBundleVersion</key><string>1.0.0</string>
	<key>CFBundleShortVersionString</key><string>1.0</string>
	<key>CFBundlePackageType</key><string>APPL</string>
	<key>CFBundleExecutable</key><string>KrepostChat</string>
	<key>LSMinimumSystemVersion</key><string>12.0</string>
	<key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
echo -n 'APPL????' > "$APP/Contents/PkgInfo"

cp -f "$HERE/app.py" "$HERE/bridge.py" "$RES/"
cat > "$MACOS/KrepostChat" <<'LAUNCH'
#!/bin/bash
set -euo pipefail
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
pick_python() {
  for c in \
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" \
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" \
    "/opt/homebrew/bin/python3" \
    "/usr/local/bin/python3" \
    "python3"
  do
    bin=""
    if [[ -x "$c" ]]; then bin="$c"
    elif command -v "$c" >/dev/null 2>&1; then bin="$(command -v "$c")"; fi
    [[ -n "$bin" ]] || continue
    if "$bin" -c "import tkinter" 2>/dev/null; then echo "$bin"; return 0; fi
  done
  return 1
}
PY="$(pick_python || true)"
if [[ -z "${PY}" ]]; then
  osascript -e 'display dialog "Нужен Python 3 с Tkinter (python.org или brew install python-tk)" buttons {"OK"} with title "Krepost Chat"'
  exit 1
fi
LOG="${HOME}/Library/Logs/KrepostChat.log"
mkdir -p "$(dirname "$LOG")"
exec "$PY" "$RES/app.py" "$@" >>"$LOG" 2>&1
LAUNCH
chmod +x "$MACOS/KrepostChat"

rm -rf "$DEST_APP"
ditto "$APP" "$DEST_APP"
xattr -dr com.apple.quarantine "$DEST_APP" 2>/dev/null || true
chmod +x "$DEST_APP/Contents/MacOS/KrepostChat"

echo "✅ Krepost Chat → $DEST_APP"
open "$DEST_APP" 2>/dev/null || true
