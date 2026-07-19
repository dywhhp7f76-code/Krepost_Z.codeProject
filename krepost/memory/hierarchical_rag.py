"""
HierarchicalDomainRAG — каркас Phase 4.

Supervisor→SearchBrief→DomainScout[]→ContextReader[]→EvidenceGrader→loop

Один голос наружу = Supervisor (main LLM в Orchestrator после retrieve).
SearchBrief: пока heuristic (DomainRouter + tokens); LLM-brief — следующий шаг.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from krepost.memory.context_reader import read_pool, read_pool_async
from krepost.memory.domain_router import DomainRouter
from krepost.memory.domain_scout import run_domain_scouts
from krepost.memory.domains import FALLBACK_DOMAIN
from krepost.memory.evidence_grader import EvidenceGrader
from krepost.memory.search_brief import (
    GradeVerdict,
    ReaderDossier,
    ScoutHit,
    SearchBrief,
)
from krepost.memory.store import MemoryStore, RetrievalResult, RetrievedChunk
from krepost.security.tool_guard import ToolOutputGuard

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")

_TOKEN = re.compile(r"[\wа-яА-ЯёЁ]+", re.UNICODE)
_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are",
    "что", "как", "это", "для", "при", "или", "и", "в", "на", "с", "по", "не",
}


class _Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        *,
        where: Optional[dict] = None,
    ) -> RetrievalResult: ...


@dataclass
class HierarchicalRound:
    brief: SearchBrief
    hits: List[ScoutHit] = field(default_factory=list)
    dossiers: List[ReaderDossier] = field(default_factory=list)
    verdict: Optional[GradeVerdict] = None


@dataclass
class HierarchicalResult:
    rounds: List[HierarchicalRound] = field(default_factory=list)
    accepted: bool = False
    final_dossiers: List[ReaderDossier] = field(default_factory=list)
    final_verdict: Optional[GradeVerdict] = None

    @property
    def evidence_text(self) -> str:
        """Контекст для Supervisor — не ответ юзеру."""
        parts = []
        for d in self.final_dossiers:
            cite = ", ".join(d.citations[:5])
            parts.append(
                f"[domain={d.domain_id} conf={d.confidence:.2f} src={cite}]\n"
                f"{d.summary_or_extract}"
            )
        return "\n\n---\n\n".join(parts)


@dataclass
class HierarchicalTrace:
    brief: Optional[SearchBrief] = None
    grade: Optional[str] = None
    rounds: int = 0
    accepted: bool = False
    domains: List[str] = field(default_factory=list)
    brief_source: str = ""


def draft_search_brief(
    query: str,
    domain_ids: List[str],
    *,
    max_anchors: int = 8,
) -> SearchBrief:
    """Heuristic SearchBrief (пока без Supervisor-LLM)."""
    tokens = [
        t for t in _TOKEN.findall((query or "").lower())
        if len(t) > 2 and t not in _STOP
    ]
    # уникальные, порядок сохранения
    seen = set()
    anchors: List[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            anchors.append(t)
        if len(anchors) >= max_anchors:
            break
    if not anchors and query.strip():
        anchors = [query.strip()[:80]]
    domains = [d for d in domain_ids if d] or [FALLBACK_DOMAIN]
    return SearchBrief(
        query_anchors=anchors,
        domains=domains,
        round=0,
        user_query=query or "",
    )


class HierarchicalDomainRAG:
    """
    Loop max_rounds. При partial/irrelevant — refine SearchBrief
    (SupervisorBriefDrafter или heuristic). Не отвечает пользователю.
    """

    def __init__(
        self,
        retriever: _Retriever,
        *,
        max_rounds: int = 2,
        scout_k: int = 5,
        max_readers: int = 2,
        grader: Optional[EvidenceGrader] = None,
        brief_drafter: Any = None,
        occ_reader: Any = None,
    ):
        self.retriever = retriever
        self.max_rounds = max(1, max_rounds)
        self.scout_k = scout_k
        self.max_readers = max_readers
        self.grader = grader or EvidenceGrader()
        self.brief_drafter = brief_drafter
        self.occ_reader = occ_reader

    async def run(self, brief: SearchBrief, *, ctx: Any = None) -> HierarchicalResult:
        current = SearchBrief(
            query_anchors=list(brief.query_anchors),
            domains=list(brief.domains),
            round=brief.round,
            user_query=brief.user_query,
        )
        out = HierarchicalResult()

        for r in range(self.max_rounds):
            current.round = r
            hits = await run_domain_scouts(
                current, self.retriever, k=self.scout_k
            )
            if self.occ_reader is not None:
                dossiers = await read_pool_async(
                    current,
                    hits,
                    max_readers=self.max_readers,
                    occ_reader=self.occ_reader,
                    ctx=ctx,
                )
            else:
                dossiers = read_pool(
                    current, hits, max_readers=self.max_readers
                )
            verdict = self.grader.grade(current, dossiers)
            round_rec = HierarchicalRound(
                brief=SearchBrief(
                    query_anchors=list(current.query_anchors),
                    domains=list(current.domains),
                    round=r,
                    user_query=current.user_query,
                ),
                hits=hits,
                dossiers=dossiers,
                verdict=verdict,
            )
            out.rounds.append(round_rec)
            out.final_dossiers = dossiers
            out.final_verdict = verdict

            if verdict.status == "relevant":
                out.accepted = True
                break
            if r + 1 >= self.max_rounds:
                break
            if self.brief_drafter is not None:
                current = await self.brief_drafter.draft(
                    current.user_query,
                    list(current.domains),
                    round=r + 1,
                    previous=current,
                    grade_note=verdict.note or verdict.status,
                    missing_anchors=verdict.missing_anchors,
                )
            else:
                for m in verdict.missing_anchors:
                    if m not in current.query_anchors:
                        current.query_anchors.append(m)
                if not verdict.missing_anchors and current.user_query:
                    uq = current.user_query.strip()
                    if uq and uq not in current.query_anchors:
                        current.query_anchors.append(uq)

        return out


class HierarchicalMemoryFacade:
    """
    Duck-compatible с MemoryStore для Orchestrator/harness.

    retrieve() = DomainRouter → Supervisor(SearchBrief) → HierarchicalDomainRAG
    → chunks. Ответ юзеру пишет только Supervisor (main LLM) после этого.
    """

    def __init__(
        self,
        store: MemoryStore,
        domain_router: DomainRouter,
        pipeline: HierarchicalDomainRAG,
        *,
        fallback_flat: bool = True,
        brief_drafter: Any = None,
    ):
        self.store = store
        self.domain_router = domain_router
        self.pipeline = pipeline
        self.fallback_flat = fallback_flat
        self.brief_drafter = brief_drafter
        self.last_trace: Optional[HierarchicalTrace] = None
        self.last_result: Optional[HierarchicalResult] = None

    def set_supervisor_backend(self, backend: Any) -> None:
        """Подключить main LLM как Supervisor для SearchBrief (+ refine)."""
        from krepost.memory.supervisor_brief import SupervisorBriefDrafter

        drafter = SupervisorBriefDrafter(backend)
        self.brief_drafter = drafter
        self.pipeline.brief_drafter = drafter

    def set_occ_reader(self, occ_reader: Any) -> None:
        """ContextReader pool ← OccReader (опционально)."""
        self.pipeline.occ_reader = occ_reader

    @property
    def embedder(self) -> Any:
        return self.store.embedder

    @property
    def collection(self) -> Any:
        return self.store.collection

    @property
    def confidence_threshold(self) -> float:
        return self.store.confidence_threshold

    def _dossiers_to_chunks(
        self, query: str, result: HierarchicalResult
    ) -> List[RetrievedChunk]:
        chunks: List[RetrievedChunk] = []
        grade = result.final_verdict.status if result.final_verdict else ""
        for d in result.final_dossiers:
            if not (d.summary_or_extract or "").strip():
                continue
            src = d.citations[0] if d.citations else d.domain_id
            meta: Dict[str, Any] = {
                "domain": d.domain_id,
                "src": src,
                "hierarchical": True,
                "grade": grade,
                "citations": list(d.citations[:8]),
            }
            chunks.append(
                RetrievedChunk(
                    text=d.summary_or_extract,
                    score=float(d.confidence),
                    doc_id=str(src),
                    metadata=meta,
                )
            )
        return chunks

    async def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        hits = await self.domain_router.route(query)
        domain_ids = [h.domain_id for h in hits]
        brief_source = "heuristic"
        if self.brief_drafter is not None:
            brief = await self.brief_drafter.draft(query, domain_ids, round=0)
            brief_source = getattr(self.brief_drafter, "last_source", "llm")
        else:
            brief = draft_search_brief(query, domain_ids)
        result = await self.pipeline.run(brief)
        self.last_result = result
        self.last_trace = HierarchicalTrace(
            brief=brief,
            grade=result.final_verdict.status if result.final_verdict else None,
            rounds=len(result.rounds),
            accepted=result.accepted,
            domains=list(brief.domains),
            brief_source=brief_source,
        )
        chunks = self._dossiers_to_chunks(query, result)
        if not chunks and self.fallback_flat:
            logger.info(
                "HierarchicalDomainRAG: empty dossiers — flat fallback "
                f"(domains={domain_ids})"
            )
            return await self.store.retrieve(query, k=k or 5)

        if k is not None:
            chunks = chunks[:k]
        top = chunks[0].score if chunks else 0.0
        return RetrievalResult(
            query,
            chunks,
            top,
            confident=bool(result.accepted) or top >= self.store.confidence_threshold,
        )

    def retrieve_sync(self, query: str, k: int | None = None) -> RetrievalResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.retrieve(query, k=k))
        raise RuntimeError(
            "retrieve_sync called from running event loop — use await retrieve()"
        )

    def build_context(
        self, result: RetrievalResult, *, guard: Optional[ToolOutputGuard] = None
    ) -> str:
        return self.store.build_context(result, guard=guard)

    def _source_label(self, meta: Dict[str, Any], doc_id: str) -> str:
        return self.store._source_label(meta, doc_id)


def trace_to_meta(trace: Optional[HierarchicalTrace]) -> Dict[str, Any]:
    """Сжатый HierarchicalTrace → metadata ответа /v1/query."""
    if trace is None:
        return {}
    brief = trace.brief
    return {
        "hierarchical": True,
        "SearchBrief": {
            "query_anchors": list(brief.query_anchors) if brief else [],
            "domains": list(brief.domains) if brief else list(trace.domains),
            "round": brief.round if brief else 0,
        },
        "EvidenceGrader": trace.grade,
        "hierarchical_rounds": trace.rounds,
        "hierarchical_accepted": trace.accepted,
        "brief_source": trace.brief_source,
    }


def wrap_hierarchical_memory(
    store: MemoryStore,
    *,
    use_hybrid: bool = True,
    max_domains: int = 3,
    max_rounds: int = 2,
    scout_k: int = 5,
    max_readers: int = 2,
    top_n: int = 5,
    per_domain_k: int = 5,
) -> HierarchicalMemoryFacade:
    """Factory для serve_lmstudio / factory.py."""
    retriever: Any = store
    if use_hybrid:
        from krepost.memory.hybrid import HybridRetriever

        retriever = HybridRetriever(
            store,
            top_n=top_n,
            vector_k=per_domain_k,
            bm25_k=per_domain_k,
        )
    pipeline = HierarchicalDomainRAG(
        retriever,
        max_rounds=max_rounds,
        scout_k=scout_k,
        max_readers=max_readers,
    )
    return HierarchicalMemoryFacade(
        store,
        DomainRouter(store.embedder, max_domains=max_domains),
        pipeline,
    )
