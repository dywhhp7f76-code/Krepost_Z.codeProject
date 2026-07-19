#!/usr/bin/env python3
"""
serve_lmstudio.py — БОЕВОЙ HTTP-сервер Крепости поверх LM Studio.

    /v1/query  — security → RAG → LLM → episodic
    /v1/agent  — security → tool-loop (fetch / memory_search / vault_read) → episodic

Модели (LM Studio, 127.0.0.1:1234):
    main  = qwen/qwen3.6-35b-a3b
    guard = qwen3guard-gen-4b

Запуск:
    KREPOST_ENABLE_MEMORY=1 KREPOST_ENABLE_AGENT=1 KREPOST_ENABLE_EPISODIC=1 \\
    KREPOST_ENABLE_MEMORY_ROUTER=1 \\
      uvicorn serve_lmstudio:app --host 0.0.0.0 --port 8000

Phase 3 MemoryRouter: domain route → per-domain retrieve → ScoreReranker.
Phase 4 HierarchicalDomainRAG (opt-in):
    KREPOST_ENABLE_HIERARCHICAL_RAG=1
    → DomainRouter → SearchBrief → DomainScout[] → ContextReader[] →
      EvidenceGrader → loop → Supervisor (main LLM).
    При Hierarchical=1 MemoryRouter-обёртка не ставится (Phase 4 путь выше).

CrossEncoder: KREPOST_RERANKER_CROSS_ENCODER=1 (тяжёлый, по умолчанию off).
После включения — переиндексировать vault (metadata.domain): python ingest_vault.py
"""
import os
from pathlib import Path

from krepost.api.app import create_app
from krepost.memory.bge_provider import BGEProvider
from krepost.memory.chroma_factory import (
    env_chroma_dir,
    make_chroma_client,
    make_fewshot_collection,
    make_memory_stack,
)
from krepost.memory.episodic import EpisodicMemory, init_logging
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
ENABLE_EPISODIC = os.environ.get("KREPOST_ENABLE_EPISODIC", "1").lower() not in (
    "0", "false", "no", "off",
)
ENABLE_MEMORY_ROUTER = os.environ.get("KREPOST_ENABLE_MEMORY_ROUTER", "1").lower() not in (
    "0", "false", "no", "off",
)
ENABLE_HIERARCHICAL = os.environ.get(
    "KREPOST_ENABLE_HIERARCHICAL_RAG", "0"
).lower() not in ("0", "false", "no", "off")
USE_RERANKER_CE = os.environ.get("KREPOST_RERANKER_CROSS_ENCODER", "0").lower() not in (
    "0", "false", "no", "off",
)
ENABLE_HYBRID = os.environ.get("KREPOST_ENABLE_HYBRID", "1").lower() not in (
    "0", "false", "no", "off",
)
VAULT = Path(os.environ.get("KREPOST_VAULT", "vault"))
CHROMA_DIR = env_chroma_dir()
EPISODIC_DIR = Path(os.environ.get("KREPOST_EPISODIC_DIR", "data/memory"))

embedder = None
fewshot_col = None
memory_store = None
episodic_memory = None

if ENABLE_MEMORY or ENABLE_AGENT:
    embedder, _mem_col, memory_store = make_memory_stack(chroma_dir=CHROMA_DIR)
    if memory_store is not None and ENABLE_HIERARCHICAL:
        from krepost.memory.hierarchical_rag import wrap_hierarchical_memory

        memory_store = wrap_hierarchical_memory(
            memory_store,
            use_hybrid=ENABLE_HYBRID,
        )
    elif ENABLE_MEMORY_ROUTER and memory_store is not None:
        from krepost.memory.memory_router import wrap_memory_store

        memory_store = wrap_memory_store(
            memory_store,
            use_cross_encoder=USE_RERANKER_CE,
            use_hybrid=ENABLE_HYBRID,
        )
    client = make_chroma_client(CHROMA_DIR)
    fewshot_col = make_fewshot_collection(client)

if ENABLE_EPISODIC and embedder is not None:
    init_logging(Path("data/logs"))
    episodic_memory = EpisodicMemory(
        BGEProvider(embedder),
        base_dir=EPISODIC_DIR,
    )

from krepost.memory.occ_reader import occ_reader_from_env

occ_reader = occ_reader_from_env()

orchestrator = build_openai_orchestrator(
    MAIN_MODEL,
    base_url=BASE_URL,
    guard_model=GUARD_MODEL,
    embedder=embedder,
    chroma_collection=fewshot_col,
    memory_store=memory_store if ENABLE_MEMORY else None,
    episodic_memory=episodic_memory,
    occ_reader=occ_reader,
)

# Supervisor (main LLM) пишет SearchBrief + refine в loop
if (
    ENABLE_HIERARCHICAL
    and memory_store is not None
    and hasattr(memory_store, "set_supervisor_backend")
):
    try:
        _sup_backend = orchestrator.router.default.backend
        memory_store.set_supervisor_backend(_sup_backend)
    except Exception:  # pragma: no cover
        pass
# ContextReader ← OccReader (если включён OCC)
if (
    ENABLE_HIERARCHICAL
    and occ_reader is not None
    and memory_store is not None
    and hasattr(memory_store, "set_occ_reader")
):
    memory_store.set_occ_reader(occ_reader)

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
        episodic_memory=episodic_memory,
    )

title_bits = ["Krepost API (LM Studio"]
if ENABLE_MEMORY:
    title_bits.append("+ memory")
if ENABLE_MEMORY and ENABLE_HIERARCHICAL:
    title_bits.append("+ HierarchicalDomainRAG")
    if memory_store is not None and getattr(memory_store, "brief_drafter", None):
        title_bits.append("+ SupervisorBrief")
elif ENABLE_MEMORY and ENABLE_MEMORY_ROUTER:
    title_bits.append("+ MemoryRouter")
if ENABLE_MEMORY and ENABLE_HYBRID:
    title_bits.append("+ hybrid")
if occ_reader is not None:
    title_bits.append("+ OCC-reader")
if ENABLE_EPISODIC and episodic_memory is not None:
    title_bits.append("+ episodic")
if ENABLE_AGENT:
    title_bits.append("+ agent harness")
title = " ".join(title_bits) + ")"

app = create_app(orchestrator, agent=agent, title=title)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("KREPOST_API_HOST", "0.0.0.0")
    port = int(os.environ.get("KREPOST_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
