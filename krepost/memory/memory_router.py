"""
MemoryRouter — Phase 3: роутер → retrieval → reranker → контекст для LLM.

Хранители остаются тупыми (индекс + адреса). Один голос — основной LLM
после просева. См. _handoff/MEMORY_ROUTER_SPEC.md.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from krepost.memory.domain_router import DomainHit, DomainRouter
from krepost.memory.reranker import Reranker, ScoreReranker
from krepost.memory.store import MemoryStore, RetrievalResult, RetrievedChunk
from krepost.security.tool_guard import ToolOutputGuard

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


@dataclass
class RouteTrace:
    domains: List[DomainHit] = field(default_factory=list)
    retrieved_before_rerank: int = 0
    after_rerank: int = 0


class MemoryRouter:
    """
    Duck-compatible с MemoryStore для Orchestrator/harness:
    retrieve() / build_context() / _source_label.
    """

    def __init__(
        self,
        store: MemoryStore,
        domain_router: DomainRouter,
        reranker: Optional[Reranker] = None,
        *,
        per_domain_k: int = 5,
        top_n: int = 5,
        fallback_flat: bool = True,
        hybrid: Optional[Any] = None,
    ):
        self.store = store
        self.domain_router = domain_router
        self.reranker: Reranker = reranker or ScoreReranker()
        self.per_domain_k = per_domain_k
        self.top_n = top_n
        self.fallback_flat = fallback_flat
        self.hybrid = hybrid  # HybridRetriever | None — vector+BM25+RRF
        self.last_trace: Optional[RouteTrace] = None

    @property
    def embedder(self) -> Any:
        return self.store.embedder

    @property
    def collection(self) -> Any:
        return self.store.collection

    async def retrieve(self, query: str, k: int | None = None) -> RetrievalResult:
        top_n = self.top_n if k is None else k
        hits = await self.domain_router.route(query)
        domain_ids = [h.domain_id for h in hits]

        merged: List[RetrievedChunk] = []
        seen: set[str] = set()

        async def _one(did: str) -> RetrievalResult:
            try:
                retriever = self.hybrid if self.hybrid is not None else self.store
                return await retriever.retrieve(
                    query,
                    k=self.per_domain_k,
                    where={"domain": did},
                )
            except Exception as e:
                logger.warning(
                    f"MemoryRouter domain retrieve {did!r} failed: "
                    f"{type(e).__name__}: {e}"
                )
                return RetrievalResult(query, [], 0.0, False)

        results = await asyncio.gather(*[_one(d) for d in domain_ids])
        for res in results:
            for c in res.chunks:
                key = f"{c.doc_id}:{c.metadata.get('chunk', '')}:{hash(c.text)}"
                if key in seen:
                    continue
                seen.add(key)
                meta = dict(c.metadata)
                meta.setdefault("routed_domain", meta.get("domain"))
                merged.append(
                    RetrievedChunk(
                        text=c.text,
                        score=c.score,
                        doc_id=c.doc_id,
                        metadata=meta,
                    )
                )

        # Старый индекс без metadata.domain → плоский fallback
        if not merged and self.fallback_flat:
            logger.info(
                "MemoryRouter: empty domain hits — flat fallback "
                f"(domains={domain_ids})"
            )
            flat = await self.store.retrieve(query, k=max(top_n, self.per_domain_k))
            merged = list(flat.chunks)

        before = len(merged)
        if hasattr(self.reranker, "rerank_async"):
            ranked = await self.reranker.rerank_async(  # type: ignore[attr-defined]
                query, merged, top_n=top_n
            )
        else:
            ranked = await asyncio.to_thread(
                self.reranker.rerank, query, merged, top_n=top_n
            )

        self.last_trace = RouteTrace(
            domains=hits,
            retrieved_before_rerank=before,
            after_rerank=len(ranked),
        )
        top = ranked[0].score if ranked else 0.0
        return RetrievalResult(
            query,
            ranked,
            top,
            confident=top >= self.store.confidence_threshold,
        )

    def retrieve_sync(self, query: str, k: int | None = None) -> RetrievalResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.retrieve(query, k=k))
        raise RuntimeError("retrieve_sync called from running event loop — use await retrieve()")

    def build_context(
        self, result: RetrievalResult, *, guard: Optional[ToolOutputGuard] = None
    ) -> str:
        return self.store.build_context(result, guard=guard)

    def _source_label(self, meta: Dict[str, Any], doc_id: str) -> str:
        return self.store._source_label(meta, doc_id)


def wrap_memory_store(
    store: MemoryStore,
    *,
    use_cross_encoder: bool = False,
    max_domains: int = 3,
    top_n: int = 5,
    per_domain_k: int = 5,
    use_hybrid: bool = False,
) -> MemoryRouter:
    from krepost.memory.reranker import make_default_reranker

    hybrid = None
    if use_hybrid:
        from krepost.memory.hybrid import HybridRetriever

        hybrid = HybridRetriever(store, top_n=top_n, vector_k=per_domain_k, bm25_k=per_domain_k)

    return MemoryRouter(
        store,
        DomainRouter(store.embedder, max_domains=max_domains),
        make_default_reranker(use_cross_encoder=use_cross_encoder),
        per_domain_k=per_domain_k,
        top_n=top_n,
        hybrid=hybrid,
    )
