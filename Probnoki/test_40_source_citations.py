"""
Пробник #40 (Т1): Source citations в build_context.

Паттерн LocalAI 4.4.0 — каждый найденный фрагмент помечается цитатой источника
[src: файл#чанк], чтобы модель (и оператор) видели происхождение данных.
memory/2026-06-16: сигнал силы — повтор в 4 дайджестах.
"""
import math

from krepost.memory.store import MemoryStore, RetrievalResult, RetrievedChunk


# ---- детерминированный bag-of-words эмбеддер (из test_28) ----
VOCAB = {"python": 0, "list": 1, "append": 2, "weather": 3, "sunny": 4}


class BowEmbedder:
    def encode(self, text):
        v = [0.0] * len(VOCAB)
        for w in text.lower().split():
            if w in VOCAB:
                v[VOCAB[w]] = 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


def _chunks_with_meta():
    return [
        RetrievedChunk(text="python list append", score=0.9, doc_id="notes.md",
                       metadata={"doc_id": "notes.md", "chunk": 0, "src": "obsidian/notes.md"}),
        RetrievedChunk(text="weather sunny today", score=0.7, doc_id="log.md",
                       metadata={"doc_id": "log.md", "chunk": 2}),
    ]


class TestSourceCitations:

    def test_citation_rendered_with_src(self):
        store = MemoryStore(BowEmbedder(), collection=None)
        ctx = store.build_context(RetrievalResult("q", _chunks_with_meta(), 0.9, True))
        assert "[src: obsidian/notes.md#0]" in ctx
        assert "[src: log.md#2]" in ctx

    def test_fallback_to_doc_id_when_no_src(self):
        store = MemoryStore(BowEmbedder(), collection=None)
        ctx = store.build_context(RetrievalResult("q", _chunks_with_meta(), 0.9, True))
        # второй чанк не имеет 'src' — должен фолбэчить на doc_id
        assert "[src: log.md#2]" in ctx

    def test_no_chunk_index_no_hash(self):
        store = MemoryStore(BowEmbedder(), collection=None)
        ch = [RetrievedChunk(text="x", score=0.9, doc_id="a.md", metadata={"src": "a.md"})]
        ctx = store.build_context(RetrievalResult("q", ch, 0.9, True))
        assert "[src: a.md]" in ctx
        assert "#" not in ctx.split("[src: a.md]")[1].split("]")[0]

    def test_guard_rescan_compatible(self):
        from krepost.security.tool_guard import ToolOutputGuard
        store = MemoryStore(BowEmbedder(), collection=None)
        ch = [RetrievedChunk(text="normal data", score=0.9, doc_id="n.md",
                             metadata={"doc_id": "n.md", "chunk": 0})]
        ctx = store.build_context(RetrievalResult("q", ch, 0.9, True), guard=ToolOutputGuard())
        assert "[src: n.md#0]" in ctx

    def test_empty_context_no_citation(self):
        store = MemoryStore(BowEmbedder(), collection=None)
        ctx = store.build_context(RetrievalResult("q", [], 0.0, False))
        assert ctx == ""
