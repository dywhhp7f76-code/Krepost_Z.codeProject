"""
Пробник #41 (Т2): Immutable raw + type=raw/derived.

memory/2026-06-28: LLM, переписывающие свою память, деградируют (100%→52.6%).
add() пишет чанки с type="raw" по умолчанию (неизменяемый первоисточник);
caller может явно передать type="derived" для summary/дериватива. raw НЕ
перезаписывается моделью — реорганизация только детерминированными скриптами.
"""
import math

from krepost.memory.store import MemoryStore


VOCAB = {"python": 0, "list": 1, "append": 2}


class BowEmbedder:
    def encode(self, text):
        v = [0.0] * len(VOCAB)
        for w in text.lower().split():
            if w in VOCAB:
                v[VOCAB[w]] = 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]


class FakeCollection:
    def __init__(self):
        self.added = []

    def add(self, *, ids, embeddings, documents, metadatas):
        for i, _id in enumerate(ids):
            self.added.append({"id": _id, "meta": metadatas[i], "doc": documents[i]})

    def query(self, *, query_embeddings, n_results):
        return {"distances": [[]], "documents": [[]], "metadatas": [[]]}


def _store(**kw):
    return MemoryStore(BowEmbedder(), FakeCollection(), **kw)


class TestImmutableRawType:

    def test_raw_default_type(self):
        s = _store()
        s.add_sync("d1", "python list append")
        assert all(m["meta"]["type"] == "raw" for m in s.collection.added)

    def test_explicit_derived_preserved(self):
        s = _store()
        s.add_sync("d1", "python list append", metadata={"type": "derived"})
        assert all(m["meta"]["type"] == "derived" for m in s.collection.added)

    def test_user_metadata_merged_with_type(self):
        s = _store()
        s.add_sync("d1", "python list append", metadata={"src": "notes.md", "tag": "ref"})
        m = s.collection.added[0]["meta"]
        assert m["type"] == "raw"
        assert m["src"] == "notes.md"
        assert m["tag"] == "ref"
        assert m["doc_id"] == "d1"
        assert m["chunk"] == 0

    def test_raw_chunks_are_distinct_ids(self):
        s = _store(chunk_max_chars=30, chunk_overlap=5)
        s.add_sync("d1", "python list append. " * 10)
        # несколько чанков — каждый со своим chunk-индексом, но type=raw
        types = {m["meta"]["type"] for m in s.collection.added}
        assert types == {"raw"}
        idxs = [m["meta"]["chunk"] for m in s.collection.added]
        assert idxs == list(range(len(idxs)))
