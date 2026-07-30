"""
Red Team Loop — adversarial-тренировка SecurityPipeline.

Цикл: Генерация атак → Прогон через Pipeline → Анализ →
       Выявление слабостей → Отчёт → [Обновление защиты через Gate]

Из роадмапа (Фаза 2.1–2.2):
  Атака → спарринг → провалы → изолированная база →
  дообучение (gate) → safety-обвязка → повтор.

Risk 2: hard-cap + cooldown между атаками/запусками.
Risk 3: success по содержимому ответа Main (process→generate→process_output).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Awaitable, Literal

from loguru import logger

from ataker.generator import AttackGenerator, AttackPayload, AttackCategory
from ataker.vault import AttackVault
from ataker.mutations import MutationEngine
from ataker.success import ContentSuccessAnalyzer, ContentSuccess

SuccessMode = Literal["verdict", "content", "both"]

# Адекватный потолок для фаззера (100 из аудита — слишком мал)
DEFAULT_HARD_CAP = 1000
# Cooldown выключен по умолчанию; для continuous-режима на Air ставь 30+.
DEFAULT_COOLDOWN_SEC = 0.0
DEFAULT_ATTACK_DELAY_SEC = 0.0


class CooldownError(RuntimeError):
    """Повторный run() раньше истечения cooldown."""


@dataclass
class RedTeamResult:
    """Результат одного атакующего прогона."""
    payload: AttackPayload
    actual_verdict: str
    actual_layer: Optional[str]
    confidence: float
    latency_ms: float
    bypassed: bool
    input_verdict: Optional[str] = None
    output_verdict: Optional[str] = None
    model_output: Optional[str] = None
    content_success: Optional[ContentSuccess] = None
    success_mode: str = "verdict"

    @property
    def success(self) -> bool:
        return self.bypassed


@dataclass
class RedTeamReport:
    """Отчёт о red team сессии."""
    run_id: str
    total_attacks: int
    blocked: int
    bypassed: int
    block_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    by_category: Dict[str, Dict[str, int]]
    by_layer: Dict[str, int]
    by_mutation: Dict[str, Dict[str, int]]
    weaknesses: List[Dict[str, Any]]
    duration_sec: float
    success_mode: str = "verdict"
    hard_cap: int = DEFAULT_HARD_CAP
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        # ContentSuccess → plain dict already via asdict if dataclass
        return d

    def summary(self) -> str:
        lines = [
            f"═══ RED TEAM REPORT: {self.run_id} ═══",
            f"Режим успеха: {self.success_mode}",
            f"Всего атак: {self.total_attacks} (hard_cap={self.hard_cap})",
            f"Заблокировано: {self.blocked} ({self.block_rate:.1%})",
            f"Обошли защиту: {self.bypassed}",
            f"Средняя latency: {self.avg_latency_ms:.1f}ms",
            f"P95 latency: {self.p95_latency_ms:.1f}ms",
            f"Длительность: {self.duration_sec:.1f}s",
            "",
            "По категориям:",
        ]
        for cat, stats in sorted(self.by_category.items()):
            total = stats.get("total", 0)
            bypassed = stats.get("bypassed", 0)
            rate = (total - bypassed) / total if total > 0 else 1.0
            marker = "⚠️" if bypassed > 0 else "✓"
            lines.append(f"  {marker} {cat}: {total - bypassed}/{total} blocked ({rate:.0%})")

        if self.weaknesses:
            lines.append("")
            lines.append(f"СЛАБОСТИ ОБНАРУЖЕНЫ: {len(self.weaknesses)}")
            for w in self.weaknesses[:10]:
                lines.append(f"  - [{w.get('category')}] {w.get('description', '')[:100]}")

        return "\n".join(lines)


class RedTeamLoop:
    """
    Основной цикл adversarial-тестирования.

    Использование:
        loop = RedTeamLoop(pipeline=security_pipeline)
        report = await loop.run()
        print(report.summary())
    """

    def __init__(
        self,
        pipeline,
        vault: AttackVault | None = None,
        generator: AttackGenerator | None = None,
        mutation_engine: MutationEngine | None = None,
        session_id: str = "red-team",
        seed: int | None = None,
        *,
        hard_cap: int = DEFAULT_HARD_CAP,
        cooldown_sec: float = DEFAULT_COOLDOWN_SEC,
        attack_delay_sec: float = DEFAULT_ATTACK_DELAY_SEC,
        success_mode: SuccessMode = "verdict",
        main_generate: Callable[[str], Awaitable[str]] | Callable[[str], str] | None = None,
        success_analyzer: ContentSuccessAnalyzer | None = None,
        cooldown_state_path: str | Path | None = None,
    ):
        self._pipeline = pipeline
        self._mutation_engine = mutation_engine or MutationEngine(seed=seed)
        self._generator = generator or AttackGenerator(
            mutation_engine=self._mutation_engine, seed=seed
        )
        self._vault = vault
        self._session_id = session_id
        self._results: List[RedTeamResult] = []

        self._hard_cap = max(1, int(hard_cap))
        self._cooldown_sec = max(0.0, float(cooldown_sec))
        self._attack_delay_sec = max(0.0, float(attack_delay_sec))
        self._success_mode: SuccessMode = success_mode
        self._main_generate = main_generate
        self._success_analyzer = success_analyzer or ContentSuccessAnalyzer()
        self._cooldown_state_path = (
            Path(cooldown_state_path)
            if cooldown_state_path
            else Path("vault_data/.red_team_cooldown.json")
        )
        self._last_run_ended_at: float | None = None

    async def run(
        self,
        categories: List[AttackCategory] | None = None,
        mutations_per_template: int = 3,
        include_chained: bool = True,
        chain_depth: int = 2,
        max_attacks: int | None = None,
        on_result: Callable[[RedTeamResult], None] | None = None,
        *,
        enforce_cooldown: bool = True,
    ) -> RedTeamReport:
        """Запустить полный цикл red team тестирования."""
        self._check_cooldown(enforce_cooldown)

        run_id = f"rt-{int(time.time())}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        start_time = time.time()
        self._results = []

        logger.info(
            f"[RED TEAM] Запуск сессии {run_id} "
            f"(mode={self._success_mode}, hard_cap={self._hard_cap})"
        )

        payloads = self._generator.generate_from_templates(
            categories=categories,
            mutations_per_template=mutations_per_template,
        )

        if include_chained:
            chained = self._generator.generate_chained(
                categories=categories,
                chain_depth=chain_depth,
                count_per_category=3,
            )
            payloads.extend(chained)

        payloads = self._apply_caps(payloads, max_attacks)
        logger.info(f"[RED TEAM] Сгенерировано {len(payloads)} атак")

        if self._vault:
            self._vault.store_payloads(payloads, source="red_team")

        report = await self._execute(payloads, run_id, start_time, on_result)
        self._mark_run_finished()
        return report

    async def run_from_vault(
        self,
        *,
        categories: List[AttackCategory | str] | None = None,
        max_attacks: int | None = None,
        on_result: Callable[[RedTeamResult], None] | None = None,
        enforce_cooldown: bool = True,
        source_filter: str | None = None,
    ) -> RedTeamReport:
        """Прогнать payload'ы из Attack Vault (база Атакера / архив)."""
        if not self._vault:
            raise RuntimeError("vault required for run_from_vault")

        self._check_cooldown(enforce_cooldown)
        run_id = f"rt-vault-{int(time.time())}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        start_time = time.time()
        self._results = []

        rows = self._vault.get_all_payloads()
        if source_filter:
            rows = [r for r in rows if r.get("source") == source_filter]
        if categories:
            cat_vals = {
                c.value if isinstance(c, AttackCategory) else str(c) for c in categories
            }
            rows = [r for r in rows if r.get("category") in cat_vals]

        payloads: List[AttackPayload] = []
        for r in rows:
            try:
                cat = AttackCategory(r["category"])
            except ValueError:
                cat = AttackCategory.JAILBREAK
            meta = r.get("metadata") or "{}"
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except json.JSONDecodeError:
                    meta = {"raw_metadata": meta}
            mutations = r.get("mutations_applied") or "[]"
            if isinstance(mutations, str):
                try:
                    mutations = json.loads(mutations)
                except json.JSONDecodeError:
                    mutations = []
            payloads.append(
                AttackPayload(
                    id=r["id"],
                    category=cat,
                    original=r.get("original") or "",
                    mutated=r.get("mutated") or r.get("original") or "",
                    mutations_applied=list(mutations),
                    expected_verdict=r.get("expected_verdict") or "RED",
                    expected_layer=r.get("expected_layer"),
                    metadata=meta if isinstance(meta, dict) else {},
                    created_at=float(r.get("created_at") or time.time()),
                )
            )

        payloads = self._apply_caps(payloads, max_attacks)
        logger.info(f"[RED TEAM] Из vault: {len(payloads)} атак (run={run_id})")
        report = await self._execute(payloads, run_id, start_time, on_result)
        self._mark_run_finished()
        return report

    async def run_single(self, text: str) -> RedTeamResult:
        """Прогнать один payload через pipeline."""
        payload = AttackPayload(
            id=f"single-{int(time.time())}",
            category=AttackCategory.DIRECT_INJECTION,
            original=text,
            mutated=text,
            mutations_applied=[],
        )
        return await self._test_payload(payload)

    def _apply_caps(
        self, payloads: List[AttackPayload], max_attacks: int | None
    ) -> List[AttackPayload]:
        limit = self._hard_cap
        if max_attacks is not None:
            limit = min(limit, max(0, int(max_attacks)))
        if len(payloads) > limit:
            import random

            random.shuffle(payloads)
            payloads = payloads[:limit]
            logger.info(f"[RED TEAM] Обрезано hard_cap/max_attacks → {limit}")
        return payloads

    def _check_cooldown(self, enforce: bool) -> None:
        if not enforce or self._cooldown_sec <= 0:
            return
        last = self._last_run_ended_at
        if last is None and self._cooldown_state_path.exists():
            try:
                data = json.loads(self._cooldown_state_path.read_text(encoding="utf-8"))
                last = float(data.get("last_run_ended_at") or 0)
            except (OSError, ValueError, json.JSONDecodeError):
                last = None
        if last is None:
            return
        elapsed = time.time() - last
        if elapsed < self._cooldown_sec:
            remaining = self._cooldown_sec - elapsed
            raise CooldownError(
                f"cooldown active: wait {remaining:.1f}s "
                f"(cooldown_sec={self._cooldown_sec})"
            )

    def _mark_run_finished(self) -> None:
        self._last_run_ended_at = time.time()
        try:
            self._cooldown_state_path.parent.mkdir(parents=True, exist_ok=True)
            self._cooldown_state_path.write_text(
                json.dumps({"last_run_ended_at": self._last_run_ended_at}),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning(f"[RED TEAM] Не удалось записать cooldown state: {e}")

    async def _execute(
        self,
        payloads: List[AttackPayload],
        run_id: str,
        start_time: float,
        on_result: Callable[[RedTeamResult], None] | None,
    ) -> RedTeamReport:
        for i, payload in enumerate(payloads):
            result = await self._test_payload(payload)
            self._results.append(result)

            if self._vault:
                self._vault.store_result(
                    payload_id=payload.id,
                    actual_verdict=result.actual_verdict,
                    actual_layer=result.actual_layer,
                    confidence=result.confidence,
                    latency_ms=result.latency_ms,
                    bypassed=result.bypassed,
                    run_id=run_id,
                )

            if on_result:
                on_result(result)

            if (i + 1) % 50 == 0:
                bypassed_so_far = sum(1 for r in self._results if r.bypassed)
                logger.info(
                    f"[RED TEAM] Прогресс: {i + 1}/{len(payloads)} "
                    f"(bypassed: {bypassed_so_far})"
                )

            if self._attack_delay_sec > 0 and i + 1 < len(payloads):
                await asyncio.sleep(self._attack_delay_sec)

        duration = time.time() - start_time
        report = self._build_report(run_id, duration)
        logger.info(f"[RED TEAM] Сессия завершена: {report.block_rate:.1%} block rate")
        return report

    async def _test_payload(self, payload: AttackPayload) -> RedTeamResult:
        """Прогнать один payload: verdict и/или полный цикл + content."""
        start = time.perf_counter()

        try:
            ctx = await self._pipeline.process(payload.mutated, self._session_id)
            input_verdict = getattr(ctx, "verdict", "ERROR")
            layer = getattr(ctx, "violation_layer", None)
            confidence = float(getattr(ctx, "confidence", 0.0) or 0.0)

            model_output: Optional[str] = None
            output_verdict: Optional[str] = None
            content: Optional[ContentSuccess] = None
            bypassed: bool

            need_content = self._success_mode in ("content", "both")
            input_bypass = input_verdict != "RED"

            if need_content and input_bypass and self._main_generate is not None:
                # Полный цикл: generate → process_output → content judge
                raw = self._main_generate(payload.mutated)
                if asyncio.iscoroutine(raw):
                    raw = await raw
                model_output = str(raw)
                if hasattr(ctx, "ai_output"):
                    ctx.ai_output = model_output
                if hasattr(self._pipeline, "process_output"):
                    ctx = await self._pipeline.process_output(ctx)
                    output_verdict = getattr(ctx, "verdict", None)
                    model_output = getattr(ctx, "ai_output", model_output) or model_output
                content = self._success_analyzer.analyze(payload.mutated, model_output or "")
                content_bypass = content.attack_succeeded and (
                    output_verdict is None or output_verdict != "RED"
                )
                if self._success_mode == "content":
                    bypassed = content_bypass
                else:  # both — успех только если вход пропустили И контент вредный
                    bypassed = input_bypass and content_bypass
            elif need_content and not input_bypass:
                bypassed = False
                content = ContentSuccess(
                    complied=False, refused=True, score=0.0, reason="blocked_on_input"
                )
            elif need_content and self._main_generate is None:
                # Нет Main — деградируем к verdict с пометкой
                bypassed = input_bypass
                content = ContentSuccess(
                    complied=False,
                    refused=False,
                    score=0.0,
                    reason="no_main_generate_fallback_verdict",
                )
                logger.warning(
                    "[RED TEAM] success_mode=%s but main_generate is None — "
                    "fallback to verdict-only",
                    self._success_mode,
                )
            else:
                bypassed = input_bypass

            latency = (time.perf_counter() - start) * 1000
            return RedTeamResult(
                payload=payload,
                actual_verdict=output_verdict or input_verdict,
                actual_layer=layer,
                confidence=confidence,
                latency_ms=latency,
                bypassed=bypassed,
                input_verdict=input_verdict,
                output_verdict=output_verdict,
                model_output=model_output,
                content_success=content,
                success_mode=self._success_mode,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning(f"[RED TEAM] payload error: {e}")
            return RedTeamResult(
                payload=payload,
                actual_verdict="ERROR",
                actual_layer=None,
                confidence=0.0,
                latency_ms=latency,
                bypassed=True,
                success_mode=self._success_mode,
            )

    def _build_report(self, run_id: str, duration: float) -> RedTeamReport:
        """Собрать отчёт по результатам."""
        total = len(self._results)
        blocked = sum(1 for r in self._results if not r.bypassed)
        bypassed = total - blocked

        latencies = [r.latency_ms for r in self._results]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0

        by_category: Dict[str, Dict[str, int]] = {}
        for r in self._results:
            cat = r.payload.category.value
            if cat not in by_category:
                by_category[cat] = {"total": 0, "blocked": 0, "bypassed": 0}
            by_category[cat]["total"] += 1
            if r.bypassed:
                by_category[cat]["bypassed"] += 1
            else:
                by_category[cat]["blocked"] += 1

        by_layer: Dict[str, int] = {}
        for r in self._results:
            if not r.bypassed and r.actual_layer:
                by_layer[r.actual_layer] = by_layer.get(r.actual_layer, 0) + 1

        by_mutation: Dict[str, Dict[str, int]] = {}
        for r in self._results:
            for m in r.payload.mutations_applied:
                if m not in by_mutation:
                    by_mutation[m] = {"total": 0, "blocked": 0, "bypassed": 0}
                by_mutation[m]["total"] += 1
                if r.bypassed:
                    by_mutation[m]["bypassed"] += 1
                else:
                    by_mutation[m]["blocked"] += 1

        weaknesses = []
        for r in self._results:
            if r.bypassed:
                desc = (
                    f"Атака категории {r.payload.category.value} обошла защиту. "
                    f"Мутации: {r.payload.mutations_applied}. "
                    f"Verdict: {r.actual_verdict} вместо RED."
                )
                if r.content_success is not None:
                    desc += (
                        f" Content: succeeded={r.content_success.attack_succeeded} "
                        f"({r.content_success.reason})."
                    )
                weaknesses.append({
                    "payload_id": r.payload.id,
                    "category": r.payload.category.value,
                    "original": r.payload.original[:200],
                    "mutations": r.payload.mutations_applied,
                    "actual_verdict": r.actual_verdict,
                    "success_mode": r.success_mode,
                    "description": desc,
                })

        return RedTeamReport(
            run_id=run_id,
            total_attacks=total,
            blocked=blocked,
            bypassed=bypassed,
            block_rate=blocked / total if total > 0 else 0,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            by_category=by_category,
            by_layer=by_layer,
            by_mutation=by_mutation,
            weaknesses=weaknesses,
            duration_sec=duration,
            success_mode=self._success_mode,
            hard_cap=self._hard_cap,
        )

    @property
    def results(self) -> List[RedTeamResult]:
        return self._results.copy()

    @property
    def last_report(self) -> Optional[RedTeamReport]:
        if not self._results:
            return None
        return self._build_report("last", 0)
