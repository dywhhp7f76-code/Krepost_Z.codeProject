"""
RELAI regression control — неизменяемое правило до любого auto-RSI.

Статус: правило СЕЙЧАС (governance). Код verifier / eval-suite —
после Ataker Useful/Correct/Safe (см. ROADMAP «RELAI-VCL»).

Запрет: ImprovementGate / любой self-improve контур НЕ имеет права
автоматически применять изменения, если регресс-набор не пройден.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Идентификатор правила — не удалять и не ослаблять без решения оператора.
RELAI_RULE_ID = "RELAI-NO-AUTO-RSI-WITHOUT-REGRESSION"

RELAI_RULE_TEXT = (
    "Автоматический RSI / self-improve запрещён, пока нет зелёного "
    "регресс-набора (Useful/Correct/Safe + критичные Probnoki). "
    "Fail-closed: нет suite → нет auto-apply."
)


@dataclass(frozen=True)
class RelaiVerdict:
    allowed: bool
    rule_id: str = RELAI_RULE_ID
    reason: str = ""


def allows_auto_rsi(
    *,
    regression_suite_passed: bool,
    suite_name: Optional[str] = None,
    operator_override: bool = False,
) -> RelaiVerdict:
    """
    Gate перед auto-apply улучшений.

    operator_override=True — только явное решение человека (не агента).
    """
    if operator_override:
        return RelaiVerdict(
            True,
            reason="operator_override — ручное одобрение оператора",
        )
    if not regression_suite_passed:
        label = suite_name or "regression_suite"
        return RelaiVerdict(
            False,
            reason=f"{label} not green — {RELAI_RULE_TEXT}",
        )
    return RelaiVerdict(
        True,
        reason=f"regression suite green ({suite_name or 'ok'})",
    )
