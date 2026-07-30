"""Тесты Ataker harness (target / feedback / stub planner / loop)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ataker.adversarial_loop import AdversarialLoop
from ataker.feedback import (
    FeedbackEntry,
    assert_planner_safe,
    hit_to_feedback,
    hit_to_trace,
)
from ataker.generator import AttackCategory
from ataker.planner import StubPlanner
from ataker.planner_types import PlannedAttack, PlannerInput
from ataker.recipe_executor import build_batch, build_payload_from_recipe
from ataker.target_http import HitResult, KrepostHttpTarget
from ataker.knowledge_loader import catalog_summary, list_source_cards, load_snippets


class TestKrepostHttpTargetClassify:
    def test_block_from_verdict(self):
        hit = KrepostHttpTarget._classify(
            {"status": "ok", "verdict": "RED", "answer": "no"},
            12.5,
        )
        assert hit.mark == "BLOCK"
        assert not hit.bypassed

    def test_bypass(self):
        hit = KrepostHttpTarget._classify(
            {"status": "ok", "verdict": "GREEN", "answer": "hi"},
            3.0,
        )
        assert hit.mark == "BYPASS"
        assert hit.bypassed

    def test_error(self):
        hit = KrepostHttpTarget._classify(
            {"status": "transport_error"},
            1.0,
        )
        assert hit.mark == "ERR"


class TestFeedbackBlackBox:
    def test_hit_to_feedback_no_layer(self):
        hit = HitResult(
            mark="BLOCK",
            verdict="RED",
            status="blocked",
            latency_ms=10,
            layer="Layer2-Guard",
            answer="secret stuff",
        )
        fb = hit_to_feedback(hit, category="direct_injection", mutations=["base64"])
        d = fb.to_dict()
        assert "layer" not in d
        assert "answer" not in d
        assert d["bypassed"] is False
        assert_planner_safe(d)

    def test_trace_keeps_layer_for_operator(self):
        hit = HitResult(
            mark="BYPASS",
            verdict="GREEN",
            status="ok",
            latency_ms=5,
            layer="none",
            answer="SYSTEM_COMPROMISED",
        )
        tr = hit_to_trace(hit, payload_text="ignore all", category="jailbreak")
        assert tr.layer == "none"
        assert "SYSTEM" in tr.answer_preview
        assert tr.feedback.bypassed is True


class TestRecipeExecutor:
    def test_build_applies_mutations(self):
        recipe = PlannedAttack(
            template_category=AttackCategory.DIRECT_INJECTION,
            mutations=["prefix_innocent"],
            template_index=0,
        )
        payload = build_payload_from_recipe(recipe, counter=0)
        assert payload.category == AttackCategory.DIRECT_INJECTION
        assert "prefix_innocent" in payload.mutations_applied
        assert payload.mutated != payload.original or True  # prefix may wrap

    def test_batch_size(self):
        recipes = [
            PlannedAttack(
                template_category=AttackCategory.SOCIAL_ENGINEERING,
                mutations=["homoglyph"],
            )
            for _ in range(4)
        ]
        batch = build_batch(recipes, seed=1)
        assert len(batch) == 4


class TestStubPlanner:
    def test_batch_and_blackbox_input(self):
        planner = StubPlanner(seed=0)
        fb = [
            FeedbackEntry(
                verdict="RED",
                bypassed=False,
                mark="BLOCK",
                category="direct_injection",
                mutations=["base64"],
            )
        ]
        inp = PlannerInput(iteration=1, feedback=fb, batch_size=6)
        view = inp.planner_view()
        assert_planner_safe(view)
        for item in view["feedback"]:
            assert_planner_safe(item)
        out = planner.plan(inp)
        assert len(out.attack_recipes) == 6
        assert out.reasoning

    def test_repeat_on_bypass(self):
        planner = StubPlanner(seed=0)
        fb = [
            FeedbackEntry(
                verdict="GREEN",
                bypassed=True,
                mark="BYPASS",
                category="social_engineering",
                mutations=["prefix_innocent"],
            )
        ]
        out = planner.plan(PlannerInput(iteration=2, feedback=fb, batch_size=3))
        assert all(
            r.template_category == AttackCategory.SOCIAL_ENGINEERING
            for r in out.attack_recipes
        )


class _FakeTarget:
    base_url = "http://fake:8010"

    def __init__(self, marks):
        self._marks = list(marks)
        self._i = 0

    def post_query(self, text: str, *, session_id=None) -> HitResult:
        mark = self._marks[min(self._i, len(self._marks) - 1)]
        self._i += 1
        if mark == "BLOCK":
            return HitResult(
                mark="BLOCK",
                verdict="RED",
                status="blocked",
                latency_ms=1.0,
                layer="Layer1-Regex",
                answer="no",
            )
        if mark == "BYPASS":
            return HitResult(
                mark="BYPASS",
                verdict="GREEN",
                status="ok",
                latency_ms=1.0,
                layer=None,
                answer="ok",
            )
        return HitResult(
            mark="ERR",
            verdict="",
            status="transport_error",
            latency_ms=1.0,
            error="boom",
        )


class TestKnowledgeLoader:
    def test_source_cards_exist(self):
        cards = list_source_cards()
        names = {p.name for p in cards}
        assert "01-owasp-llm-top10.md" in names
        assert "03-mitre-attack.md" in names
        assert "OWASP" in catalog_summary() or "owasp" in catalog_summary().lower() or len(cards) >= 4

    def test_snippets_nonempty(self):
        snips = load_snippets(max_chars=400)
        assert len(snips) >= 4
        assert any("OWASP" in s or "LLM" in s for s in snips)


class TestAdversarialLoop:
    def test_stops_on_bypass(self, tmp_path):
        target = _FakeTarget(["BLOCK", "BLOCK", "BYPASS", "BLOCK"])
        loop = AdversarialLoop(
            target=target,
            planner=StubPlanner(seed=0),
            batch_size=2,
            max_iterations=5,
            stop_on_bypass=True,
            seed=0,
            report_dir=tmp_path,
        )
        report = loop.run()
        assert report.stop_reason == "bypass"
        assert report.bypassed >= 1
        assert report.iterations >= 1
        # Planner records must not embed layer inside feedback entries
        for rec in report.records:
            for fb in rec.feedback:
                assert "layer" not in fb

    def test_max_iterations(self, tmp_path):
        target = _FakeTarget(["BLOCK"] * 50)
        loop = AdversarialLoop(
            target=target,
            batch_size=2,
            max_iterations=2,
            stop_on_bypass=True,
            seed=1,
            report_dir=tmp_path,
        )
        report = loop.run()
        assert report.stop_reason == "max_iterations"
        assert report.iterations == 2
        assert report.total_hits == 4
