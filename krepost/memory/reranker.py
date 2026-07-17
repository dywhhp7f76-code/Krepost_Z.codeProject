"""
Reranker («вахтёр») — обязательный клапан нагрузки (MEMORY_ROUTER_SPEC §4).

В контекст основного LLM идёт ТОЛЬКО top-N после rerank, не всё найденное.
По умолчанию — ScoreReranker (без доп. модели). CrossEncoder — опционально
(bge-reranker), ленивый импорт.
"""
from __future__ import annotations

import asyncio
from typing import Any, List, Optional, Protocol, Sequence

from krepost.memory.store import RetrievedChunk


class Reranker(Protocol):
    def rerank(
        self, query: str, chunks: Sequence[RetrievedChunk], *, top_n: int
    ) -> List[RetrievedChunk]: ...


class ScoreReranker:
    """Детерминированный вахтёр: сортировка по уже посчитанному score."""

    def rerank(
        self, query: str, chunks: Sequence[RetrievedChunk], *, top_n: int
    ) -> List[RetrievedChunk]:
        ordered = sorted(chunks, key=lambda c: c.score, reverse=True)
        return list(ordered[: max(0, top_n)])


class CrossEncoderReranker:
    """bge-reranker / CrossEncoder. Тяжёлая модель — поднимать по требованию."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model: Any = None

    def _ensure(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self, query: str, chunks: Sequence[RetrievedChunk], *, top_n: int
    ) -> List[RetrievedChunk]:
        if not chunks:
            return []
        model = self._ensure()
        pairs = [(query, c.text) for c in chunks]
        scores = model.predict(pairs)
        ranked = sorted(
            zip(chunks, scores),
            key=lambda x: float(x[1]),
            reverse=True,
        )
        out: List[RetrievedChunk] = []
        for chunk, sc in ranked[: max(0, top_n)]:
            meta = dict(chunk.metadata)
            meta["rerank_score"] = float(sc)
            out.append(
                RetrievedChunk(
                    text=chunk.text,
                    score=float(sc),
                    doc_id=chunk.doc_id,
                    metadata=meta,
                )
            )
        return out

    async def rerank_async(
        self, query: str, chunks: Sequence[RetrievedChunk], *, top_n: int
    ) -> List[RetrievedChunk]:
        return await asyncio.to_thread(self.rerank, query, chunks, top_n=top_n)


def make_default_reranker(
    *,
    use_cross_encoder: bool = False,
    model_name: str = "BAAI/bge-reranker-v2-m3",
) -> Reranker:
    if use_cross_encoder:
        return CrossEncoderReranker(model_name)
    return ScoreReranker()
