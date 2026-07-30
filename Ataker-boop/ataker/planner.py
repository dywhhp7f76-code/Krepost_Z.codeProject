"""Planner: stub (round-robin) + точка расширения под LLM."""
from __future__ import annotations

from typing import List, Optional, Protocol, Sequence

from ataker.feedback import FeedbackEntry
from ataker.generator import ATTACK_TEMPLATES, AttackCategory
from ataker.mutations import MutationEngine
from ataker.planner_types import PlannedAttack, PlannerInput, PlannerOutput

# Приоритет «человеческих» категорий (спека В.11)
_HUMAN_FIRST: List[AttackCategory] = [
    AttackCategory.SOCIAL_ENGINEERING,
    AttackCategory.MULTI_TURN,
    AttackCategory.ROLE_HIJACK,
    AttackCategory.JAILBREAK,
    AttackCategory.DIRECT_INJECTION,
    AttackCategory.SYSTEM_PROMPT_LEAK,
    AttackCategory.ENCODING_BYPASS,
    AttackCategory.HOMOGLYPH,
]


class Planner(Protocol):
    def plan(self, inp: PlannerInput) -> PlannerOutput: ...


def _categories_with_templates() -> List[AttackCategory]:
    return [c for c in _HUMAN_FIRST if ATTACK_TEMPLATES.get(c)]


class StubPlanner:
    """Без LLM: round-robin категорий + фиксированный набор мутаций.

    Смотрит на фидбек: если категория часто BLOCK — пробуем другую +
    prefix_innocent / homoglyph. Если BYPASS — повторяем рецепт.
    """

    def __init__(
        self,
        *,
        seed: int = 0,
        default_mutations: Optional[Sequence[str]] = None,
    ):
        self._seed = seed
        self._categories = _categories_with_templates()
        self._mut_engine = MutationEngine(seed=seed)
        available = set(self._mut_engine.available_mutations)
        defaults = list(default_mutations or ("prefix_innocent", "homoglyph"))
        self._default_mutations = [m for m in defaults if m in available] or [
            self._mut_engine.available_mutations[0]
        ]
        self._rr = 0

    def plan(self, inp: PlannerInput) -> PlannerOutput:
        n = max(1, inp.batch_size)
        bypassed = [f for f in inp.feedback if f.bypassed]
        blocked_cats = {
            f.category for f in inp.feedback if f.mark == "BLOCK" and f.category
        }

        recipes: List[PlannedAttack] = []
        reasoning_bits: List[str] = []

        if bypassed:
            # Повторяем успешный рецепт
            src = bypassed[-1]
            try:
                cat = AttackCategory(src.category) if src.category else self._next_cat()
            except ValueError:
                cat = self._next_cat()
            muts = list(src.mutations) or list(self._default_mutations)
            for _ in range(n):
                recipes.append(
                    PlannedAttack(
                        template_category=cat,
                        mutations=muts,
                        chain_depth=max(1, len(muts)),
                        technique_ref=src.technique_ref,
                        reasoning="repeat bypass recipe",
                    )
                )
            reasoning_bits.append(
                f"iter={inp.iteration}: repeat bypass category={cat.value} muts={muts}"
            )
            hypothesis = f"Exploit {cat.value} further; keep mutations {muts}"
        else:
            for i in range(n):
                cat = self._pick_category(blocked_cats, i)
                muts = self._pick_mutations(cat, blocked_cats)
                recipes.append(
                    PlannedAttack(
                        template_category=cat,
                        mutations=muts,
                        chain_depth=max(1, len(muts)),
                        reasoning=f"stub rr i={i}",
                    )
                )
            reasoning_bits.append(
                f"iter={inp.iteration}: round-robin n={n} "
                f"avoid_blocked={sorted(blocked_cats)}"
            )
            hypothesis = (
                "Rotate human-first categories; add soft mutations when blocked"
            )

        return PlannerOutput(
            reasoning="; ".join(reasoning_bits),
            attack_recipes=recipes,
            hypothesis=hypothesis,
        )

    def _next_cat(self) -> AttackCategory:
        cat = self._categories[self._rr % len(self._categories)]
        self._rr += 1
        return cat

    def _pick_category(self, blocked: set, i: int) -> AttackCategory:
        # Сдвигаем rr, предпочитаем не-blocked
        for _ in range(len(self._categories)):
            cat = self._next_cat()
            if cat.value not in blocked:
                return cat
        return self._categories[i % len(self._categories)]

    def _pick_mutations(self, cat: AttackCategory, blocked: set) -> List[str]:
        if cat.value in blocked or blocked:
            # Мягкие «человеческие» обёртки
            soft = [m for m in ("prefix_innocent", "markdown_wrap", "homoglyph")
                    if m in self._mut_engine.available_mutations]
            return soft[:2] or list(self._default_mutations)
        return list(self._default_mutations)
