"""
HybridRetriever — vector + BM25 + RRF (кирпич HierarchicalDomainRAG / Phase 3+).

Без новых зависимостей: лёгкий BM25Okapi + reciprocal rank fusion.
Работает поверх MemoryStore / Chroma; фильтр where=domain сохраняется.
"""
from __future__ import annotations

import asyncio
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from krepost.memory.store import MemoryStore, RetrievalResult, RetrievedChunk

_TOKEN = re.compile(r"[\wа-яА-ЯёЁ]+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


class BM25Okapi:
    """Минимальный BM25 без rank_bm25."""

    def __init__(self, corpus_tokens: Sequence[Sequence[str]], *, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = [list(doc) for doc in corpus_tokens]
        self.n = len(self.corpus)
        self.doc_len = [len(d) for d in self.corpus]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        df: Dict[str, int] = defaultdict(int)
        for doc in self.corpus:
            for t in set(doc):
                df[t] += 1
        self.idf = {
            t: math.log(1 + (self.n - freq + 0.5) / (freq + 0.5))
            for t, freq in df.items()
        }

    def scores(self, query_tokens: Sequence[str]) -> List[float]:
        out = [0.0] * self.n
        if not self.n or not query_tokens:
            return out
        for i, doc in enumerate(self.corpus):
            tf: Dict[str, int] = defaultdict(int)
            for t in doc:
                tf[t] += 1
            score = 0.0
            dl = self.doc_len[i] or 1
            for t in query_tokens:
                if t not in tf:
                    continue
                idf = self.idf.get(t, 0.0)
                freq = tf[t]
                denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
                score += idf * (freq * (self.k1 + 1)) / (denom or 1.0)
            out[i] = score
        return out


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]],
    *,
    k: int = 60,
) -> List[Tuple[str, float]]:
    """ids в порядке убывания ранга → fused (id, score)."""
    scores: Dict[str, float] = defaultdict(float)
    for lst in ranked_lists:
        for rank, doc_id in enumerate(lst):
            scores[doc_id] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


@dataclass
class _Bm25Index:
    ids: List[str] = field(default_factory=list)
    texts: List[str] = field(default_factory=list)
    metas: List[Dict[str, Any]] = field(default_factory=list)
    bm25: Optional[BM25Okapi] = None
    domain_key: str = ""


class HybridRetriever:
    """
    vector (MemoryStore) + BM25 по корпусу domain → RRF → top_n.
    BM25-корпус кэшируется per domain_key.
    """

    def __init__(
        self,
        store: MemoryStore,
        *,
        vector_k: int = 10,
        bm25_k: int = 10,
        top_n: int = 5,
        rrf_k: int = 60,
    ):
        self.store = store
        self.vector_k = vector_k
        self.bm25_k = bm25_k
        self.top_n = top_n
        self.rrf_k = rrf_k
        self._indexes: Dict[str, _Bm25Index] = {}

    def _domain_key(self, where: Optional[Dict[str, Any]]) -> str:
        if not where:
            return "__all__"
        return str(where.get("domain") or sorted(where.items()))

    def _build_bm25(self, where: Optional[Dict[str, Any]]) -> _Bm25Index:
        key = self._domain_key(where)
        if key in self._indexes and self._indexes[key].bm25 is not None:
            return self._indexes[key]

        col = self.store.collection
        kwargs: Dict[str, Any] = {"include": ["documents", "metadatas"]}
        if where is not None:
            kwargs["where"] = where
        # Chroma get без ids — все подходящие (для большого vault позже — лимит)
        data = col.get(**kwargs)
        ids = list(data.get("ids") or [])
        docs = list(data.get("documents") or [])
        metas = list(data.get("metadatas") or [])
        tokens = [tokenize(d or "") for d in docs]
        idx = _Bm25Index(
            ids=ids,
            texts=docs,
            metas=[m or {} for m in metas],
            bm25=BM25Okapi(tokens) if tokens else None,
            domain_key=key,
        )
        self._indexes[key] = idx
        return idx

    def invalidate_bm25(self, domain: Optional[str] = None) -> None:
        if domain is None:
            self._indexes.clear()
        else:
            self._indexes.pop(domain, None)
            self._indexes.pop("__all__", None)

    def _bm25_rank(
        self, query: str, where: Optional[Dict[str, Any]]
    ) -> List[RetrievedChunk]:
        idx = self._build_bm25(where)
        if not idx.bm25 or not idx.ids:
            return []
        scores = idx.bm25.scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        out: List[RetrievedChunk] = []
        for i in order[: self.bm25_k]:
            if scores[i] <= 0:
                continue
            meta = dict(idx.metas[i])
            meta["bm25_score"] = float(scores[i])
            out.append(
                RetrievedChunk(
                    text=idx.texts[i] or "",
                    score=float(scores[i]),
                    doc_id=str(meta.get("doc_id") or idx.ids[i]),
                    metadata=meta,
                )
            )
        return out

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        *,
        where: Optional[Dict[str, Any]] = None,
    ) -> RetrievalResult:
        top_n = self.top_n if k is None else k
        if not query or not query.strip():
            return RetrievalResult(query, [], 0.0, False)

        vec_res = await self.store.retrieve(query, k=self.vector_k, where=where)
        bm25_chunks = await asyncio.to_thread(self._bm25_rank, query, where)

        def _key(c: RetrievedChunk) -> str:
            return f"{c.doc_id}:{c.metadata.get('chunk', '')}:{hash(c.text)}"

        vec_ids = [_key(c) for c in vec_res.chunks]
        bm_ids = [_key(c) for c in bm25_chunks]
        by_id = {_key(c): c for c in vec_res.chunks}
        for c in bm25_chunks:
            by_id.setdefault(_key(c), c)

        fused = reciprocal_rank_fusion([vec_ids, bm_ids], k=self.rrf_k)
        chunks: List[RetrievedChunk] = []
        for fid, rrf_score in fused[:top_n]:
            base = by_id.get(fid)
            if base is None:
                continue
            meta = dict(base.metadata)
            meta["rrf_score"] = float(rrf_score)
            chunks.append(
                RetrievedChunk(
                    text=base.text,
                    score=float(rrf_score),
                    doc_id=base.doc_id,
                    metadata=meta,
                )
            )

        # если BM25 пуст (нет корпуса) — чисто vector
        if not chunks and vec_res.chunks:
            chunks = list(vec_res.chunks[:top_n])

        top = chunks[0].score if chunks else 0.0
        # confident по vector top, если есть
        confident = vec_res.confident if vec_res.chunks else top >= self.store.confidence_threshold
        return RetrievalResult(query, chunks, top, confident=confident)
