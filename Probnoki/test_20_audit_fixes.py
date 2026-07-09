"""
Пробник #20: фиксы внешнего аудита main (PR #1, шаг 1).

Проверяет:
1.1 Глобальный lock снят с горячего пути: два конкурентных process() с
    медленным Guard выполняются параллельно, а не последовательно;
    process() после close() по-прежнему кидает RuntimeError.
1.2 Numpy truthiness: mock-эмбеддер возвращает np.ndarray; повторный
    запрос (эмбеддинг берётся из кэша) даёт ТОТ ЖЕ вердикт, а не
    ValueError -> fail-closed RED.
1.3 Пустая few-shot БД — холодный старт, НЕ ошибка: (False, [], None);
    fail-closed остаётся для реальных аномалий (None-ответ, исключение).
"""

import asyncio
import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from krepost.security.pipeline import FewShotMatcher, SecurityPipeline


# ═══════════════════════════════════════════════════════════════════════════
# 1.2 Numpy truthiness в FewShotMatcher.match()
# ═══════════════════════════════════════════════════════════════════════════

def _ndarray_embedder():
    """Эмбеддер как sentence-transformers по умолчанию: возвращает np.ndarray."""
    embedder = MagicMock()
    embedder.encode = MagicMock(return_value=np.array([0.1, 0.2, 0.3]))
    return embedder


def _green_collection():
    collection = MagicMock()
    collection.metadata = {"hnsw:space": "cosine"}
    collection.query = MagicMock(return_value={
        "distances": [[0.5]],           # similarity 0.5 < threshold -> нет match
        "documents": [["пример"]],
        "metadatas": [[{"label": "GREEN"}]],
    })
    return collection


class TestNumpyTruthiness:

    @pytest.mark.asyncio
    async def test_repeat_query_same_verdict_with_ndarray(self):
        """Один текст дважды: второй раз эмбеддинг из кэша (np.ndarray).
        До фикса `if cached:` кидал ValueError -> fail-closed на повторе."""
        matcher = FewShotMatcher(
            embedder=_ndarray_embedder(), chroma_collection=_green_collection()
        )
        first = await matcher.match("повторяющийся запрос")
        second = await matcher.match("повторяющийся запрос")

        assert first == second, f"вердикты разошлись: {first} != {second}"
        assert second[2] is None, f"повтор ушёл в fail-closed: {second[2]}"

    @pytest.mark.asyncio
    async def test_second_call_uses_cache_not_encoder(self):
        """Повторный вызов не должен заново кодировать текст."""
        embedder = _ndarray_embedder()
        matcher = FewShotMatcher(
            embedder=embedder, chroma_collection=_green_collection()
        )
        await matcher.match("текст")
        await matcher.match("текст")
        assert embedder.encode.call_count == 1


# ═══════════════════════════════════════════════════════════════════════════
# 1.3 Пустая few-shot БД = холодный старт
# ═══════════════════════════════════════════════════════════════════════════

class TestEmptyDbColdStart:

    @pytest.mark.asyncio
    async def test_empty_db_is_not_an_error(self):
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        collection.query = MagicMock(return_value={
            "distances": [[]], "documents": [[]], "metadatas": [[]],
        })
        matcher = FewShotMatcher(
            embedder=_ndarray_embedder(), chroma_collection=collection
        )
        blocked, matches, reason = await matcher.match("холодный старт")
        assert blocked is False
        assert matches == []
        assert reason is None

    @pytest.mark.asyncio
    async def test_malformed_response_still_fail_closed(self):
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        collection.query = MagicMock(return_value=None)
        matcher = FewShotMatcher(
            embedder=_ndarray_embedder(), chroma_collection=collection
        )
        blocked, _, reason = await matcher.match("аномалия")
        assert blocked is True
        assert reason == "fewshot_invalid_response_fail_closed"

    @pytest.mark.asyncio
    async def test_exception_still_fail_closed(self):
        collection = MagicMock()
        collection.metadata = {"hnsw:space": "cosine"}
        collection.query = MagicMock(side_effect=RuntimeError("DB crashed"))
        matcher = FewShotMatcher(
            embedder=_ndarray_embedder(), chroma_collection=collection
        )
        blocked, _, reason = await matcher.match("сбой")
        assert blocked is True
        assert reason == "fewshot_error_fail_closed"


# ═══════════════════════════════════════════════════════════════════════════
# 1.1 Глобальный lock снят с горячего пути process()
# ═══════════════════════════════════════════════════════════════════════════

class _SlowGuardClient:
    """Guard, отвечающий GREEN с задержкой — имитация реального инференса."""

    def __init__(self, delay: float):
        self.delay = delay

    async def chat(self, model=None, messages=None, format=None):
        await asyncio.sleep(self.delay)
        return {"message": {"content":
                '{"status":"GREEN","reason":"ok","confidence":0.9}'}}


def _pipeline_with_slow_guard(tmp_path, delay: float) -> SecurityPipeline:
    return SecurityPipeline(
        guard_client=_SlowGuardClient(delay),
        trust_db_path=tmp_path / "trust.db",
    )


class TestNoGlobalLockOnHotPath:

    @pytest.mark.asyncio
    async def test_concurrent_requests_run_in_parallel(self, tmp_path):
        """4 конкурентных запроса с Guard ~0.3с: при глобальном lock суммарно
        было бы >= 1.2с (строгая очередь), параллельно — около 0.3с."""
        delay = 0.3
        p = _pipeline_with_slow_guard(tmp_path, delay)

        start = time.perf_counter()
        results = await asyncio.gather(*[
            p.process(f"обычный вопрос номер {i}", session_id=f"s{i}")
            for i in range(4)
        ])
        elapsed = time.perf_counter() - start

        assert all(r.verdict == "GREEN" for r in results), \
            [r.verdict for r in results]
        assert elapsed < delay * 4, (
            f"запросы выполнялись последовательно: {elapsed:.2f}s "
            f">= {delay * 4:.2f}s — глобальный lock вернулся?"
        )

    @pytest.mark.asyncio
    async def test_process_after_close_still_raises(self, tmp_path):
        """Снятие lock не сломало fail-closed на закрытом пайплайне."""
        p = _pipeline_with_slow_guard(tmp_path, 0.01)
        await p.close()
        with pytest.raises(RuntimeError, match="closed"):
            await p.process("запрос после close", session_id="s1")
