#!/bin/bash
# Удаляет старые копии Krepost Downloader и ставит свежую из этой ветки.
# Запуск на MacBook Air, из корня репо:
#   ./tools/KrepostDownloader/reinstall_mac.sh

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

echo "→ Репо: $REPO"
cd "$REPO"

# Подтянуть последние фиксы UI (пустое окно)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git fetch origin cursor/gui-download-manager-e5ae 2>/dev/null || true
  git checkout cursor/gui-download-manager-e5ae 2>/dev/null || true
  git pull --ff-only origin cursor/gui-download-manager-e5ae 2>/dev/null || true
fi

echo "→ Удаляю старые копии…"
rm -rf "${HOME}/Applications/Krepost Downloader.app"
rm -rf "${HOME}/Applications/KrepostDownloader.app"
rm -rf "/Applications/Krepost Downloader.app"
rm -rf "/Applications/KrepostDownloader.app"
# старый ярлык внутри репо тоже пересоберём через install
xattr -dr com.apple.quarantine "$HERE/KrepostDownloader.app" 2>/dev/null || true

chmod +x "$HERE/install_mac.sh"
"$HERE/install_mac.sh"

echo ""
echo "✅ Готово. Старое удалено, новое в:"
echo "   ${HOME}/Applications/Krepost Downloader.app"
