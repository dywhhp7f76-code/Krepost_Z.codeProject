#!/bin/bash
# Copies app.py + core + icon into Resources and marks the .app executable.
# Run once after clone on MacBook:
#   ./tools/KrepostDownloader/install_mac.sh

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HERE/KrepostDownloader.app"
RES="$APP/Contents/Resources"
MACOS="$APP/Contents/MacOS"

mkdir -p "$RES" "$MACOS"
cp -f "$HERE/app.py" "$HERE/downloader_core.py" "$RES/"
# Icon: папка → магнит
if [[ -f "$HERE/assets/AppIcon.icns" ]]; then
  cp -f "$HERE/assets/AppIcon.icns" "$RES/AppIcon.icns"
fi
if [[ -f "$HERE/assets/icon.png" ]]; then
  cp -f "$HERE/assets/icon.png" "$RES/AppIcon.png"
fi
chmod +x "$MACOS/KrepostDownloader"

# Clear quarantine so Gatekeeper allows double-click after download from git
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

touch "$APP"

echo "Готово: откройте $APP (иконка: папка, залетающая в магнит)"
echo "Можно перетащить .app в /Applications или держать в папке проекта."
echo "Папка загрузок по умолчанию: ~/Downloads (смените в окне)."
echo "Для моделей Атакера укажите: /Volumes/AtakerDirty/Ataker/models/"
