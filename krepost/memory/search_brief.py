"""
Контракты HierarchicalDomainRAG (Phase 4) — LOCKED IDs из канона.

См. _handoff/HIERARCHICAL_DOMAIN_RAG_SPEC.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


GradeStatus = Literal["relevant", "partial", "irrelevant"]


@dataclass
class SearchBrief:
    """Задание Supervisor → DomainScout[]. Не ответ пользователю."""

    query_anchors: List[str]
    domains: List[str]
    round: int = 0
    user_query: str = ""

    def __post_init__(self) -> None:
        self.query_anchors = [a.strip() for a in self.query_anchors if a and a.strip()]
        self.domains = [d.strip() for d in self.domains if d and d.strip()]
        if not self.domains:
            raise ValueError("SearchBrief.domains must be 1..K non-empty")


@dataclass
class ScoutHit:
    """Выход DomainScout: адреса/чанки одного domain, не текст юзеру."""

    domain_id: str
    doc_id: str
    paths: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    chunk_ids: List[str] = field(default_factory=list)
    texts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReaderDossier:
    """Выход ContextReader: выжимка + citations. Не финальный ответ."""

    domain_id: str
    summary_or_extract: str
    citations: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class GradeVerdict:
    """Выход EvidenceGrader → Supervisor (accept | refine)."""

    status: GradeStatus
    missing_anchors: List[str] = field(default_factory=list)
    note: str = ""
