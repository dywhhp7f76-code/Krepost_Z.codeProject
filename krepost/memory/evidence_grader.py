"""
EvidenceGrader — relevant / partial / irrelevant к вопросу (Phase 4).

Не замена Supervisor. Детерминированный scaffold; LLM-judge — позже.
"""
from __future__ import annotations

from typing import Sequence

from krepost.memory.search_brief import (
    GradeVerdict,
    ReaderDossier,
    SearchBrief,
)


class EvidenceGrader:
    """
    status:
      relevant   — все anchors покрыты dossier
      partial    — часть anchors
      irrelevant — нет покрытия / пустые dossier
    """

    def __init__(self, *, partial_ratio: float = 0.34):
        self.partial_ratio = partial_ratio

    def grade(
        self,
        brief: SearchBrief,
        dossiers: Sequence[ReaderDossier],
    ) -> GradeVerdict:
        anchors = [a.strip().lower() for a in brief.query_anchors if a.strip()]
        blob = " ".join(
            (d.summary_or_extract or "") + " " + " ".join(d.citations)
            for d in dossiers
        ).lower()
        non_empty = [d for d in dossiers if (d.summary_or_extract or "").strip()]

        if not non_empty:
            return GradeVerdict(
                status="irrelevant",
                missing_anchors=list(brief.query_anchors),
                note="empty dossiers",
            )

        if not anchors:
            # нет якорей — есть хоть какой-то extract → partial (Supervisor уточнит)
            return GradeVerdict(
                status="partial",
                missing_anchors=[],
                note="no anchors; extract present",
            )

        missing = [a for a in brief.query_anchors if a.strip().lower() not in blob]
        hit = sum(1 for a in anchors if a in blob)
        ratio = hit / len(anchors)

        if ratio >= 1.0:
            return GradeVerdict(status="relevant", missing_anchors=[], note="all anchors")
        if ratio >= self.partial_ratio:
            return GradeVerdict(
                status="partial",
                missing_anchors=missing,
                note=f"anchor_ratio={ratio:.2f}",
            )
        return GradeVerdict(
            status="irrelevant",
            missing_anchors=missing or list(brief.query_anchors),
            note=f"anchor_ratio={ratio:.2f}",
        )
