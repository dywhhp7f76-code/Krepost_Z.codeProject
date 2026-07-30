#!/bin/bash
# Собирает .app и ставит ярлык в ~/Applications — тогда Spotlight / Finder находят.
#
#   cd /path/to/Krepost_Z.codeProject
#   git checkout cursor/gui-download-manager-e5ae   # или main после merge
#   ./tools/KrepostDownloader/install_mac.sh
#   open ~/Applications/Krepost\ Downloader.app

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HERE/KrepostDownloader.app"
RES="$APP/Contents/Resources"
MACOS="$APP/Contents/MacOS"
DEST_DIR="${HOME}/Applications"
DEST_APP="${DEST_DIR}/Krepost Downloader.app"

mkdir -p "$RES" "$MACOS" "$DEST_DIR"
cp -f "$HERE/app.py" "$HERE/downloader_core.py" "$RES/"
if [[ -f "$HERE/assets/AppIcon.icns" ]]; then
  cp -f "$HERE/assets/AppIcon.icns" "$RES/AppIcon.icns"
fi
if [[ -f "$HERE/assets/icon.png" ]]; then
  cp -f "$HERE/assets/icon.png" "$RES/AppIcon.png"
fi
chmod +x "$MACOS/KrepostDownloader"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
touch "$APP"

# Копия в ~/Applications (Spotlight индексирует «Программы»)
rm -rf "$DEST_APP"
ditto "$APP" "$DEST_APP"
xattr -dr com.apple.quarantine "$DEST_APP" 2>/dev/null || true
chmod +x "$DEST_APP/Contents/MacOS/KrepostDownloader"

echo ""
echo "✅ Установлено:"
echo "   $DEST_APP"
echo ""
echo "Открыть сейчас:"
echo "   open \"$DEST_APP\""
echo ""
echo "В Finder: Программы → папка Applications в домашней папке"
echo "   (или Spotlight: «Krepost Downloader»)"
echo ""
echo "Если Spotlight ещё пусто — подождите минуту или:"
echo "   mdimport \"$DEST_APP\""
echo ""
open "$DEST_APP" 2>/dev/null || true
