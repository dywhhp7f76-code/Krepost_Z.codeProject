"""
krepost/orchestration/factory.py

Сборка боевого стека на Ollama. Один клиент обслуживает и guard (Qwen3Guard,
имя модели фиксировано в GuardClassifier), и main-модель (Qwen3.x) — они
различаются только именем модели в вызове.

На Mac Studio: поднять `ollama serve`, `ollama pull` нужные модели, вызвать
build_ollama_orchestrator()/build_ollama_agent() — остальное уже собрано.
Клиент можно внедрить (тесты); в проде создаётся из host.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Sequence

from krepost.orchestration.ollama_backend import OllamaBackend
from krepost.orchestration.openai_backend import (DEFAULT_BASE_URL,
                                                  OpenAIBackend,
                                                  OpenAIGuardClient)
from krepost.orchestration.orchestrator import Orchestrator
from krepost.orchestration.router import Route, Router
from krepost.orchestration.tools import Tool, ToolAgent, ToolRegistry
from krepost.security.pipeline import SecurityPipeline

try:
    from krepost.memory.chroma_factory import (
        DEFAULT_CHROMA_DIR,
        DEFAULT_FEWSHOT_COLLECTION,
        DEFAULT_MEMORY_COLLECTION,
        make_chroma_client,
        make_fewshot_collection,
        make_memory_stack,
    )
    from krepost.memory.store import MemoryStore
except ImportError:  # pragma: no cover
    make_memory_stack = None  # type: ignore[misc, assignment]
    MemoryStore = Any  # type: ignore[misc, assignment]

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MAIN_MODEL = "qwen3.6:27b"
DEFAULT_TRUST_DB = Path("data/trust_registry.db")

# Имя guard-модели зависит от транспорта:
# - Ollama: "qwen3guard-gen:4b" (дефолт в GuardClassifier);
# - LM Studio / OpenAI-совместимый: "qwen3guard-gen-4b" (дефис, как в LM Studio).
DEFAULT_OPENAI_GUARD_MODEL = "qwen3guard-gen-4b"


def _resolve_openai_api_key(explicit: Optional[str]) -> str:
    """P2 #16: явный аргумент → env KREPOST_OPENAI_API_KEY → фолбэк 'lm-studio'.

    Хардкод 'lm-studio' молча ловил 401 на реальном OpenAI-совместимом сервере
    с авторизацией; теперь ключ приходит из окружения, а локальный LM Studio
    (которому ключ безразличен) продолжает работать по фолбэку.
    """
    return explicit or os.environ.get("KREPOST_OPENAI_API_KEY") or "lm-studio"


def make_ollama_client(host: str = DEFAULT_HOST) -> Any:
    import ollama  # ленивый импорт — только при реальной сборке
    return ollama.Client(host=host)


def build_ollama_pipeline(
    *,
    host: str = DEFAULT_HOST,
    trust_db_path: Path = DEFAULT_TRUST_DB,
    embedder: Any = None,
    chroma_collection: Any = None,
    enable_cache: bool = False,
    client: Any = None,
) -> tuple[SecurityPipeline, Any]:
    """Возвращает (pipeline, client). Клиент общий — его же переиспользуют
    бэкенды. embedder/chroma опциональны (без них Layer 3 просто пропускается)."""
    client = client or make_ollama_client(host)
    pipeline = SecurityPipeline(
        guard_client=client,
        # Layer 4: семантический output-guard ОТКЛЮЧЕН (см. build_openai_pipeline
        # для обоснования). Qwen3Guard не годится для output-classification.
        output_guard_client=None,
        embedder=embedder,
        chroma_collection=chroma_collection,
        trust_db_path=trust_db_path,
        enable_cache=enable_cache,
    )
    return pipeline, client


def build_ollama_orchestrator(
    main_model: str = DEFAULT_MAIN_MODEL,
    *,
    host: str = DEFAULT_HOST,
    routes: Optional[Sequence[Route]] = None,
    trust_db_path: Path = DEFAULT_TRUST_DB,
    embedder: Any = None,
    chroma_collection: Any = None,
    client: Any = None,
    options: Optional[dict] = None,
) -> Orchestrator:
    pipeline, client = build_ollama_pipeline(
        host=host, trust_db_path=trust_db_path, embedder=embedder,
        chroma_collection=chroma_collection, client=client,
    )
    backend = OllamaBackend(main_model, host=host, client=client, options=options)
    router = Router(list(routes or []), default=Route("main", backend))
    return Orchestrator(pipeline, router)


def build_ollama_agent(
    main_model: str = DEFAULT_MAIN_MODEL,
    *,
    tools: Sequence[Tool] = (),
    host: str = DEFAULT_HOST,
    trust_db_path: Path = DEFAULT_TRUST_DB,
    embedder: Any = None,
    chroma_collection: Any = None,
    client: Any = None,
    options: Optional[dict] = None,
    max_iters: int = 6,
) -> ToolAgent:
    pipeline, client = build_ollama_pipeline(
        host=host, trust_db_path=trust_db_path, embedder=embedder,
        chroma_collection=chroma_collection, client=client,
    )
    backend = OllamaBackend(main_model, host=host, client=client, options=options)
    return ToolAgent(pipeline, backend, ToolRegistry(tools), max_iters=max_iters)


# ─────────────────────────────────────────────────────────────────────────
# OpenAI-совместимый стек (LM Studio / vLLM / LocalAI)
# ─────────────────────────────────────────────────────────────────────────

def build_openai_pipeline(
    *,
    base_url: str = DEFAULT_BASE_URL,
    api_key: Optional[str] = None,
    trust_db_path: Path = DEFAULT_TRUST_DB,
    embedder: Any = None,
    chroma_collection: Any = None,
    enable_cache: bool = False,
    transport: Any = None,
    guard_model: str = DEFAULT_OPENAI_GUARD_MODEL,
) -> tuple[SecurityPipeline, Any]:
    """(pipeline, transport). guard_client — OpenAIGuardClient на том же
    transport, что и main-бэкенд (один сервер, разные имена моделей).

    guard_model — имя guard-модели на OpenAI-совместимом сервере
    (LM Studio отдаёт её как "qwen3guard-gen-4b")."""
    api_key = _resolve_openai_api_key(api_key)
    guard = OpenAIGuardClient(base_url=base_url, api_key=api_key, transport=transport)
    pipeline = SecurityPipeline(
        guard_client=guard,
        # Layer 4: семантический output-guard ОТКЛЮЧЕН. Qwen3Guard заточен под
        # классификацию ВХОДОВ (injection-detection); на выходах сваливается в
        # чат-режим → parse_error → ложные блокировки benign. Для air-gapped
        # локалки модерация собственных ответов не нужна: получатель = сам
        # оператор. Layer 4 остаётся regex-only (PII/leak/secret-паттерны).
        output_guard_client=None,
        embedder=embedder,
        chroma_collection=chroma_collection,
        trust_db_path=trust_db_path,
        enable_cache=enable_cache,
        guard_model_name=guard_model,
    )
    return pipeline, guard._transport


def build_openai_orchestrator(
    main_model: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    api_key: Optional[str] = None,
    routes: Optional[Sequence[Route]] = None,
    trust_db_path: Path = DEFAULT_TRUST_DB,
    embedder: Any = None,
    chroma_collection: Any = None,
    transport: Any = None,
    options: Optional[dict] = None,
    guard_model: str = DEFAULT_OPENAI_GUARD_MODEL,
    memory_store: Optional[Any] = None,
    vault_name: str = "Krepost",
    episodic_memory: Optional[Any] = None,
    occ_reader: Optional[Any] = None,
) -> Orchestrator:
    api_key = _resolve_openai_api_key(api_key)
    pipeline, transport = build_openai_pipeline(
        base_url=base_url, api_key=api_key, trust_db_path=trust_db_path,
        embedder=embedder, chroma_collection=chroma_collection, transport=transport,
        guard_model=guard_model,
    )
    backend = OpenAIBackend(main_model, base_url=base_url, api_key=api_key,
                            transport=transport, options=options)
    router = Router(list(routes or []), default=Route("main", backend))
    return Orchestrator(
        pipeline, router,
        memory_store=memory_store,
        vault_name=vault_name,
        episodic_memory=episodic_memory,
        occ_reader=occ_reader,
    )


def build_vllm_orchestrator(
    main_model: str,
    *,
    base_url: str = "http://127.0.0.1:8001/v1",
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> Orchestrator:
    """Алиас OpenAI-стека под vLLM (тот же OpenAIBackend, другие дефолты URL).

    vLLM: `vllm serve <model> --port 8001 --enable-auto-tool-choice --tool-call-parser ...`
    См. scripts/vllm_serve.example.sh
    """
    return build_openai_orchestrator(
        main_model, base_url=base_url, api_key=api_key or "EMPTY", **kwargs,
    )


def build_openai_orchestrator_with_memory(
    main_model: str,
    *,
    chroma_dir: Path = DEFAULT_CHROMA_DIR,
    memory_collection: str = DEFAULT_MEMORY_COLLECTION,
    fewshot_collection: str = DEFAULT_FEWSHOT_COLLECTION,
    enable_memory_router: bool = False,
    use_cross_encoder: bool = False,
    **kwargs: Any,
) -> Orchestrator:
    """Боевой стек: BGE-M3 + persistent Chroma (memory + fewshot) + MemoryStore."""
    if make_memory_stack is None:
        raise RuntimeError("memory stack unavailable — install sentence-transformers + chromadb")
    embedder, mem_col, memory_store = make_memory_stack(
        chroma_dir=chroma_dir, collection_name=memory_collection,
    )
    if enable_memory_router:
        from krepost.memory.memory_router import wrap_memory_store

        memory_store = wrap_memory_store(
            memory_store, use_cross_encoder=use_cross_encoder,
        )
    client = make_chroma_client(chroma_dir)
    fewshot_col = make_fewshot_collection(client, fewshot_collection)
    kwargs.setdefault("embedder", embedder)
    kwargs.setdefault("chroma_collection", fewshot_col)
    kwargs.setdefault("memory_store", memory_store)
    return build_openai_orchestrator(main_model, **kwargs)


def build_openai_agent(
    main_model: str,
    *,
    tools: Sequence[Tool] = (),
    base_url: str = DEFAULT_BASE_URL,
    api_key: Optional[str] = None,
    trust_db_path: Path = DEFAULT_TRUST_DB,
    embedder: Any = None,
    chroma_collection: Any = None,
    transport: Any = None,
    options: Optional[dict] = None,
    max_iters: int = 6,
    guard_model: str = DEFAULT_OPENAI_GUARD_MODEL,
    episodic_memory: Optional[Any] = None,
) -> ToolAgent:
    api_key = _resolve_openai_api_key(api_key)
    pipeline, transport = build_openai_pipeline(
        base_url=base_url, api_key=api_key, trust_db_path=trust_db_path,
        embedder=embedder, chroma_collection=chroma_collection, transport=transport,
        guard_model=guard_model,
    )
    backend = OpenAIBackend(main_model, base_url=base_url, api_key=api_key,
                            transport=transport, options=options)
    return ToolAgent(
        pipeline, backend, ToolRegistry(tools), max_iters=max_iters,
        episodic_memory=episodic_memory,
    )


def build_openai_agent_with_harness(
    main_model: str,
    *,
    chroma_dir: Path = DEFAULT_CHROMA_DIR,
    memory_collection: str = DEFAULT_MEMORY_COLLECTION,
    fewshot_collection: str = DEFAULT_FEWSHOT_COLLECTION,
    vault_root: Path = Path("vault"),
    max_iters: int = 6,
    **kwargs: Any,
) -> ToolAgent:
    """Боевой агент: security + RAG-память + fetch/memory_search/vault_read."""
    if make_memory_stack is None:
        raise RuntimeError("memory stack unavailable — install sentence-transformers + chromadb")
    from krepost.orchestration.harness_tools import build_default_harness_tools

    embedder, _mem_col, memory_store = make_memory_stack(
        chroma_dir=chroma_dir, collection_name=memory_collection,
    )
    client = make_chroma_client(chroma_dir)
    fewshot_col = make_fewshot_collection(client, fewshot_collection)
    tools = build_default_harness_tools(
        memory_store=memory_store, vault_root=vault_root,
    )
    kwargs.setdefault("embedder", embedder)
    kwargs.setdefault("chroma_collection", fewshot_col)
    kwargs.setdefault("tools", tools)
    kwargs.setdefault("max_iters", max_iters)
    return build_openai_agent(main_model, **kwargs)
