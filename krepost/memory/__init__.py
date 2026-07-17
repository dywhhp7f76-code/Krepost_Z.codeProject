"""
krepost.memory — RAG-слой базы знаний (этап memory, ARCHITECTURE_VISION §2).
"""
from krepost.memory.chunker import chunk_text
from krepost.memory.domain_router import DomainRouter
from krepost.memory.episodic import EpisodicMemory, SecurityVerdict
from krepost.memory.memory_router import MemoryRouter, wrap_memory_store
from krepost.memory.store import (
    AddResult,
    MemoryStore,
    RetrievalResult,
    RetrievedChunk,
)

__all__ = [
    "chunk_text",
    "DomainRouter",
    "EpisodicMemory",
    "MemoryRouter",
    "MemoryStore",
    "AddResult",
    "RetrievedChunk",
    "RetrievalResult",
    "SecurityVerdict",
    "wrap_memory_store",
]
