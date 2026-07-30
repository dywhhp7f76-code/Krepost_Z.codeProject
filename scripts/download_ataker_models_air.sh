#!/usr/bin/env bash
# Подготовка (не бой): скачать Planner + Executor GGUF на AtakerDirty.
#
#   bash scripts/download_ataker_models_air.sh           # оба
#   bash scripts/download_ataker_models_air.sh --planner
#   bash scripts/download_ataker_models_air.sh --executor
#   bash scripts/download_ataker_models_air.sh --dry-run
#
# Planner:  RavichandranJ/Dolphin3-Cyber-8B-GGUF  Q4_K_M
# Executor: QuantFactory/Llama-3.2-3B-Instruct-abliterated-GGUF  Q4_K_M
set -euo pipefail

PLANNER_REPO="${ATAKER_PLANNER_HF_REPO:-RavichandranJ/Dolphin3-Cyber-8B-GGUF}"
PLANNER_FILE="${ATAKER_PLANNER_GGUF:-Dolphin3.0-Llama3.1-8B-abliterated.Q4_K_M.gguf}"
EXECUTOR_REPO="${ATAKER_EXECUTOR_HF_REPO:-QuantFactory/Llama-3.2-3B-Instruct-abliterated-GGUF}"
EXECUTOR_FILE="${ATAKER_EXECUTOR_GGUF:-Llama-3.2-3B-Instruct-abliterated.Q4_K_M.gguf}"

SSD_LINK="${HOME}/Ataker-SSD"
VOL_MODELS="/Volumes/AtakerDirty/Ataker/models"
DRY=0
DO_PLANNER=0
DO_EXECUTOR=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --planner) DO_PLANNER=1 ;;
    --executor) DO_EXECUTOR=1 ;;
    -h|--help)
      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
  esac
done

# default: both
if [[ "$DO_PLANNER" == "0" && "$DO_EXECUTOR" == "0" ]]; then
  DO_PLANNER=1
  DO_EXECUTOR=1
fi

if [[ -d "$VOL_MODELS" ]]; then
  DEST="$VOL_MODELS"
elif [[ -d "$SSD_LINK/models" ]]; then
  DEST="$SSD_LINK/models"
elif [[ -L "$SSD_LINK" || -d "$SSD_LINK" ]]; then
  DEST="$SSD_LINK/models"
else
  DEST="$VOL_MODELS"
fi

echo "dest: ${DEST}"
echo "planner:  ${PLANNER_REPO} / ${PLANNER_FILE}  (do=${DO_PLANNER})"
echo "executor: ${EXECUTOR_REPO} / ${EXECUTOR_FILE}  (do=${DO_EXECUTOR})"

if [[ "$DRY" == "1" ]]; then
  echo "(dry-run) готовка моделей — бой не запускается"
  exit 0
fi

if [[ ! -d "/Volumes/AtakerDirty" && ! -e "$SSD_LINK" ]]; then
  echo "ERROR: AtakerDirty не смонтирован." >&2
  echo "  Ожидаю: $VOL_MODELS или $SSD_LINK/models" >&2
  exit 1
fi

mkdir -p "$DEST"

_download() {
  local repo="$1" file="$2"
  local out="${DEST}/${file}"
  if [[ -f "$out" ]]; then
    ls -lh "$out"
    echo "уже есть: $file"
    return 0
  fi
  echo "качаю ${repo} :: ${file}"
  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$repo" "$file" --local-dir "$DEST" --local-dir-use-symlinks False
  elif command -v hf >/dev/null 2>&1; then
    hf download "$repo" "$file" --local-dir "$DEST"
  else
    python3 -m pip install -q --user "huggingface_hub" 2>/dev/null || python3 -m pip install -q "huggingface_hub"
    python3 -c "
from huggingface_hub import hf_hub_download
print(hf_hub_download(repo_id='${repo}', filename='${file}', local_dir='${DEST}'))
"
  fi
  if [[ ! -f "$out" ]]; then
    found="$(find "$DEST" -name "$file" -type f 2>/dev/null | head -1 || true)"
    if [[ -n "$found" && "$found" != "$out" ]]; then
      ln -sf "$found" "$out" || cp -n "$found" "$out"
    fi
  fi
  [[ -f "$out" ]] || { echo "ERROR: нет файла $out" >&2; exit 2; }
  ls -lh "$out"
}

[[ "$DO_PLANNER" == "1" ]] && _download "$PLANNER_REPO" "$PLANNER_FILE"
[[ "$DO_EXECUTOR" == "1" ]] && _download "$EXECUTOR_REPO" "$EXECUTOR_FILE"

echo ""
echo "✅ Готовка файлов на SSD. Дальше (ещё не бой):"
echo "  1. LM Studio → Load Planner (+ Executor)"
echo "  2. Local Server :1234 → export ATAKER_PLANNER_MODEL / ATAKER_EXECUTOR_MODEL / ATAKER_JUDGE_MODEL"
echo "  3. curl …/v1/models — оба id видны"
echo "  4. Только потом: serve_sandbox_air + smoke (отдельная команда)"
