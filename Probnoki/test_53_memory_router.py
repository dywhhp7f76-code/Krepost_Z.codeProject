"""
Пробник #53: MemoryRouter Phase 3 (route → retrieve → rerank).

Детерминированный BOW-эмбеддер + FakeCollection с where=domain.
"""
from __future__ import annotations

import math

import pytest

from krepost.memory.domain_router import DomainRouter
from krepost.memory.domains import DomainSpec
from krepost.memory.memory_router import MemoryRouter
from krepost.memory.reranker import ScoreReranker
from krepost.memory.store import MemoryStore


VOCAB = [
    "energy", "solar", "battery",
    "hack", "exploit", "security",
    "philosophy", "ethics", "mind",
    "other", "misc",
]


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
        self.docs = []

    def add(self, ids, embeddings, documents, metadatas):
        for i in range(len(ids)):
            self.docs.append((embeddings[i], documents[i], metadatas[i]))

    def query(self, query_embeddings, n_results, where=None):
        q = query_embeddings[0]
        scored = []
        for emb, doc, meta in self.docs:
            if where is not None:
                if not _match_where(meta or {}, where):
                    continue
            dot = sum(a * b for a, b in zip(q, emb))
            scored.append((1.0 - dot, doc, meta))
        scored.sort(key=lambda x: x[0])
        top = scored[:n_results]
        return {
            "distances": [[d for d, _, _ in top]],
            "documents": [[doc for _, doc, _ in top]],
            "metadatas": [[m for _, _, m in top]],
        }


def _match_where(meta: dict, where: dict) -> bool:
    for key, expected in where.items():
        if isinstance(expected, dict) and "$in" in expected:
            if meta.get(key) not in expected["$in"]:
                return False
        elif meta.get(key) != expected:
            return False
    return True


DOMAINS = (
    DomainSpec("01-Energy", ("energy solar battery power",), "01-Energy"),
    DomainSpec("03-Programming_Hacking", ("hack exploit security",), "03-Programming_Hacking"),
    DomainSpec("04-Philosophy_AI", ("philosophy ethics mind",), "04-Philosophy_AI"),
    DomainSpec("13-other", ("other misc",), "13-other"),
)


@pytest.fixture
def store():
    s = MemoryStore(BowEmbedder(), FakeCollection(), min_relevance=0.1, confidence_threshold=0.5)
    s.add_sync(
        "01-Energy/solar.md",
        "solar battery energy storage for offgrid",
        metadata={"domain": "01-Energy", "src": "01-Energy/solar.md"},
    )
    s.add_sync(
        "03-Programming_Hacking/notes.md",
        "hack exploit security tools and payloads",
        metadata={"domain": "03-Programming_Hacking", "src": "03-Programming_Hacking/notes.md"},
    )
    s.add_sync(
        "04-Philosophy_AI/ethics.md",
        "philosophy ethics mind and consciousness",
        metadata={"domain": "04-Philosophy_AI", "src": "04-Philosophy_AI/ethics.md"},
    )
    return s


def test_domain_router_picks_energy():
    r = DomainRouter(BowEmbedder(), DOMAINS, min_score=0.1, max_domains=2)
    hits = r.route_sync("solar battery energy")
    ids = [h.domain_id for h in hits]
    assert "01-Energy" in ids
    assert ids[0] == "01-Energy"


def test_domain_from_relpath():
    from krepost.memory.domains import domain_from_relpath

    assert domain_from_relpath("01-Energy/a.md") == "01-Energy"
    assert domain_from_relpath("unknown/x.md") == "13-other"


@pytest.mark.asyncio
async def test_memory_router_routes_and_reranks(store):
    router = MemoryRouter(
        store,
        DomainRouter(BowEmbedder(), DOMAINS, min_score=0.1, max_domains=2),
        ScoreReranker(),
        per_domain_k=3,
        top_n=2,
        fallback_flat=False,
    )
    result = await router.retrieve("solar battery energy")
    assert not result.empty
    assert router.last_trace is not None
    assert any(h.domain_id == "01-Energy" for h in router.last_trace.domains)
    assert len(result.chunks) <= 2
    # в топе должен быть energy-чанк, не philosophy
    joined = " ".join(c.text for c in result.chunks)
    assert "solar" in joined or "battery" in joined
    assert "consciousness" not in joined


@pytest.mark.asyncio
async def test_memory_router_flat_fallback_without_domain_meta():
    s = MemoryStore(BowEmbedder(), FakeCollection(), min_relevance=0.1)
    s.add_sync("legacy.md", "solar battery energy legacy note", metadata={"src": "legacy.md"})
    router = MemoryRouter(
        s,
        DomainRouter(BowEmbedder(), DOMAINS, min_score=0.1, max_domains=1),
        ScoreReranker(),
        fallback_flat=True,
    )
    result = await router.retrieve("solar battery energy")
    assert not result.empty


def test_score_reranker_top_n():
    from krepost.memory.store import RetrievedChunk

    chunks = [
        RetrievedChunk("a", 0.2, "1"),
        RetrievedChunk("b", 0.9, "2"),
        RetrievedChunk("c", 0.5, "3"),
    ]
    out = ScoreReranker().rerank("q", chunks, top_n=2)
    assert [c.doc_id for c in out] == ["2", "3"]


def test_relai_blocks_auto_rsi_without_suite():
    from krepost.governance.relai import allows_auto_rsi

    bad = allows_auto_rsi(regression_suite_passed=False)
    assert bad.allowed is False
    good = allows_auto_rsi(regression_suite_passed=True, suite_name="ataker")
    assert good.allowed is True
    ov = allows_auto_rsi(regression_suite_passed=False, operator_override=True)
    assert ov.allowed is True
