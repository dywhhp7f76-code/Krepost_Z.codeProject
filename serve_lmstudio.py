#!/usr/bin/env python3
"""
serve_lmstudio.py — БОЕВОЙ HTTP-сервер Крепости поверх LM Studio.

В отличие от krepost.api.server (демо с dev-guard, пропускающим всё), здесь
собирается реальный стек: main-модель + настоящий Qwen3Guard + RAG (MemoryStore).

    HTTP → Orchestrator.handle (Security → RAG → Router → LLM → Security) → JSON

Модели (LM Studio, 127.0.0.1:1234, без авторизации):
    main  = qwen/qwen3.6-35b-a3b
    guard = qwen3guard-gen-4b

Запуск:
    uvicorn serve_lmstudio:app --host 0.0.0.0 --port 8000

Переопределение через окружение:
    KREPOST_MAIN_MODEL, KREPOST_GUARD_MODEL, KREPOST_LMSTUDIO_URL
    KREPOST_ENABLE_MEMORY=0 — отключить RAG (только security+LLM)
    KREPOST_CHROMA_DIR — путь к persistent Chroma
"""
import os

from krepost.api.app import create_app
from krepost.orchestration.factory import (
    build_openai_orchestrator,
    build_openai_orchestrator_with_memory,
)

MAIN_MODEL = os.environ.get("KREPOST_MAIN_MODEL", "qwen/qwen3.6-35b-a3b")
GUARD_MODEL = os.environ.get("KREPOST_GUARD_MODEL", "qwen3guard-gen-4b")
BASE_URL = os.environ.get("KREPOST_LMSTUDIO_URL", "http://127.0.0.1:1234/v1")
ENABLE_MEMORY = os.environ.get("KREPOST_ENABLE_MEMORY", "1").lower() not in (
    "0", "false", "no", "off",
)

if ENABLE_MEMORY:
    orchestrator = build_openai_orchestrator_with_memory(
        main_model=MAIN_MODEL,
        base_url=BASE_URL,
        guard_model=GUARD_MODEL,
    )
else:
    orchestrator = build_openai_orchestrator(
        main_model=MAIN_MODEL,
        base_url=BASE_URL,
        guard_model=GUARD_MODEL,
    )

app = create_app(
    orchestrator,
    title="Krepost API (LM Studio, боевой + memory)" if ENABLE_MEMORY
    else "Krepost API (LM Studio, боевой)",
)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("KREPOST_API_HOST", "0.0.0.0")
    port = int(os.environ.get("KREPOST_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
