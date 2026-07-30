#!/bin/bash
# Копирует офлайн-плагины на SSD Ataker (Mac).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SSD_ROOT="${ATAKER_SSD:-/Volumes/AtakerDirty/Ataker}"
DEST="${SSD_ROOT}/плагины обсидиан"

if [[ ! -d "${SSD_ROOT}" ]]; then
  echo "SSD не смонтирован: ${SSD_ROOT}"
  echo "Подключи AtakerDirty или: ATAKER_SSD=/путь/к/тому/Ataker $0"
  exit 1
fi

mkdir -p "${DEST}"
if command -v rsync >/dev/null 2>&1; then
  rsync -a "${HERE}/" "${DEST}/" --exclude 'install_to_ssd.sh'
else
  cp -a "${HERE}/." "${DEST}/"
fi
echo "✅ Плагины → ${DEST}"
ls "${DEST}/plugins"
