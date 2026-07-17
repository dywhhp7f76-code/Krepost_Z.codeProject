"""
Эмбеддинг-роутер доменов (MEMORY_ROUTER_SPEC §2).

Лёгкий: без вызова основного LLM. Вход — запрос, выход — список domain id
для опроса (может быть >1). Авто-создание доменов запрещено.
"""
from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from krepost.memory.domains import DEFAULT_DOMAINS, DomainSpec, FALLBACK_DOMAIN


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return float(dot / (na * nb))


def _to_float_list(v: Any) -> List[float]:
    if hasattr(v, "tolist"):
        v = v.tolist()
    if v and isinstance(v[0], (list, tuple)):
        v = v[0]
    return [float(x) for x in v]


@dataclass(frozen=True)
class DomainHit:
    domain_id: str
    score: float


class DomainRouter:
    """Классификация запроса → top-N доменов по cosine к лейблам домена."""

    def __init__(
        self,
        embedder: Any,
        domains: Sequence[DomainSpec] | None = None,
        *,
        min_score: float = 0.22,
        max_domains: int = 3,
        always_include_fallback: bool = False,
    ):
        self.embedder = embedder
        self.domains: Tuple[DomainSpec, ...] = tuple(domains or DEFAULT_DOMAINS)
        self.min_score = min_score
        self.max_domains = max(1, max_domains)
        self.always_include_fallback = always_include_fallback
        self._centroids: Optional[List[Tuple[str, List[float]]]] = None

    def _embed_sync(self, text: str) -> List[float]:
        return _to_float_list(self.embedder.encode(text))

    async def _embed(self, text: str) -> List[float]:
        v = await asyncio.to_thread(self.embedder.encode, text)
        return _to_float_list(v)

    def _ensure_centroids(self) -> List[Tuple[str, List[float]]]:
        if self._centroids is None:
            out: List[Tuple[str, List[float]]] = []
            for d in self.domains:
                label = " ".join(d.labels)
                out.append((d.id, self._embed_sync(label)))
            self._centroids = out
        return self._centroids

    def route_sync(self, query: str) -> List[DomainHit]:
        if not query or not query.strip():
            return [DomainHit(FALLBACK_DOMAIN, 0.0)]
        q = self._embed_sync(query)
        hits = [
            DomainHit(did, _cosine(q, vec))
            for did, vec in self._ensure_centroids()
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        picked = [h for h in hits if h.score >= self.min_score][: self.max_domains]
        if not picked:
            picked = hits[:1] if hits else [DomainHit(FALLBACK_DOMAIN, 0.0)]
        if self.always_include_fallback and not any(
            h.domain_id == FALLBACK_DOMAIN for h in picked
        ):
            fb = next((h for h in hits if h.domain_id == FALLBACK_DOMAIN), None)
            if fb is not None and len(picked) < self.max_domains:
                picked.append(fb)
        return picked

    async def route(self, query: str) -> List[DomainHit]:
        if not query or not query.strip():
            return [DomainHit(FALLBACK_DOMAIN, 0.0)]
        q = await self._embed(query)
        # centroids ещё могут быть не прогреты — прогрев sync в thread
        await asyncio.to_thread(self._ensure_centroids)
        hits = [
            DomainHit(did, _cosine(q, vec))
            for did, vec in (self._centroids or [])
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        picked = [h for h in hits if h.score >= self.min_score][: self.max_domains]
        if not picked:
            picked = hits[:1] if hits else [DomainHit(FALLBACK_DOMAIN, 0.0)]
        if self.always_include_fallback and not any(
            h.domain_id == FALLBACK_DOMAIN for h in picked
        ):
            fb = next((h for h in hits if h.domain_id == FALLBACK_DOMAIN), None)
            if fb is not None and len(picked) < self.max_domains:
                picked.append(fb)
        return picked

    def domain_ids(self, query: str) -> List[str]:
        return [h.domain_id for h in self.route_sync(query)]
