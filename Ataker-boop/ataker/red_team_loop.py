"""
Red Team Loop — adversarial-тренировка SecurityPipeline.

Цикл: Генерация атак → Прогон через Pipeline → Анализ →
       Выявление слабостей → Отчёт → [Обновление защиты через Gate]

Из роадмапа (Фаза 2.1–2.2):
  Атака → спарринг → провалы → изолированная база →
  дообучение (gate) → safety-обвязка → повтор.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Callable

from loguru import logger

from ataker.generator import AttackGenerator, AttackPayload, AttackCategory
from ataker.vault import AttackVault
from ataker.mutations import MutationEngine
from ataker.success_analyzer import (
    analyze_verdicts,
    DEFAULT_JUDGE_SAMPLES,
    DEFAULT_INSTABILITY_THRESHOLD,
)


@dataclass
class RedTeamResult:
    """Результат одного атакующего прогона."""
    payload: AttackPayload
    actual_verdict: str
    actual_layer: Optional[str]
    confidence: float
    latency_ms: float
    bypassed: bool
    errored: bool = False
    judge_verdicts: List[str] = field(default_factory=list)
    judge_instability_rate: float = 0.0
    quarantined: bool = False

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
    judge_instability_rate: float = 0.0
    quarantined_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"═══ RED TEAM REPORT: {self.run_id} ═══",
            f"Всего атак: {self.total_attacks}",
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

        if self.quarantined_count:
            lines.append("")
            lines.append(
                f"КАРАНТИН (нестабильный judge): {self.quarantined_count} "
                f"(avg instability {self.judge_instability_rate:.1%})"
            )

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
        judge_samples: int = 1,
        instability_threshold: float = DEFAULT_INSTABILITY_THRESHOLD,
    ):
        self._pipeline = pipeline
        self._mutation_engine = mutation_engine or MutationEngine(seed=seed)
        self._generator = generator or AttackGenerator(
            mutation_engine=self._mutation_engine, seed=seed
        )
        self._vault = vault
        self._session_id = session_id
        self._judge_samples = max(1, judge_samples)
        self._instability_threshold = instability_threshold
        self._results: List[RedTeamResult] = []

    async def run(
        self,
        categories: List[AttackCategory] | None = None,
        mutations_per_template: int = 3,
        include_chained: bool = True,
        chain_depth: int = 2,
        max_attacks: int | None = None,
        on_result: Callable[[RedTeamResult], None] | None = None,
    ) -> RedTeamReport:
        """Запустить полный цикл red team тестирования."""
        # Раньше: hashlib.md5(str(time.time())) от того же time.time() — два
        # прогона в одну секунду давали одинаковый run_id. Теперь случайный
        # токен из 6 hex-символов (через secrets — криптографически стойкий).
        run_id = f"rt-{int(time.time())}-{secrets.token_hex(3)}"
        start_time = time.time()
        self._results = []

        logger.info(f"[RED TEAM] Запуск сессии {run_id}")

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

        if max_attacks and len(payloads) > max_attacks:
            import random
            random.shuffle(payloads)
            payloads = payloads[:max_attacks]

        logger.info(f"[RED TEAM] Сгенерировано {len(payloads)} атак")

        if self._vault:
            self._vault.store_payloads(payloads, source="red_team")

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

        duration = time.time() - start_time
        report = self._build_report(run_id, duration)

        logger.info(f"[RED TEAM] Сессия завершена: {report.block_rate:.1%} block rate")

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

    async def _test_payload(self, payload: AttackPayload) -> RedTeamResult:
        """Прогнать один payload через SecurityPipeline."""
        start = time.perf_counter()
        samples = self._judge_samples

        try:
            if samples < DEFAULT_JUDGE_SAMPLES:
                ctx = await self._pipeline.process(
                    payload.mutated, self._session_id
                )
                latency = (time.perf_counter() - start) * 1000
                bypassed = ctx.verdict != "RED"
                return RedTeamResult(
                    payload=payload,
                    actual_verdict=ctx.verdict,
                    actual_layer=ctx.violation_layer,
                    confidence=ctx.confidence,
                    latency_ms=latency,
                    bypassed=bypassed,
                )

            verdicts: List[str] = []
            layers: List[Optional[str]] = []
            confidences: List[float] = []
            for _ in range(samples):
                ctx = await self._pipeline.process(
                    payload.mutated, self._session_id
                )
                verdicts.append(ctx.verdict)
                layers.append(ctx.violation_layer)
                confidences.append(ctx.confidence)

            analysis = analyze_verdicts(
                verdicts,
                instability_threshold=self._instability_threshold,
            )
            latency = (time.perf_counter() - start) * 1000
            bypassed = analysis.final_verdict != "RED"

            # layer/confidence от прогона с финальным вердиктом
            match_idx = next(
                (i for i, v in enumerate(verdicts) if v == analysis.final_verdict),
                0,
            )

            return RedTeamResult(
                payload=payload,
                actual_verdict=analysis.final_verdict,
                actual_layer=layers[match_idx],
                confidence=confidences[match_idx],
                latency_ms=latency,
                bypassed=bypassed,
                judge_verdicts=analysis.verdicts,
                judge_instability_rate=analysis.instability_rate,
                quarantined=analysis.quarantined,
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            # Инфраструктурный сбой (таймаут/сеть/краш pipeline) — это НЕ взлом.
            # Раньше считалось bypassed=True и завышало статистику обходов защиты.
            # Теперь отдельный признак errored: ни блок, ни обход.
            logger.warning(f"[RED TEAM] payload {payload.id} errored: {type(e).__name__}: {e}")
            return RedTeamResult(
                payload=payload,
                actual_verdict="ERROR",
                actual_layer=None,
                confidence=0.0,
                latency_ms=latency,
                bypassed=False,
                errored=True,
            )

    def _build_report(self, run_id: str, duration: float) -> RedTeamReport:
        """Собрать отчёт по результатам."""
        total = len(self._results)
        # Ошибки (errored) — отдельный класс: ни блок, ни обход. Раньше они
        # засчитывались как bypassed (bypassed=True) и завышали число обходов;
        # теперь bypassed=False, но мы не должны считать их блоком.
        blocked = sum(1 for r in self._results if not r.bypassed and not r.errored)
        bypassed = sum(1 for r in self._results if r.bypassed)
        # total - blocked - bypassed = количество ошибок (для прозрачности)

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
            if r.quarantined:
                weaknesses.append({
                    "payload_id": r.payload.id,
                    "category": r.payload.category.value,
                    "type": "judge_instability",
                    "judge_verdicts": r.judge_verdicts,
                    "judge_instability_rate": r.judge_instability_rate,
                    "actual_verdict": r.actual_verdict,
                    "description": (
                        f"Нестабильный guard: {r.judge_verdicts} "
                        f"(instability={r.judge_instability_rate:.2f}) → карантин."
                    ),
                })
            elif r.bypassed:
                weaknesses.append({
                    "payload_id": r.payload.id,
                    "category": r.payload.category.value,
                    "original": r.payload.original[:200],
                    "mutations": r.payload.mutations_applied,
                    "actual_verdict": r.actual_verdict,
                    "description": (
                        f"Атака категории {r.payload.category.value} обошла защиту. "
                        f"Мутации: {r.payload.mutations_applied}. "
                        f"Verdict: {r.actual_verdict} вместо RED."
                    ),
                })

        instability_rates = [r.judge_instability_rate for r in self._results if r.judge_verdicts]
        avg_instability = (
            sum(instability_rates) / len(instability_rates) if instability_rates else 0.0
        )
        quarantined_count = sum(1 for r in self._results if r.quarantined)

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
            judge_instability_rate=avg_instability,
            quarantined_count=quarantined_count,
        )

    @property
    def results(self) -> List[RedTeamResult]:
        return self._results.copy()

    @property
    def last_report(self) -> Optional[RedTeamReport]:
        if not self._results:
            return None
        return self._build_report("last", 0)
