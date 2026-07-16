#!/usr/bin/env python3
"""
serve_lmstudio.py — БОЕВОЙ HTTP-сервер Крепости поверх LM Studio.

    /v1/query  — security → RAG → LLM
    /v1/agent  — security → tool-loop (fetch / memory_search / vault_read)

Модели (LM Studio, 127.0.0.1:1234):
    main  = qwen/qwen3.6-35b-a3b
    guard = qwen3guard-gen-4b

Запуск:
    KREPOST_ENABLE_MEMORY=1 KREPOST_ENABLE_AGENT=1 \\
      uvicorn serve_lmstudio:app --host 0.0.0.0 --port 8000
"""
import os
from pathlib import Path

from krepost.api.app import create_app
from krepost.memory.chroma_factory import (
    env_chroma_dir,
    make_chroma_client,
    make_fewshot_collection,
    make_memory_stack,
)
from krepost.orchestration.factory import (
    build_openai_agent,
    build_openai_orchestrator,
)
from krepost.orchestration.harness_tools import build_default_harness_tools

MAIN_MODEL = os.environ.get("KREPOST_MAIN_MODEL", "qwen/qwen3.6-35b-a3b")
GUARD_MODEL = os.environ.get("KREPOST_GUARD_MODEL", "qwen3guard-gen-4b")
BASE_URL = os.environ.get("KREPOST_LMSTUDIO_URL", "http://127.0.0.1:1234/v1")
ENABLE_MEMORY = os.environ.get("KREPOST_ENABLE_MEMORY", "1").lower() not in (
    "0", "false", "no", "off",
)
ENABLE_AGENT = os.environ.get("KREPOST_ENABLE_AGENT", "1").lower() not in (
    "0", "false", "no", "off",
)
VAULT = Path(os.environ.get("KREPOST_VAULT", "vault"))
CHROMA_DIR = env_chroma_dir()

embedder = None
fewshot_col = None
memory_store = None

if ENABLE_MEMORY or ENABLE_AGENT:
    embedder, _mem_col, memory_store = make_memory_stack(chroma_dir=CHROMA_DIR)
    client = make_chroma_client(CHROMA_DIR)
    fewshot_col = make_fewshot_collection(client)

orchestrator = build_openai_orchestrator(
    MAIN_MODEL,
    base_url=BASE_URL,
    guard_model=GUARD_MODEL,
    embedder=embedder,
    chroma_collection=fewshot_col,
    memory_store=memory_store if ENABLE_MEMORY else None,
)

agent = None
if ENABLE_AGENT:
    tools = build_default_harness_tools(
        memory_store=memory_store,
        vault_root=VAULT,
    )
    agent = build_openai_agent(
        MAIN_MODEL,
        tools=tools,
        base_url=BASE_URL,
        guard_model=GUARD_MODEL,
        embedder=embedder,
        chroma_collection=fewshot_col,
    )

title_bits = ["Krepost API (LM Studio"]
if ENABLE_MEMORY:
    title_bits.append("+ memory")
if ENABLE_AGENT:
    title_bits.append("+ agent harness")
title = " ".join(title_bits) + ")"

app = create_app(orchestrator, agent=agent, title=title)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("KREPOST_API_HOST", "0.0.0.0")
    port = int(os.environ.get("KREPOST_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
