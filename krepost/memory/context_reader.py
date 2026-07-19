"""
ContextReader — OCC-style extract по ScoutHit (HierarchicalDomainRAG Phase 4).

Пул ≤2. Не отвечает пользователю. Без LLM: детерминированная выжимка;
с OccReader — `read_async` / `read_pool_async` (fail-open → sync extract).
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from krepost.memory.search_brief import ReaderDossier, ScoutHit, SearchBrief
from krepost.memory.store import RetrievalResult, RetrievedChunk


def _group_domains(
    brief: SearchBrief,
    hits: Sequence[ScoutHit],
    max_readers: int,
) -> Tuple[List[str], Dict[str, List[ScoutHit]]]:
    by_domain: Dict[str, List[ScoutHit]] = {}
    for h in hits:
        by_domain.setdefault(h.domain_id, []).append(h)
    order: List[str] = []
    for d in brief.domains:
        if d in by_domain and d not in order:
            order.append(d)
    for d in by_domain:
        if d not in order:
            order.append(d)
    return order[: max(1, max_readers)], by_domain


class ContextReader:
    """Один reader: hits → ReaderDossier (extract + citations)."""

    def __init__(
        self,
        *,
        max_chars: int = 2000,
        max_hits: int = 4,
        occ_reader: Any = None,
    ):
        self.max_chars = max_chars
        self.max_hits = max_hits
        self.occ_reader = occ_reader

    def read(
        self,
        brief: SearchBrief,
        hits: Sequence[ScoutHit],
        *,
        domain_id: str | None = None,
    ) -> ReaderDossier:
        selected = list(hits)
        if domain_id:
            selected = [h for h in selected if h.domain_id == domain_id]
        selected = selected[: self.max_hits]
        if not selected:
            did = domain_id or (brief.domains[0] if brief.domains else "unknown")
            return ReaderDossier(
                domain_id=did,
                summary_or_extract="",
                citations=[],
                confidence=0.0,
            )

        citations: List[str] = []
        parts: List[str] = []
        size = 0
        top_score = 0.0
        did = selected[0].domain_id

        for h in selected:
            did = h.domain_id
            top_score = max(top_score, float(h.scores.get("top", 0.0)))
            for p in h.paths:
                if p not in citations:
                    citations.append(p)
            for text in h.texts:
                block = text.strip()
                if not block:
                    continue
                if size + len(block) > self.max_chars:
                    remain = self.max_chars - size
                    if remain > 40:
                        parts.append(block[:remain] + "…")
                    break
                parts.append(block)
                size += len(block)

        blob = " ".join(parts).lower()
        anchors = [a.lower() for a in brief.query_anchors if a]
        hit_n = sum(1 for a in anchors if a in blob) if anchors else 0
        anchor_ratio = (hit_n / len(anchors)) if anchors else (1.0 if parts else 0.0)
        confidence = min(1.0, 0.5 * top_score + 0.5 * anchor_ratio) if parts else 0.0

        return ReaderDossier(
            domain_id=did,
            summary_or_extract="\n\n".join(parts),
            citations=citations,
            confidence=float(confidence),
        )

    def _hits_to_retrieval(
        self, brief: SearchBrief, hits: Sequence[ScoutHit]
    ) -> RetrievalResult:
        chunks: List[RetrievedChunk] = []
        for h in hits:
            for i, text in enumerate(h.texts):
                src = h.paths[i] if i < len(h.paths) else (
                    h.paths[0] if h.paths else h.doc_id
                )
                chunks.append(
                    RetrievedChunk(
                        text=text,
                        score=float(h.scores.get("top", 0.0)),
                        doc_id=h.doc_id,
                        metadata={"domain": h.domain_id, "src": src},
                    )
                )
        top = chunks[0].score if chunks else 0.0
        q = brief.user_query or " ".join(brief.query_anchors)
        return RetrievalResult(q, chunks, top, True)

    async def read_async(
        self,
        brief: SearchBrief,
        hits: Sequence[ScoutHit],
        *,
        domain_id: str | None = None,
        ctx: Any = None,
    ) -> ReaderDossier:
        """Extract; OccReader сжимает (fail-open → sync read)."""
        base = self.read(brief, hits, domain_id=domain_id)
        if self.occ_reader is None or not base.summary_or_extract.strip():
            return base
        selected = [h for h in hits if domain_id is None or h.domain_id == domain_id]
        selected = selected[: self.max_hits]
        retrieval = self._hits_to_retrieval(brief, selected)
        question = brief.user_query or " ".join(brief.query_anchors)
        try:
            occ = await self.occ_reader.answer(question, retrieval, ctx=ctx)
            if occ.used_reader and occ.text and not occ.no_data:
                return ReaderDossier(
                    domain_id=base.domain_id,
                    summary_or_extract=occ.text.strip(),
                    citations=list(base.citations),
                    confidence=max(base.confidence, 0.55),
                )
        except Exception:
            pass
        return base


def read_pool(
    brief: SearchBrief,
    hits: Sequence[ScoutHit],
    *,
    max_readers: int = 2,
    max_chars: int = 2000,
    occ_reader: Any = None,
) -> List[ReaderDossier]:
    """ContextReader pool ≈ 2 — sync extract."""
    order, by_domain = _group_domains(brief, hits, max_readers)
    reader = ContextReader(max_chars=max_chars, occ_reader=occ_reader)
    return [reader.read(brief, by_domain[d], domain_id=d) for d in order]


async def read_pool_async(
    brief: SearchBrief,
    hits: Sequence[ScoutHit],
    *,
    max_readers: int = 2,
    max_chars: int = 2000,
    occ_reader: Any = None,
    ctx: Any = None,
) -> List[ReaderDossier]:
    """Пул ContextReader с опциональным OccReader (≤2)."""
    order, by_domain = _group_domains(brief, hits, max_readers)
    reader = ContextReader(max_chars=max_chars, occ_reader=occ_reader)
    out: List[ReaderDossier] = []
    for d in order:
        out.append(
            await reader.read_async(brief, by_domain[d], domain_id=d, ctx=ctx)
        )
    return out
