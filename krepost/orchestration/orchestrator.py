"""
krepost/orchestration/orchestrator.py

Оркестратор — недостающее звено между слоями безопасности и LLM.
Владеет полным жизненным циклом запроса (ARCHITECTURE_VISION §4):

    User → Security (process) → Router → LLM(backend) → Security (process_output) → User

Пайплайн отдаёт замороженный аудит-контекст из process() и принимает свежий
контекст в process_output(); оркестратор склеивает эти половины и порождает
единый результат с вердиктами входа и выхода.

Fail-closed избирательно (ARCHITECTURE_VISION §5.4):
- вход скомпрометирован → генерация НЕ запускается вообще (жёсткий fail-closed);
- выход скомпрометирован → отдаётся заблокированный/очищенный текст из Layer 4;
- отказ бэкенда (инфраструктура) → мягкая деградация: статус backend_error,
  нейтральное сообщение, это НЕ трактуется как атака.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional

from krepost.security.pipeline import SecurityContext, Verdict

if TYPE_CHECKING:
    from krepost.orchestration.router import Router
    from krepost.security.pipeline import SecurityPipeline

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


OrchestrationStatus = Literal["ok", "blocked_input", "blocked_output", "backend_error"]

DEFAULT_BLOCKED_MESSAGE = "Доступ заблокирован."
DEFAULT_ERROR_MESSAGE = "Сервис временно недоступен. Повторите запрос позже."


@dataclass
class OrchestrationResult:
    """Итог полного цикла. `status` — единственный источник истины о том,
    что произошло; `output` пригоден к показу пользователю при любом статусе."""

    session_id: str
    status: OrchestrationStatus
    verdict: Verdict
    output: str
    route: Optional[str] = None
    input_audit_hash: Optional[str] = None
    input_trace_hash: Optional[str] = None
    violation_layer: Optional[str] = None
    attack_vector: Optional[str] = None
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"


class Orchestrator:
    """Связывает SecurityPipeline + Router + бэкенды в один вызов handle()."""

    def __init__(
        self,
        pipeline: "SecurityPipeline",
        router: "Router",
        blocked_message: str = DEFAULT_BLOCKED_MESSAGE,
        error_message: str = DEFAULT_ERROR_MESSAGE,
    ):
        self.pipeline = pipeline
        self.router = router
        self.blocked_message = blocked_message
        self.error_message = error_message

    async def handle(self, text: str, session_id: str) -> OrchestrationResult:
        start = time.perf_counter()

        # ── Вход: слои 1–3 ──────────────────────────────────────────────
        in_ctx = await self.pipeline.process(text, session_id)

        if in_ctx.is_compromised:
            # Жёсткий fail-closed: генерации нет вообще.
            return OrchestrationResult(
                session_id=session_id,
                status="blocked_input",
                verdict=in_ctx.verdict,
                output=self.blocked_message,
                input_audit_hash=in_ctx.audit_hash,
                input_trace_hash=in_ctx.trace_hash,
                violation_layer=in_ctx.violation_layer,
                attack_vector=in_ctx.attack_vector,
                latency_ms=(time.perf_counter() - start) * 1000,
                metadata={"trusted": in_ctx.metadata.get("trusted", False)},
            )

        # ── Маршрутизация ───────────────────────────────────────────────
        route = self.router.select(in_ctx)

        # ── Генерация: исходный текст, не нормализованный ───────────────
        try:
            raw_output = await route.backend.generate(text, in_ctx)
        except Exception as e:
            # Инфраструктурный сбой бэкенда — мягкая деградация, не атака.
            logger.error(f"backend {route.name!r} generate failed: {type(e).__name__}: {e}")
            return OrchestrationResult(
                session_id=session_id,
                status="backend_error",
                verdict=in_ctx.verdict,
                output=self.error_message,
                route=route.name,
                input_audit_hash=in_ctx.audit_hash,
                input_trace_hash=in_ctx.trace_hash,
                latency_ms=(time.perf_counter() - start) * 1000,
                metadata={"error": type(e).__name__},
            )

        # ── Выход: Layer 4 (свежий контекст, как ожидает process_output) ─
        out_ctx = SecurityContext(session_id=session_id, user_input=text)
        out_ctx.ai_output = raw_output
        out_ctx = await self.pipeline.process_output(out_ctx)

        blocked_out = out_ctx.is_compromised
        return OrchestrationResult(
            session_id=session_id,
            status="blocked_output" if blocked_out else "ok",
            verdict=out_ctx.verdict if blocked_out else in_ctx.verdict,
            output=out_ctx.ai_output,
            route=route.name,
            input_audit_hash=in_ctx.audit_hash,
            input_trace_hash=in_ctx.trace_hash,
            violation_layer=out_ctx.violation_layer if blocked_out else None,
            attack_vector=out_ctx.attack_vector if blocked_out else None,
            latency_ms=(time.perf_counter() - start) * 1000,
            metadata={"trusted": in_ctx.metadata.get("trusted", False)},
        )
