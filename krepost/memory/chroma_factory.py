"""
krepost/memory/chroma_factory.py

Фабрика embedder + persistent Chroma для RAG и Layer 3 (BGE-M3, cosine).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from krepost.memory.store import MemoryStore
from krepost.security.tool_guard import ToolOutputGuard

DEFAULT_CHROMA_DIR = Path("data/chroma")
DEFAULT_MEMORY_COLLECTION = "krepost_mem"
DEFAULT_FEWSHOT_COLLECTION = "fewshot_attacks"
DEFAULT_EMBED_MODEL = "BAAI/bge-m3"


def make_bge_embedder(model_name: str = DEFAULT_EMBED_MODEL) -> Any:
    """SentenceTransformer BGE-M3 — ленивый импорт, только при боевой сборке."""
    from sentence_transformers import SentenceTransformer

    # Сначала локальный кэш (Studio часто зависает на HF Hub).
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except Exception:
        return SentenceTransformer(model_name)


def make_chroma_client(persist_dir: Path | str = DEFAULT_CHROMA_DIR) -> Any:
    import chromadb

    path = Path(persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def make_chroma_collection(
    client: Any,
    name: str,
    *,
    metadata: Optional[dict] = None,
) -> Any:
    meta = {"hnsw:space": "cosine", **(metadata or {})}
    return client.get_or_create_collection(name=name, metadata=meta)


def make_memory_stack(
    *,
    chroma_dir: Path | str = DEFAULT_CHROMA_DIR,
    collection_name: str = DEFAULT_MEMORY_COLLECTION,
    embed_model: str = DEFAULT_EMBED_MODEL,
    ingest_guard: bool = True,
    min_relevance: float = 0.35,
    confidence_threshold: float = 0.6,
) -> tuple[Any, Any, MemoryStore]:
    """(embedder, collection, MemoryStore) для боевого RAG."""
    embedder = make_bge_embedder(embed_model)
    client = make_chroma_client(chroma_dir)
    collection = make_chroma_collection(client, collection_name)
    guard = ToolOutputGuard() if ingest_guard else None
    store = MemoryStore(
        embedder,
        collection,
        min_relevance=min_relevance,
        confidence_threshold=confidence_threshold,
        ingest_guard=guard,
    )
    return embedder, collection, store


def make_fewshot_collection(
    client: Any,
    name: str = DEFAULT_FEWSHOT_COLLECTION,
) -> Any:
    return make_chroma_collection(client, name)


def env_chroma_dir() -> Path:
    return Path(os.environ.get("KREPOST_CHROMA_DIR", DEFAULT_CHROMA_DIR))
