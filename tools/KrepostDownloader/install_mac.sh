#!/bin/bash
# Copies app.py + core into Resources and marks the .app executable.
# Run once after clone on MacBook:
#   ./tools/KrepostDownloader/install_mac.sh

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HERE/KrepostDownloader.app"
RES="$APP/Contents/Resources"
MACOS="$APP/Contents/MacOS"

mkdir -p "$RES" "$MACOS"
cp -f "$HERE/app.py" "$HERE/downloader_core.py" "$RES/"
chmod +x "$MACOS/KrepostDownloader"

# Clear quarantine so Gatekeeper allows double-click after download from git
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

echo "Готово: откройте $APP"
echo "Можно перетащить .app в /Applications или держать в папке проекта."
echo "Папка загрузок по умолчанию: ~/Downloads (смените в окне)."
echo "Для моделей Атакера укажите: /Volumes/AtakerDirty/Ataker/models/"
