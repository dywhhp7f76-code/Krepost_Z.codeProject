"""
krepost/api/app.py

HTTP-обвязка поверх Orchestrator — точка входа сервиса (ARCHITECTURE_VISION §4):

    HTTP POST → Orchestrator.handle (security → router → LLM → security) → JSON

`create_app(orchestrator)` — фабрика: принимает уже собранный Orchestrator
(DI, как и весь проект), поэтому тестируется с мок-бэкендами и запускается с
реальными, когда они появятся.

Безопасность самого API (серверная роль):
- bind на localhost делается в server.py (принцип локальности §5.1);
- лимит размера тела (413) + max_length на поля (422) — против раздувания;
- rate limiting уже в пайплайне (SessionRateLimiter);
- необработанные исключения → generic 500 без утечки стека (паттерн SEC-004).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from krepost.api.alerts import AlertDispatcher, format_prometheus_metrics
from krepost.orchestration.orchestrator import Orchestrator, OrchestrationResult
from krepost.orchestration.tools import AgentResult, ToolAgent

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


API_VERSION = "0.1.0"
MAX_BODY_BYTES = 256 * 1024  # 256 KB — тело запроса; текст отдельно ограничен полем


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=32000)
    session_id: str = Field(..., min_length=1, max_length=200)


class QueryResponse(BaseModel):
    status: str
    verdict: str
    output: str
    session_id: str
    route: Optional[str] = None
    latency_ms: float = 0.0
    audit_hash: Optional[str] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    status: str
    verdict: str
    output: str
    session_id: str
    iterations: int = 0
    audit_hash: Optional[str] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


def _to_response(r: OrchestrationResult) -> QueryResponse:
    return QueryResponse(
        status=r.status,
        verdict=r.verdict,
        output=r.output,
        session_id=r.session_id,
        route=r.route,
        latency_ms=round(r.latency_ms, 2),
        audit_hash=r.input_audit_hash,
        diagnostics={
            "violation_layer": r.violation_layer,
            "attack_vector": r.attack_vector,
            "trace_hash": r.input_trace_hash,
            **r.metadata,
        },
    )


def _agent_to_response(r: AgentResult) -> AgentResponse:
    return AgentResponse(
        status=r.status,
        verdict=r.verdict,
        output=r.output,
        session_id=r.session_id,
        iterations=r.iterations,
        audit_hash=r.input_audit_hash,
        diagnostics={
            "violation_layer": r.violation_layer,
            "tool_trace": [
                {"tool": t.tool, "status": t.status, "reason": t.reason}
                for t in r.tool_trace
            ],
        },
    )


def create_app(
    orchestrator: Orchestrator,
    *,
    agent: ToolAgent | None = None,
    title: str = "Krepost API",
    alert_dispatcher: AlertDispatcher | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        # Корректное закрытие пайплайна при остановке сервиса.
        try:
            await orchestrator.pipeline.close()
        except Exception as e:  # pragma: no cover
            logger.error(f"pipeline close on shutdown failed: {e}")
        if agent is not None and agent.pipeline is not orchestrator.pipeline:
            try:
                await agent.pipeline.close()
            except Exception as e:  # pragma: no cover
                logger.error(f"agent pipeline close on shutdown failed: {e}")

    app = FastAPI(title=title, version=API_VERSION, lifespan=lifespan)
    alerts = alert_dispatcher or AlertDispatcher()

    def _metrics_snapshot() -> Dict[str, Any]:
        pipe = orchestrator.pipeline
        with pipe._metrics_lock:
            snap = dict(pipe.metrics)
            snap["red_by_layer"] = dict(snap.get("red_by_layer", {}))
            total = snap.get("total_requests", 0)
            redactions = snap.get("pii_redactions", 0) + snap.get("secret_redactions", 0)
            snap["pii_filter_healthy"] = bool(total == 0 or redactions > 0)
            snap["agent_enabled"] = agent is not None
        return snap

    @app.middleware("http")
    async def limit_body(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "payload_too_large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "bad_content_length"})
        return await call_next(request)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        # Не отдаём стек/детали наружу — только generic-ошибка.
        logger.error(f"unhandled API error: {type(exc).__name__}: {exc}")
        return JSONResponse(status_code=500, content={"status": "error", "detail": "internal_error"})

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": API_VERSION,
            "agent": agent is not None,
            "tools": (
                [t["name"] for t in agent.registry.specs()] if agent is not None else []
            ),
        }

    @app.get("/metrics")
    async def metrics():
        snap = _metrics_snapshot()
        alerts.maybe_alert_pii_unhealthy(snap)
        return snap

    @app.get("/metrics/prometheus")
    async def metrics_prometheus():
        snap = _metrics_snapshot()
        alerts.maybe_alert_pii_unhealthy(snap)
        return PlainTextResponse(format_prometheus_metrics(snap))

    @app.post("/v1/query", response_model=QueryResponse)
    async def query(req: QueryRequest):
        result = await orchestrator.handle(req.text, req.session_id)
        return _to_response(result)

    if agent is not None:
        @app.post("/v1/agent", response_model=AgentResponse)
        async def agent_query(req: QueryRequest):
            result = await agent.run(req.text, req.session_id)
            return _agent_to_response(result)

    return app
