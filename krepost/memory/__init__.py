"""
krepost.memory — RAG-слой базы знаний (этап memory, ARCHITECTURE_VISION §2).
"""
from krepost.memory.chunker import chunk_text
from krepost.memory.context_reader import ContextReader
from krepost.memory.domain_router import DomainRouter
from krepost.memory.domain_scout import DomainScout
from krepost.memory.episodic import EpisodicMemory, SecurityVerdict
from krepost.memory.evidence_grader import EvidenceGrader
from krepost.memory.hierarchical_rag import (
    HierarchicalDomainRAG,
    HierarchicalMemoryFacade,
    wrap_hierarchical_memory,
)
from krepost.memory.memory_router import MemoryRouter, wrap_memory_store
from krepost.memory.search_brief import (
    GradeVerdict,
    ReaderDossier,
    ScoutHit,
    SearchBrief,
)
from krepost.memory.store import (
    AddResult,
    MemoryStore,
    RetrievalResult,
    RetrievedChunk,
)

__all__ = [
    "chunk_text",
    "ContextReader",
    "DomainRouter",
    "DomainScout",
    "EpisodicMemory",
    "EvidenceGrader",
    "GradeVerdict",
    "HierarchicalDomainRAG",
    "HierarchicalMemoryFacade",
    "MemoryRouter",
    "wrap_hierarchical_memory",
    "MemoryStore",
    "AddResult",
    "ReaderDossier",
    "RetrievedChunk",
    "RetrievalResult",
    "ScoutHit",
    "SearchBrief",
    "SecurityVerdict",
    "wrap_memory_store",
]
