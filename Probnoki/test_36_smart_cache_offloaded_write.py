"""
Пробник #36 (BUG-04): запись .npz в L1-кэше не должна блокировать event loop.

async encode() звал синхронный _put() → _save_embeddings() → np.savez_compressed
прямо в корутине (100–300 мс фризы под нагрузкой). Фикс: мутация словарей
остаётся на loop (быстро, атомарно), а savez уходит в asyncio.to_thread по
снимку, сериализованный asyncio.Lock (без гонки на общий tmp-файл).

Проверяем детерминированно: _atomic_write_npz исполняется в потоке != потока
event loop. Плюс функциональность (encode возвращает вектор, конкурентные
encode не падают).
"""
import asyncio
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from krepost.cache.SMART_CACHE import QueryEmbeddingCache


class _FakeEncoder:
    """Мини-энкодер без torch: детерминированный вектор по хешу длины."""

    def encode(self, text, convert_to_numpy=True, normalize_embeddings=True):
        return np.full(4, float(len(text) % 5), dtype=np.float32)

    def get_sentence_embedding_dimension(self):
        return 4

    def _first_module(self):
        return SimpleNamespace(
            auto_model=SimpleNamespace(config=SimpleNamespace(_name_or_path="fake")))


class TestNpzWriteOffLoop:

    @pytest.mark.asyncio
    async def test_savez_runs_off_event_loop(self, tmp_path):
        loop_thread = threading.get_ident()
        cache = QueryEmbeddingCache(_FakeEncoder(), cache_dir=tmp_path)
        seen = {}
        orig = cache._atomic_write_npz

        def spy(path, arrays):
            seen["thread"] = threading.get_ident()
            return orig(path, arrays)

        cache._atomic_write_npz = spy
        vec = await cache.encode("привет")
        assert vec.shape == (4,)
        assert "thread" in seen, "запись .npz не произошла"
        assert seen["thread"] != loop_thread, \
            "np.savez исполнился в потоке event loop — блокирует его"

    @pytest.mark.asyncio
    async def test_concurrent_encode_no_error_and_persists(self, tmp_path):
        cache = QueryEmbeddingCache(_FakeEncoder(), cache_dir=tmp_path)
        queries = [f"запрос-{i}" for i in range(50)]
        results = await asyncio.gather(*(cache.encode(q) for q in queries))
        assert len(results) == 50
        assert all(r.shape == (4,) for r in results)
        # перезагрузка видит сохранённое (durability не сломана)
        cache2 = QueryEmbeddingCache(_FakeEncoder(), cache_dir=tmp_path)
        assert len(cache2._entries) == 50
