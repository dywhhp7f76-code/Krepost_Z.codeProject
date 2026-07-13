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

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MAIN_MODEL = "qwen3.6:27b"
DEFAULT_TRUST_DB = Path("data/trust_registry.db")


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
) -> tuple[SecurityPipeline, Any]:
    """(pipeline, transport). guard_client — OpenAIGuardClient на том же
    transport, что и main-бэкенд (один сервер, разные имена моделей)."""
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
) -> Orchestrator:
    api_key = _resolve_openai_api_key(api_key)
    pipeline, transport = build_openai_pipeline(
        base_url=base_url, api_key=api_key, trust_db_path=trust_db_path,
        embedder=embedder, chroma_collection=chroma_collection, transport=transport,
    )
    backend = OpenAIBackend(main_model, base_url=base_url, api_key=api_key,
                            transport=transport, options=options)
    router = Router(list(routes or []), default=Route("main", backend))
    return Orchestrator(pipeline, router)


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
) -> ToolAgent:
    api_key = _resolve_openai_api_key(api_key)
    pipeline, transport = build_openai_pipeline(
        base_url=base_url, api_key=api_key, trust_db_path=trust_db_path,
        embedder=embedder, chroma_collection=chroma_collection, transport=transport,
    )
    backend = OpenAIBackend(main_model, base_url=base_url, api_key=api_key,
                            transport=transport, options=options)
    return ToolAgent(pipeline, backend, ToolRegistry(tools), max_iters=max_iters)
