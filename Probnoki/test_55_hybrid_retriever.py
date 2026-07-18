"""Пробник #55: HybridRetriever — BM25 + vector RRF."""
from __future__ import annotations

import math

import pytest

from krepost.memory.hybrid import BM25Okapi, HybridRetriever, reciprocal_rank_fusion, tokenize
from krepost.memory.store import MemoryStore


VOCAB = ["solar", "battery", "energy", "hack", "exploit", "python"]


def bow(text: str):
    t = text.lower()
    v = [float(t.count(w)) for w in VOCAB]
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class BowEmbedder:
    def encode(self, text):
        return bow(text)


class FakeCollection:
    def __init__(self):
        self.docs = []  # id, emb, doc, meta

    def add(self, ids, embeddings, documents, metadatas):
        for i in range(len(ids)):
            self.docs.append((ids[i], embeddings[i], documents[i], metadatas[i]))

    def get(self, include=None, where=None, limit=None, offset=None):
        rows = self.docs
        if where and "domain" in where:
            rows = [r for r in rows if (r[3] or {}).get("domain") == where["domain"]]
        ids = [r[0] for r in rows]
        docs = [r[2] for r in rows]
        metas = [r[3] for r in rows]
        return {"ids": ids, "documents": docs, "metadatas": metas}

    def query(self, query_embeddings, n_results, where=None):
        q = query_embeddings[0]
        scored = []
        for _id, emb, doc, meta in self.docs:
            if where and meta.get("domain") != where.get("domain"):
                continue
            scored.append((1.0 - sum(a * b for a, b in zip(q, emb)), doc, meta))
        scored.sort(key=lambda x: x[0])
        top = scored[:n_results]
        return {
            "distances": [[d for d, _, _ in top]],
            "documents": [[doc for _, doc, _ in top]],
            "metadatas": [[m for _, _, m in top]],
        }


def test_tokenize_and_bm25():
    assert "battery" in tokenize("Solar BATTERY energy")
    bm = BM25Okapi([tokenize("solar battery pack"), tokenize("hack exploit tool")])
    scores = bm.scores(tokenize("battery solar"))
    assert scores[0] > scores[1]


def test_rrf_merges_lists():
    fused = reciprocal_rank_fusion([["a", "b"], ["b", "c"]], k=60)
    ids = [x[0] for x in fused]
    assert ids[0] == "b"


@pytest.mark.asyncio
async def test_hybrid_retrieves_exact_term():
    store = MemoryStore(BowEmbedder(), FakeCollection(), min_relevance=0.01)
    store.add_sync(
        "e.md",
        "unique_token_xyz solar battery energy storage",
        metadata={"domain": "01-Energy", "src": "01-Energy/e.md"},
    )
    store.add_sync(
        "h.md",
        "hack exploit security notes",
        metadata={"domain": "03-Programming_Hacking", "src": "03-Programming_Hacking/h.md"},
    )
    hy = HybridRetriever(store, vector_k=5, bm25_k=5, top_n=3)
    # точный редкий термин — BM25 должен подтянуть energy-чанк
    res = await hy.retrieve("unique_token_xyz", where={"domain": "01-Energy"})
    assert not res.empty
    assert "unique_token_xyz" in res.chunks[0].text
