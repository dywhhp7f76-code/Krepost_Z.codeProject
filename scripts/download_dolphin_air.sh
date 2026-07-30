#!/usr/bin/env bash
# Скачать attacker/judge GGUF на AtakerDirty (только Air / dirty-zone).
#
# Модель: RavichandranJ/Dolphin3-Cyber-8B-GGUF  Q4_K_M (~4.9 GB)
# Куда:   /Volumes/AtakerDirty/Ataker/models/  (ярлык ~/Ataker-SSD/models)
#
#   bash scripts/download_dolphin_air.sh
#   bash scripts/download_dolphin_air.sh --dry-run
#
# Требует: смонтированный AtakerDirty, сеть, huggingface-cli или curl+HF.
# НЕ писать на том Time Machine «WD_BLACK Атакер».
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HF_REPO="${ATAKER_HF_REPO:-RavichandranJ/Dolphin3-Cyber-8B-GGUF}"
GGUF_NAME="${ATAKER_GGUF_NAME:-Dolphin3.0-Llama3.1-8B-abliterated.Q4_K_M.gguf}"
SSD_LINK="${HOME}/Ataker-SSD"
VOL_MODELS="/Volumes/AtakerDirty/Ataker/models"
DRY=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    -h|--help)
      sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
  esac
done

if [[ -d "$VOL_MODELS" ]]; then
  DEST="$VOL_MODELS"
elif [[ -d "$SSD_LINK/models" ]]; then
  DEST="$SSD_LINK/models"
elif [[ -L "$SSD_LINK" || -d "$SSD_LINK" ]]; then
  DEST="$SSD_LINK/models"
else
  DEST="$VOL_MODELS"
fi

OUT="${DEST}/${GGUF_NAME}"
echo "HF:   ${HF_REPO}"
echo "file: ${GGUF_NAME}"
echo "dest: ${OUT}"

if [[ "$DRY" == "1" ]]; then
  echo "(dry-run) скачал бы ${GGUF_NAME} → ${OUT}"
  exit 0
fi

if [[ ! -d "$(dirname "$DEST")" && ! -d "$DEST" ]]; then
  if [[ ! -d "/Volumes/AtakerDirty" && ! -e "$SSD_LINK" ]]; then
    echo "ERROR: AtakerDirty не смонтирован." >&2
    echo "  Ожидаю: $VOL_MODELS  или  $SSD_LINK/models" >&2
    echo "  Подключи том AtakerDirty (не WD_BLACK Атакер / Time Machine)." >&2
    exit 1
  fi
fi

if [[ -f "$OUT" ]]; then
  ls -lh "$OUT"
  echo "Уже есть — ничего не качаю. Load в LM Studio → Local Server :1234"
  exit 0
fi

mkdir -p "$DEST"

if command -v huggingface-cli >/dev/null 2>&1; then
  huggingface-cli download "$HF_REPO" "$GGUF_NAME" --local-dir "$DEST" --local-dir-use-symlinks False
elif command -v hf >/dev/null 2>&1; then
  hf download "$HF_REPO" "$GGUF_NAME" --local-dir "$DEST"
else
  echo "Ставлю huggingface_hub в user site…"
  python3 -m pip install -q --user "huggingface_hub[cli]" || python3 -m pip install -q "huggingface_hub"
  python3 - <<PY
from huggingface_hub import hf_hub_download
import shutil, os
path = hf_hub_download(
    repo_id="${HF_REPO}",
    filename="${GGUF_NAME}",
    local_dir="${DEST}",
)
print("downloaded:", path)
PY
fi

if [[ ! -f "$OUT" ]]; then
  # hf may nest under repo name
  found="$(find "$DEST" -name "$GGUF_NAME" -type f 2>/dev/null | head -1 || true)"
  if [[ -n "$found" && "$found" != "$OUT" ]]; then
    ln -sf "$found" "$OUT" || cp -n "$found" "$OUT"
  fi
fi

[[ -f "$OUT" ]] || { echo "ERROR: файл не появился: $OUT" >&2; exit 2; }
ls -lh "$OUT"
echo ""
echo "Дальше:"
echo "  1. LM Studio → Load → $OUT"
echo "  2. Local Server → http://127.0.0.1:1234/v1"
echo "  3. export ATAKER_JUDGE_URL=http://127.0.0.1:1234"
echo "     export ATAKER_JUDGE_MODEL=<id из LM Studio>"
echo "  4. ./scripts/serve_sandbox_air.sh"
echo "     JUDGE=1 LIMIT=5 ./scripts/ataker_sandbox_air.sh"
