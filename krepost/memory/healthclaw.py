"""
HealthClaw-style induction поверх EpisodicMemory (ROADMAP СЕЙЧАС).

После эпизода решаем: profile | procedure | keep_episodic | discard.
Детерминированный scaffold (без LLM). LLM-judge — следующий шаг.
Не раздувает контекст сам — только метка + опц. запись в store.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

Disposition = Literal["profile", "procedure", "keep_episodic", "discard"]

_PROC = re.compile(
    r"\b(how to|steps?|procedure|инструкц|как сделать|шаг\s*\d|сначала|затем)\b",
    re.I,
)
_PROF = re.compile(
    r"(my name|i prefer|предпочит|зовут|предпочтен|always|никогда не|\bвсегда\b)",
    re.I,
)
_NOISE = re.compile(
    r"(capital of france|2\s*\+\s*2|\bhello\b|\bпривет\b|\bping\b)",
    re.I,
)


@dataclass
class InductionVerdict:
    disposition: Disposition
    reason: str
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)


class HealthClawInductor:
    """Эвристический inductor: query+response+verdict → Disposition."""

    def __init__(self, *, min_chars: int = 40):
        self.min_chars = min_chars

    def induce(
        self,
        *,
        query: str,
        response: str,
        security_verdict: str = "GREEN",
        status: str = "ok",
    ) -> InductionVerdict:
        q = (query or "").strip()
        r = (response or "").strip()
        blob = f"{q}\n{r}"
        sev = str(security_verdict or "GREEN").upper()

        if sev in ("RED", "YELLOW") or status.startswith("blocked"):
            return InductionVerdict(
                "discard",
                reason=f"security={sev} status={status}",
                confidence=0.9,
                tags=["security"],
            )
        if len(blob) < self.min_chars or _NOISE.search(q):
            return InductionVerdict(
                "discard",
                reason="short_or_noise",
                confidence=0.7,
                tags=["noise"],
            )
        if _PROF.search(blob):
            return InductionVerdict(
                "profile",
                reason="preference_or_identity_signal",
                confidence=0.65,
                tags=["profile"],
            )
        if _PROC.search(blob) or (len(r) > 400 and "\n" in r):
            return InductionVerdict(
                "procedure",
                reason="howto_or_long_structured",
                confidence=0.6,
                tags=["procedure"],
            )
        return InductionVerdict(
            "keep_episodic",
            reason="default_retain",
            confidence=0.55,
            tags=["episodic"],
        )


class InductionStore:
    """Простые JSONL-сторы profile/procedure рядом с episodic."""

    def __init__(self, base_dir: Path):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.base / "healthclaw_profile.jsonl"
        self.procedure_path = self.base / "healthclaw_procedures.jsonl"

    def persist(
        self,
        verdict: InductionVerdict,
        *,
        query: str,
        response: str,
        session_id: str,
        episode_id: Optional[str] = None,
    ) -> None:
        if verdict.disposition not in ("profile", "procedure"):
            return
        path = (
            self.profile_path
            if verdict.disposition == "profile"
            else self.procedure_path
        )
        row: Dict[str, Any] = {
            "disposition": verdict.disposition,
            "reason": verdict.reason,
            "confidence": verdict.confidence,
            "tags": verdict.tags,
            "query": (query or "")[:2000],
            "response": (response or "")[:4000],
            "session_id": session_id,
            "episode_id": episode_id,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


async def induce_after_episode(
    *,
    query: str,
    response: str,
    session_id: str,
    security_verdict: Any = "GREEN",
    status: str = "ok",
    episode_id: Optional[str] = None,
    store: Optional[InductionStore] = None,
    inductor: Optional[HealthClawInductor] = None,
) -> InductionVerdict:
    ind = inductor or HealthClawInductor()
    verdict = ind.induce(
        query=query,
        response=response,
        security_verdict=str(security_verdict),
        status=status,
    )
    if store is not None:
        store.persist(
            verdict,
            query=query,
            response=response,
            session_id=session_id,
            episode_id=episode_id,
        )
    return verdict
