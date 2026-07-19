"""
DomainScout — лёгкий агент одного domain_id (HierarchicalDomainRAG Phase 4).

Hybrid retrieve ТОЛЬКО в своём domain. Наружу не отвечает.
"""
from __future__ import annotations

from typing import Any, List, Optional, Protocol, Sequence

from krepost.memory.search_brief import ScoutHit, SearchBrief
from krepost.memory.store import RetrievalResult, RetrievedChunk


class _Retriever(Protocol):
    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        *,
        where: Optional[dict] = None,
    ) -> RetrievalResult: ...


class DomainScout:
    """Один domain_id → ScoutHit[]. Запрещено: чужие domains, ответ юзеру."""

    def __init__(
        self,
        domain_id: str,
        retriever: _Retriever,
        *,
        k: int = 5,
    ):
        if not domain_id or not str(domain_id).strip():
            raise ValueError("DomainScout requires non-empty domain_id")
        self.domain_id = str(domain_id).strip()
        self.retriever = retriever
        self.k = k

    def _query_from_brief(self, brief: SearchBrief) -> str:
        parts = [brief.user_query.strip()] if brief.user_query.strip() else []
        parts.extend(brief.query_anchors)
        return " ".join(p for p in parts if p).strip() or " ".join(brief.query_anchors)

    @staticmethod
    def _path_of(chunk: RetrievedChunk) -> str:
        meta = chunk.metadata or {}
        return str(
            meta.get("src")
            or meta.get("source")
            or meta.get("path")
            or chunk.doc_id
            or "?"
        )

    @staticmethod
    def _chunk_id(chunk: RetrievedChunk) -> str:
        meta = chunk.metadata or {}
        c = meta.get("chunk", "")
        return f"{chunk.doc_id}:{c}" if c != "" else str(chunk.doc_id)

    def _to_hits(self, result: RetrievalResult) -> List[ScoutHit]:
        by_doc: dict[str, ScoutHit] = {}
        for ch in result.chunks:
            # защита: чужой domain не протаскиваем
            did = str((ch.metadata or {}).get("domain") or self.domain_id)
            if did != self.domain_id:
                continue
            hit = by_doc.get(ch.doc_id)
            path = self._path_of(ch)
            cid = self._chunk_id(ch)
            if hit is None:
                by_doc[ch.doc_id] = ScoutHit(
                    domain_id=self.domain_id,
                    doc_id=ch.doc_id,
                    paths=[path],
                    scores={"top": float(ch.score)},
                    chunk_ids=[cid],
                    texts=[ch.text],
                    metadata=dict(ch.metadata or {}),
                )
            else:
                if path not in hit.paths:
                    hit.paths.append(path)
                if cid not in hit.chunk_ids:
                    hit.chunk_ids.append(cid)
                    hit.texts.append(ch.text)
                hit.scores["top"] = max(hit.scores.get("top", 0.0), float(ch.score))
        return list(by_doc.values())

    async def scout(self, brief: SearchBrief) -> List[ScoutHit]:
        if self.domain_id not in brief.domains:
            return []
        query = self._query_from_brief(brief)
        if not query:
            return []
        result = await self.retriever.retrieve(
            query,
            k=self.k,
            where={"domain": self.domain_id},
        )
        return self._to_hits(result)


async def run_domain_scouts(
    brief: SearchBrief,
    retriever: _Retriever,
    *,
    k: int = 5,
) -> List[ScoutHit]:
    """DomainScout × N по brief.domains (параллельно на уровне gather — снаружи)."""
    import asyncio

    scouts = [DomainScout(d, retriever, k=k) for d in brief.domains]
    batches = await asyncio.gather(*[s.scout(brief) for s in scouts])
    out: List[ScoutHit] = []
    for batch in batches:
        out.extend(batch)
    return out
