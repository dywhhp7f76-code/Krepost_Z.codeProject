#!/usr/bin/env python3
"""
Черновик TaskContract — исполняемая схема контракта dev-задачи.

Статус: ЧЕРНОВИК в Probnoki/. Не импортируется основным кодом Крепости,
не трогает Layer 1-4. Это инструмент dev-процесса (builder → 4 аудитора),
а не рантайм-компонент.

Запуск как демо:
    python Probnoki/task_contract_draft.py

Что демонстрирует:
- схему TaskContract (dataclasses),
- разнородных аудиторов A/B/C/D (механизм, а не 4 копии LLM),
- gate: задача принята ТОЛЬКО если все 4 passed И пробник зелёный,
- возврат билдеру всегда с evidence (конкретный вывод инструмента).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
import fnmatch


# ─────────────────────────────────────────────────────────────────────────
# Схема
# ─────────────────────────────────────────────────────────────────────────

class Auditor(str, Enum):
    DETERMINISM = "A"   # запуск пробника, сверка хешей/выводов   (не LLM)
    STRUCTURE   = "B"   # AST + import-graph + grep: dead code    (не LLM)
    CONTRACT    = "C"   # валидация вывода builder против схемы    (не LLM)
    LOGIC       = "D"   # узкий чек-лист fail-closed/логики        (LLM)


@dataclass
class ScopeGuard:
    """Периметр правок. Прямая связка с правилом 'ничего не менять без согласия'."""
    allow: list[str] = field(default_factory=list)   # glob'ы, что можно
    forbid: list[str] = field(default_factory=list)  # glob'ы, что нельзя

    def violated_by(self, files_changed: list[str]) -> list[str]:
        """Возвращает файлы, нарушившие периметр (пусто = ок)."""
        bad = []
        for f in files_changed:
            if any(fnmatch.fnmatch(f, pat) for pat in self.forbid):
                bad.append(f)
                continue
            if self.allow and not any(fnmatch.fnmatch(f, pat) for pat in self.allow):
                bad.append(f)
        return bad


@dataclass
class Acceptance:
    """VERIMAP: пробник (код) + критерий (естественный язык). Пишется ДО builder.

    mechanical_check — ТОЧНАЯ команда, которая должна вернуть exit 0. Пишется
    оператором ДО работы. Builder обязан скопировать её в Deliverable БЕЗ
    изменений: если строки расходятся — builder подогнал проверку под свой код
    (красный флаг, источник hash-divergence в CI).
    """
    probnik_path: str          # путь к исполняемому тесту-приёмке
    criterion_nl: str          # словесный критерий для аудитора D
    mechanical_check: str      # точная команда, exit 0 = ok (напр. "pytest tests/ -q")
    # Инъекция запуска пробника (в реале — subprocess pytest). Для демо — колбэк.
    run_probnik: Optional[Callable[[], bool]] = None

    def is_green(self) -> bool:
        return bool(self.run_probnik and self.run_probnik())


@dataclass
class Deliverable:
    """Что builder ОБЯЗАН вернуть, чтобы задачу вообще можно было проверять.

    unchecked_example — ОДИН честный пример, который builder НЕ проверял.
    Пустая строка тут = ложь, а не аккуратность: механически ломает
    overconfidence («всё учтено»). Нельзя сдать задачу, заявив полное покрытие.
    """
    files_changed: list[str]
    api_unchanged: bool
    summary: str
    check_command: str              # копия Acceptance.mechanical_check, БЕЗ изменений
    edge_cases: list[str]           # что builder рассмотрел (список, не «всё учтено»)
    unchecked_example: str          # один честный НЕпроверенный пример; пусто = ложь

    def is_complete(self) -> bool:
        return (
            bool(self.files_changed)
            and bool(self.summary.strip())
            and bool(self.edge_cases)
        )


@dataclass
class AuditVerdict:
    auditor: Auditor
    mechanism: str          # чем именно проверял
    passed: bool
    evidence: str           # вывод grep/теста/diff — НЕ «мне кажется»


@dataclass
class TaskContract:
    id: str
    goal: str
    scope: ScopeGuard
    acceptance: Acceptance
    deliverable: Optional[Deliverable] = None      # заполняет builder
    audit: list[AuditVerdict] = field(default_factory=list)

    # ── Gate ────────────────────────────────────────────────────────────
    def accepted(self) -> tuple[bool, list[str]]:
        """Задача принята ТОЛЬКО если всё сошлось. Возвращает (ok, причины_отказа)."""
        reasons: list[str] = []

        if self.deliverable is None:
            return False, ["builder не сдал deliverable"]

        if not self.deliverable.is_complete():
            reasons.append("deliverable неполный (нет files_changed / summary / edge_cases)")

        # Честность: пустой unchecked_example = ложь, а не полное покрытие.
        if not self.deliverable.unchecked_example.strip():
            reasons.append("unchecked_example пуст — заявлено полное покрытие (ложь)")

        # Builder не имеет права менять команду проверки под свой код.
        if self.deliverable.check_command.strip() != self.acceptance.mechanical_check.strip():
            reasons.append(
                "check_command != mechanical_check — builder подогнал проверку "
                f"(ждали: {self.acceptance.mechanical_check!r})"
            )

        bad_files = self.scope.violated_by(self.deliverable.files_changed)
        if bad_files:
            reasons.append(f"нарушение периметра scope: {bad_files}")

        # Жёсткий инвариант: пробник красный → VERIFIED невозможен, что бы ни
        # писал builder в summary. Fail-closed на уровне dev-процесса.
        if not self.acceptance.is_green():
            reasons.append(f"mechanical_check FAIL (пробник красный): {self.acceptance.probnik_path}")

        seen = {v.auditor for v in self.audit}
        missing = [a.value for a in Auditor if a not in seen]
        if missing:
            reasons.append(f"нет вердикта от аудиторов: {missing}")

        for v in self.audit:
            if not v.passed:
                reasons.append(f"аудитор {v.auditor.value} завернул: {v.evidence}")

        return (len(reasons) == 0), reasons


# ─────────────────────────────────────────────────────────────────────────
# Демо: как это работает на реальном примере
# ─────────────────────────────────────────────────────────────────────────

def _demo() -> None:
    # 1. Оператор пишет контракт ДО builder. Пробник ещё красный.
    contract = TaskContract(
        id="T-042",
        goal="normalize.py: добавить ASCII fast-path, не сломав leetspeak-маппинг",
        scope=ScopeGuard(
            allow=["krepost/security/normalize.py", "Probnoki/**"],
            forbid=["krepost/security/pipeline.py"],   # этот файл трогать нельзя
        ),
        acceptance=Acceptance(
            probnik_path="Probnoki/test_19_normalize_additions.py",
            criterion_nl=(
                "ASCII-вход проходит быстрый путь, но casefold и confusables "
                "(0→o,1→i,5→s,|→i) всё ещё применяются; публичный API (str) не меняется."
            ),
            mechanical_check="pytest Probnoki/test_19_normalize_additions.py -q",
            run_probnik=lambda: True,   # в реале: subprocess pytest -> exit 0
        ),
    )

    # 2. builder заполняет deliverable — включая честный НЕпроверенный пример
    #    и КОПИЮ команды проверки без изменений
    contract.deliverable = Deliverable(
        files_changed=["krepost/security/normalize.py",
                       "Probnoki/test_19_normalize_additions.py"],
        api_unchanged=True,
        summary="Добавлен isascii() fast-path + MAX_NORMALIZE_LENGTH guard.",
        check_command="pytest Probnoki/test_19_normalize_additions.py -q",  # == mechanical_check
        edge_cases=["пустая строка", "чистый ASCII", "смешанный кириллица+латиница",
                    "вход на границе MAX_NORMALIZE_LENGTH"],
        unchecked_example="вход ровно 200_001 символ в canonicalize_for_hash — "
                          "проверял только normalize_for_scanning на этой границе",
    )

    # 3-6. Четыре РАЗНОРОДНЫХ аудитора. Три из четырёх — не LLM.
    contract.audit = [
        AuditVerdict(Auditor.DETERMINISM, "pytest Probnoki/test_19 -q",
                     passed=True, evidence="14 passed in 0.12s"),
        AuditVerdict(Auditor.STRUCTURE, "grep full-width entries + AST unreachable",
                     passed=True, evidence="0 dead entries; full-width убран (NFKC покрывает)"),
        AuditVerdict(Auditor.CONTRACT, "проверка сигнатуры возврата == str",
                     passed=True, evidence="both funcs return str; api_unchanged=True подтверждён"),
        AuditVerdict(Auditor.LOGIC, "чек-лист: leetspeak сохранён? soft=True ветка? длина?",
                     passed=True, evidence="0/1/5/| маппинг проверен для ASCII-пути"),
    ]

    ok, reasons = contract.accepted()
    print(f"[{contract.id}] accepted = {ok}")
    for r in reasons:
        print(f"   ✗ {r}")

    # Контрпример 1: builder тронул запрещённый файл + один аудитор завернул
    contract.deliverable.files_changed.append("krepost/security/pipeline.py")
    contract.audit[1] = AuditVerdict(
        Auditor.STRUCTURE, "grep", passed=False,
        evidence="дубликат _HOMOGLYPH_MAP в src/krepost/ — рассинхрон")
    ok, reasons = contract.accepted()
    print(f"\n[{contract.id}] (после регресса) accepted = {ok}")
    for r in reasons:
        print(f"   ✗ {r}")

    # Контрпример 2: builder «всё учёл» (пусто) и подогнал команду проверки
    contract2 = TaskContract(
        id="T-043", goal="демо честности",
        scope=ScopeGuard(allow=["Probnoki/**"]),
        acceptance=Acceptance(
            probnik_path="Probnoki/test_x.py",
            criterion_nl="…", mechanical_check="pytest tests/ -q",
            run_probnik=lambda: True),
        deliverable=Deliverable(
            files_changed=["Probnoki/test_x.py"], api_unchanged=True,
            summary="готово",
            check_command="pytest tests/test_x.py -k happy_path -q",  # ПОДОГНАЛ
            edge_cases=["happy path"],
            unchecked_example=""),                                    # «всё учтено» = ложь
        audit=[AuditVerdict(a, "ok", True, "ok") for a in Auditor],
    )
    ok, reasons = contract2.accepted()
    print(f"\n[{contract2.id}] (нечестная сдача) accepted = {ok}")
    for r in reasons:
        print(f"   ✗ {r}")


if __name__ == "__main__":
    _demo()
