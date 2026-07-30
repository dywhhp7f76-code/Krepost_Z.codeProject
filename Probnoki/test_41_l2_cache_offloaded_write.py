"""
Пробник #41 (BUG-04 L2): запись .npz в L2.put не на event loop.

Зеркало #36 для RAGResultsCache.put — savez уходит в to_thread по снимку.
"""
import asyncio
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from krepost.cache.SMART_CACHE import (
    QueryEmbeddingCache,
    RAGResultsCache,
    SecurityVerdict,
)


class _FakeEncoder:
    def encode(self, text, convert_to_numpy=True, normalize_embeddings=True):
        return np.full(4, float(len(text) % 5), dtype=np.float32)

    def get_sentence_embedding_dimension(self):
        return 4

    def _first_module(self):
        return SimpleNamespace(
            auto_model=SimpleNamespace(config=SimpleNamespace(_name_or_path="fake")))


@pytest.mark.asyncio
async def test_l2_savez_runs_off_event_loop(tmp_path):
    loop_thread = threading.get_ident()
    l1 = QueryEmbeddingCache(_FakeEncoder(), cache_dir=tmp_path)
    l2 = RAGResultsCache(l1, cache_dir=tmp_path)
    seen = {}
    orig = l2._atomic_write_npz

    def spy(path, arrays):
        seen["thread"] = threading.get_ident()
        return orig(path, arrays)

    l2._atomic_write_npz = spy
    key = await l2.put(
        "запрос про крепость",
        chunks=[{"text": "chunk"}],
        source_notes=["note.md"],
        verdict=SecurityVerdict.GREEN,
    )
    assert key is not None
    assert "thread" in seen, "L2 запись .npz не произошла"
    assert seen["thread"] != loop_thread, "L2 savez на event loop"


@pytest.mark.asyncio
async def test_l2_put_persists(tmp_path):
    l1 = QueryEmbeddingCache(_FakeEncoder(), cache_dir=tmp_path)
    l2 = RAGResultsCache(l1, cache_dir=tmp_path)
    await l2.put(
        "persist-me",
        chunks=[{"text": "c"}],
        source_notes=["a.md"],
        verdict=SecurityVerdict.GREEN,
    )
    l1b = QueryEmbeddingCache(_FakeEncoder(), cache_dir=tmp_path)
    l2b = RAGResultsCache(l1b, cache_dir=tmp_path)
    assert len(l2b._entries) >= 1
