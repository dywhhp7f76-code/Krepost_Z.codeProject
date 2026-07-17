#!/usr/bin/env bash
# Пример запуска vLLM как OpenAI-совместимого backend для Крепости (Studio).
# Не ставит пакеты сам — только шаблон. LM Studio остаётся дефолтом.
#
#   brew/pip: pip install vllm   # на Linux GPU; на Mac Apple Silicon часто
#   лучше mlx-lm / LM Studio. vLLM на macOS ограничен — проверяй релиз.
#
# Крепость:
#   KREPOST_LMSTUDIO_URL=http://127.0.0.1:8001/v1 \
#   KREPOST_MAIN_MODEL=<served-model-name> \
#     uvicorn serve_lmstudio:app --host 0.0.0.0 --port 8000
#
# Или: from krepost.orchestration.factory import build_vllm_orchestrator

set -euo pipefail
MODEL="${VLLM_MODEL:-Qwen/Qwen3-32B-AWQ}"
PORT="${VLLM_PORT:-8001}"

exec vllm serve "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype auto \
  --max-model-len "${VLLM_MAX_LEN:-32768}" \
  --gpu-memory-utilization "${VLLM_GPU_UTIL:-0.90}" \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
