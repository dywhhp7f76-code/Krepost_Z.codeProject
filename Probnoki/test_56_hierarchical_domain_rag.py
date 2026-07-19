"""Пробник #56: HierarchicalDomainRAG scaffold — DomainScout/ContextReader/EvidenceGrader."""
from __future__ import annotations

import math

import pytest

from krepost.memory.context_reader import ContextReader, read_pool
from krepost.memory.domain_scout import DomainScout, run_domain_scouts
from krepost.memory.evidence_grader import EvidenceGrader
from krepost.memory.hierarchical_rag import (
    HierarchicalDomainRAG,
    draft_search_brief,
    wrap_hierarchical_memory,
)
from krepost.memory.search_brief import SearchBrief
from krepost.memory.store import MemoryStore


VOCAB = ["solar", "battery", "energy", "hack", "exploit", "python", "vault"]


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
            self.docs.append((ids[i], embeddings[i], documents[i], metadatas[i]))

    def get(self, include=None, where=None, limit=None, offset=None):
        rows = self.docs
        if where and "domain" in where:
            rows = [r for r in rows if (r[3] or {}).get("domain") == where["domain"]]
        return {
            "ids": [r[0] for r in rows],
            "documents": [r[2] for r in rows],
            "metadatas": [r[3] for r in rows],
        }

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


def _store_with_docs():
    store = MemoryStore(BowEmbedder(), FakeCollection(), min_relevance=0.01)
    store.add_sync(
        "e.md",
        "solar battery energy storage vault note",
        metadata={"domain": "01-Energy", "src": "01-Energy/e.md", "chunk": 0},
    )
    store.add_sync(
        "h.md",
        "hack exploit python tool",
        metadata={"domain": "02-Security", "src": "02-Security/h.md", "chunk": 0},
    )
    return store


def test_search_brief_requires_domains():
    with pytest.raises(ValueError):
        SearchBrief(query_anchors=["a"], domains=[])


@pytest.mark.asyncio
async def test_domain_scout_stays_in_domain():
    store = _store_with_docs()
    brief = SearchBrief(
        query_anchors=["solar", "battery"],
        domains=["01-Energy"],
        user_query="energy storage",
    )
    scout = DomainScout("01-Energy", store, k=3)
    hits = await scout.scout(brief)
    assert hits
    assert all(h.domain_id == "01-Energy" for h in hits)
    assert any("solar" in t.lower() for h in hits for t in h.texts)


@pytest.mark.asyncio
async def test_domain_scout_ignores_foreign_domain_in_brief():
    store = _store_with_docs()
    brief = SearchBrief(
        query_anchors=["hack"],
        domains=["01-Energy"],  # не Security
        user_query="hack",
    )
    hits = await run_domain_scouts(brief, store, k=3)
    # retrieve только Energy — hack-док не должен попасть
    assert all(h.domain_id == "01-Energy" for h in hits)
    blob = " ".join(t for h in hits for t in h.texts).lower()
    assert "exploit" not in blob


def test_context_reader_and_grader_relevant():
    from krepost.memory.search_brief import ScoutHit

    brief = SearchBrief(
        query_anchors=["solar", "battery"],
        domains=["01-Energy"],
        user_query="q",
    )
    hits = [
        ScoutHit(
            domain_id="01-Energy",
            doc_id="e.md",
            paths=["01-Energy/e.md"],
            scores={"top": 0.9},
            chunk_ids=["e.md:0"],
            texts=["solar battery energy storage"],
        )
    ]
    dossiers = read_pool(brief, hits, max_readers=2)
    assert len(dossiers) == 1
    assert "solar" in dossiers[0].summary_or_extract.lower()
    v = EvidenceGrader().grade(brief, dossiers)
    assert v.status == "relevant"
    assert v.missing_anchors == []


def test_evidence_grader_irrelevant_empty():
    brief = SearchBrief(query_anchors=["zzz"], domains=["01-Energy"])
    v = EvidenceGrader().grade(brief, [])
    assert v.status == "irrelevant"


@pytest.mark.asyncio
async def test_hierarchical_loop_accepts():
    store = _store_with_docs()
    h = HierarchicalDomainRAG(store, max_rounds=2, scout_k=3)
    brief = SearchBrief(
        query_anchors=["solar", "battery"],
        domains=["01-Energy"],
        user_query="solar battery",
    )
    result = await h.run(brief)
    assert result.rounds
    assert result.final_verdict is not None
    assert result.accepted or result.final_verdict.status in (
        "relevant",
        "partial",
    )
    assert result.evidence_text  # для Supervisor


def test_draft_search_brief():
    b = draft_search_brief("solar battery storage", ["01-Energy"])
    assert "01-Energy" in b.domains
    assert "solar" in b.query_anchors


@pytest.mark.asyncio
async def test_wrap_hierarchical_facade_retrieve():
    store = _store_with_docs()
    facade = wrap_hierarchical_memory(store, use_hybrid=False, max_domains=2)
    res = await facade.retrieve("solar battery energy")
    assert facade.last_trace is not None
    assert facade.last_trace.brief is not None
    # либо dossier chunks, либо flat fallback — не падаем
    assert isinstance(res.chunks, list)


class _FakeSupervisorBackend:
    def __init__(self, payload: str):
        self.payload = payload
        self.calls = 0

    async def generate(self, prompt, ctx, **kwargs):
        self.calls += 1
        return self.payload


@pytest.mark.asyncio
async def test_supervisor_writes_search_brief():
    from krepost.memory.supervisor_brief import SupervisorBriefDrafter

    store = _store_with_docs()
    facade = wrap_hierarchical_memory(store, use_hybrid=False, max_domains=2)
    backend = _FakeSupervisorBackend(
        '{"query_anchors":["solar","battery"],"domains":["01-Energy"],"round":0}'
    )
    facade.set_supervisor_backend(backend)
    # DomainRouter может вернуть другие id — подменим draft path через allowed
    # Фасад роутит сам; backend обязан вернуть domain из ALLOWED.
    # Форсим brief_drafter напрямую с allowed = 01-Energy:
    drafter = SupervisorBriefDrafter(backend)
    brief = await drafter.draft(
        "tell me about solar",
        ["01-Energy", "04-Philosophy_AI"],
    )
    assert drafter.last_source == "llm"
    assert brief.query_anchors == ["solar", "battery"]
    assert brief.domains == ["01-Energy"]
    assert backend.calls == 1


@pytest.mark.asyncio
async def test_supervisor_brief_fail_open_heuristic():
    from krepost.memory.supervisor_brief import SupervisorBriefDrafter

    class Boom:
        async def generate(self, *a, **k):
            raise RuntimeError("lm down")

    drafter = SupervisorBriefDrafter(Boom())
    brief = await drafter.draft("solar battery pack", ["01-Energy"])
    assert drafter.last_source == "heuristic"
    assert "01-Energy" in brief.domains
    assert "solar" in brief.query_anchors


def test_supervisor_clamps_invented_domains():
    from krepost.memory.supervisor_brief import _clamp_domains

    assert _clamp_domains(["evil", "01-Energy"], ["01-Energy", "02-X"]) == [
        "01-Energy"
    ]
