"""Coordinator: Planner → recipes → HTTP target → black-box feedback → repeat."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from ataker.feedback import FeedbackEntry, OperatorTrace, hit_to_trace
from ataker.planner import Planner, StubPlanner
from ataker.planner_types import PlannerInput, PlannerOutput
from ataker.recipe_executor import build_batch
from ataker.target_http import HitResult, KrepostHttpTarget


class DryTarget(Protocol):
    """Для тестов без сети."""

    def post_query(self, text: str, *, session_id: Optional[str] = None) -> HitResult: ...


@dataclass
class IterationRecord:
    iteration: int
    planner: Dict[str, Any]
    feedback: List[Dict[str, Any]]
    traces: List[Dict[str, Any]]
    bypassed: int
    blocked: int
    errors: int


@dataclass
class AdversarialReport:
    run_id: str
    target_url: str
    iterations: int
    total_hits: int
    blocked: int
    bypassed: int
    errors: int
    stop_reason: str
    hypothesis: str = ""
    records: List[IterationRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "target_url": self.target_url,
            "iterations": self.iterations,
            "total_hits": self.total_hits,
            "blocked": self.blocked,
            "bypassed": self.bypassed,
            "errors": self.errors,
            "stop_reason": self.stop_reason,
            "hypothesis": self.hypothesis,
            "records": [asdict(r) for r in self.records],
        }

    def summary(self) -> str:
        return (
            f"run={self.run_id} iters={self.iterations} hits={self.total_hits} "
            f"BLOCK={self.blocked} BYPASS={self.bypassed} ERR={self.errors} "
            f"stop={self.stop_reason}"
        )


@dataclass
class AdversarialLoop:
    """Петля Planner-Executor против Krepost HTTP."""

    target: KrepostHttpTarget | DryTarget
    planner: Planner | None = None
    batch_size: int = 5
    max_iterations: int = 3
    stop_on_bypass: bool = True
    seed: int = 0
    report_dir: Optional[Path] = None

    def run(self) -> AdversarialReport:
        planner = self.planner or StubPlanner(seed=self.seed)
        run_id = time.strftime("adv_%Y%m%d_%H%M%S")
        target_url = getattr(self.target, "base_url", "dry")
        feedback_hist: List[FeedbackEntry] = []
        records: List[IterationRecord] = []
        total_b = total_x = total_e = total_hits = 0
        stop_reason = "max_iterations"
        last_hypothesis = ""

        for it in range(1, self.max_iterations + 1):
            inp = PlannerInput(
                iteration=it,
                feedback=list(feedback_hist),
                batch_size=self.batch_size,
            )
            # Страж black-box
            view = inp.planner_view()
            assert "layer" not in view
            for fb in view["feedback"]:
                assert "layer" not in fb
                assert "answer" not in fb

            out: PlannerOutput = planner.plan(inp)
            last_hypothesis = out.hypothesis
            payloads = build_batch(out.attack_recipes, seed=self.seed + it)

            iter_fb: List[FeedbackEntry] = []
            traces: List[OperatorTrace] = []
            b = x = e = 0

            for payload in payloads:
                hit = self.target.post_query(payload.mutated)
                trace = hit_to_trace(
                    hit,
                    payload_text=payload.mutated,
                    category=payload.category.value,
                    mutations=payload.mutations_applied,
                    technique_ref=(payload.metadata or {}).get("technique_ref"),
                )
                traces.append(trace)
                iter_fb.append(trace.feedback)
                total_hits += 1
                if hit.mark == "BLOCK":
                    b += 1
                    total_b += 1
                elif hit.mark == "BYPASS":
                    x += 1
                    total_x += 1
                else:
                    e += 1
                    total_e += 1

            feedback_hist.extend(iter_fb)
            # Скользящее окно: последние 3*batch
            window = self.batch_size * 3
            if len(feedback_hist) > window:
                feedback_hist = feedback_hist[-window:]

            records.append(
                IterationRecord(
                    iteration=it,
                    planner=out.to_dict(),
                    feedback=[f.to_dict() for f in iter_fb],
                    traces=[t.to_dict() for t in traces],
                    bypassed=x,
                    blocked=b,
                    errors=e,
                )
            )

            if self.stop_on_bypass and x > 0:
                stop_reason = "bypass"
                break

        report = AdversarialReport(
            run_id=run_id,
            target_url=str(target_url),
            iterations=len(records),
            total_hits=total_hits,
            blocked=total_b,
            bypassed=total_x,
            errors=total_e,
            stop_reason=stop_reason,
            hypothesis=last_hypothesis,
            records=records,
        )

        if self.report_dir is not None:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            path = self.report_dir / f"harness_{run_id}.json"
            path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return report
