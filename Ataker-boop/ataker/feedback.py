"""Black-box feedback Исполнитель → Творец.

Planner видит только verdict + bypassed (+ агрегаты).
layer / answer / raw — только в операторский лог.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from ataker.target_http import HitResult


@dataclass
class FeedbackEntry:
    """То, что видит Planner (чёрный ящик)."""

    verdict: str
    bypassed: bool
    mark: str = ""  # BLOCK|BYPASS|ERR — удобно для stub-стратегий
    category: Optional[str] = None
    mutations: List[str] = field(default_factory=list)
    technique_ref: Optional[str] = None
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OperatorTrace:
    """Полный след для оператора / vault — НЕ отдаём Planner."""

    feedback: FeedbackEntry
    layer: Optional[str] = None
    answer_preview: str = ""
    payload_preview: str = ""
    raw_status: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["feedback"] = self.feedback.to_dict()
        return d


def hit_to_feedback(
    hit: HitResult,
    *,
    category: Optional[str] = None,
    mutations: Optional[List[str]] = None,
    technique_ref: Optional[str] = None,
) -> FeedbackEntry:
    """Собрать black-box entry из HitResult."""
    return FeedbackEntry(
        verdict=hit.verdict or hit.mark,
        bypassed=hit.bypassed,
        mark=hit.mark,
        category=category,
        mutations=list(mutations or []),
        technique_ref=technique_ref,
        latency_ms=hit.latency_ms,
    )


def hit_to_trace(
    hit: HitResult,
    *,
    payload_text: str = "",
    category: Optional[str] = None,
    mutations: Optional[List[str]] = None,
    technique_ref: Optional[str] = None,
) -> OperatorTrace:
    fb = hit_to_feedback(
        hit,
        category=category,
        mutations=mutations,
        technique_ref=technique_ref,
    )
    return OperatorTrace(
        feedback=fb,
        layer=hit.layer,
        answer_preview=(hit.answer or "")[:200],
        payload_preview=(payload_text or "")[:120],
        raw_status=hit.status,
        error=hit.error,
    )


def assert_planner_safe(payload: Dict[str, Any]) -> None:
    """Тестовый страж: в dict для Planner не должно быть layer/answer/raw."""
    forbidden = {"layer", "answer", "answer_preview", "raw", "body", "diagnostics"}
    bad = forbidden.intersection(payload.keys())
    if bad:
        raise AssertionError(f"Planner payload leaks: {sorted(bad)}")
