"""
krepost.memory — RAG-слой базы знаний (этап memory, ARCHITECTURE_VISION §2).
"""
from krepost.memory.chunker import chunk_text
from krepost.memory.store import (
    AddResult,
    MemoryStore,
    RetrievalResult,
    RetrievedChunk,
)

__all__ = [
    "chunk_text",
    "MemoryStore",
    "AddResult",
    "RetrievedChunk",
    "RetrievalResult",
]
