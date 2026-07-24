"""Типы Planner ↔ Executor (рецепты, не текст payload'ов)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from ataker.feedback import FeedbackEntry
from ataker.generator import AttackCategory


@dataclass
class PlannedAttack:
    """Рецепт сборки из арсенала (не готовый текст атаки)."""

    template_category: AttackCategory
    mutations: List[str] = field(default_factory=list)
    template_index: Optional[int] = None
    chain_depth: int = 1
    expected_layer: Optional[str] = None  # гипотеза оператора; не обязательна
    technique_ref: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["template_category"] = self.template_category.value
        return d


@dataclass
class PlannerOutput:
    reasoning: str
    attack_recipes: List[PlannedAttack]
    hypothesis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reasoning": self.reasoning,
            "hypothesis": self.hypothesis,
            "attack_recipes": [r.to_dict() for r in self.attack_recipes],
        }


@dataclass
class PlannerInput:
    """Вход Творца: только black-box фидбек + опциональный RAG-контекст."""

    iteration: int
    feedback: List[FeedbackEntry]
    batch_size: int = 20
    knowledge_snippets: List[str] = field(default_factory=list)

    def planner_view(self) -> Dict[str, Any]:
        """Сериализация без утечек layer/answer."""
        return {
            "iteration": self.iteration,
            "batch_size": self.batch_size,
            "feedback": [f.to_dict() for f in self.feedback],
            "knowledge_snippets": list(self.knowledge_snippets),
        }
