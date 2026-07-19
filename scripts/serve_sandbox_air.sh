#!/usr/bin/env bash
# Песочница Крепости на Air — порт 8010, localhost only.
# Боевой Studio (:8000 / launchd) НЕ трогает.
#
# Док: _handoff/SANDBOX_ZOO_AIR.md
#
# Перед запуском: LM Studio на 127.0.0.1:1234 с нужной GGUF.
# Смена модели: KREPOST_MAIN_MODEL=... ./scripts/serve_sandbox_air.sh
#
# Ataker → http://127.0.0.1:8010  (не 10.0.0.1:8000)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${KREPOST_SANDBOX_PORT:-8010}"
HOST="${KREPOST_SANDBOX_HOST:-127.0.0.1}"

export KREPOST_LMSTUDIO_URL="${KREPOST_LMSTUDIO_URL:-http://127.0.0.1:1234/v1}"
export KREPOST_MAIN_MODEL="${KREPOST_MAIN_MODEL:-qwen/qwen3.6-35b-a3b}"
export KREPOST_GUARD_MODEL="${KREPOST_GUARD_MODEL:-qwen3guard-gen-4b}"

# Изоляция от боевых data/ на Studio
export KREPOST_CHROMA_DIR="${KREPOST_CHROMA_DIR:-$ROOT/data/chroma_sandbox}"
export KREPOST_EPISODIC_DIR="${KREPOST_EPISODIC_DIR:-$ROOT/data/memory_sandbox}"
export KREPOST_VAULT="${KREPOST_VAULT:-$ROOT/vault_sandbox}"

export KREPOST_ENABLE_MEMORY="${KREPOST_ENABLE_MEMORY:-1}"
export KREPOST_ENABLE_AGENT="${KREPOST_ENABLE_AGENT:-1}"
export KREPOST_ENABLE_EPISODIC="${KREPOST_ENABLE_EPISODIC:-1}"
export KREPOST_ENABLE_MEMORY_ROUTER="${KREPOST_ENABLE_MEMORY_ROUTER:-1}"
export KREPOST_ENABLE_HYBRID="${KREPOST_ENABLE_HYBRID:-1}"
# Phase 4 в песочнице по умолчанию ON (Studio launchd — сам решишь)
export KREPOST_ENABLE_HIERARCHICAL_RAG="${KREPOST_ENABLE_HIERARCHICAL_RAG:-1}"

mkdir -p "$KREPOST_CHROMA_DIR" "$KREPOST_EPISODIC_DIR" "$KREPOST_VAULT" "$ROOT/data/logs"

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi

UVICORN="${ROOT}/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN" ]]; then
  UVICORN="$(command -v uvicorn || true)"
fi
if [[ -z "${UVICORN}" ]]; then
  echo "❌ uvicorn не найден. Активируй .venv в $ROOT" >&2
  exit 1
fi

echo "🧪 Krepost SANDBOX (Air)"
echo "   host=$HOST port=$PORT"
echo "   LM Studio=$KREPOST_LMSTUDIO_URL"
echo "   main=$KREPOST_MAIN_MODEL guard=$KREPOST_GUARD_MODEL"
echo "   chroma=$KREPOST_CHROMA_DIR"
echo "   episodic=$KREPOST_EPISODIC_DIR"
echo "   vault=$KREPOST_VAULT"
echo "   Ataker → http://${HOST}:${PORT}"
echo

exec "$UVICORN" serve_lmstudio:app --host "$HOST" --port "$PORT"
