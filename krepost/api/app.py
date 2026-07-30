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
- необработанные исключения → generic 500 без утечки стека (паттерн SEC-004);
- операторский пароль (KREPOST_OPERATOR_PASSWORD) → Bearer-сессия для чата.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_CHAT_HTML = _STATIC_DIR / "chat.html"

from krepost.api.alerts import AlertDispatcher, format_prometheus_metrics
from krepost.api.auth import AuthGate
from krepost.api.ingest_personal import ingest_metadata, write_personal_note
from krepost.orchestration.orchestrator import Orchestrator, OrchestrationResult
from krepost.orchestration.tools import AgentResult, ToolAgent

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


API_VERSION = "0.1.0"
MAX_BODY_BYTES = 256 * 1024  # 256 KB — обычные запросы
MAX_INGEST_BYTES = 8 * 1024 * 1024  # 8 MB — личные загрузки


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=32000)
    session_id: str = Field(..., min_length=1, max_length=200)
    use_memory: bool = True


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


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=500)
    totp: str = Field(default="", max_length=16)  # позже


class LoginResponse(BaseModel):
    token: str
    expires_at: float
    auth: str = "password"


class IngestJsonRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=2_000_000)
    private: bool = True


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
    auth_gate: AuthGate | None = None,
    vault_root: Path | None = None,
) -> FastAPI:
    gate = auth_gate if auth_gate is not None else AuthGate.from_env()
    vault = Path(
        vault_root
        if vault_root is not None
        else os.environ.get("KREPOST_VAULT", "vault")
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if gate.enabled and not gate.configured:
            logger.error(
                "KREPOST_REQUIRE_AUTH=1 но KREPOST_OPERATOR_PASSWORD пуст — "
                "все защищённые маршруты вернут 503"
            )
        elif gate.enabled:
            logger.info("Operator auth ON — Bearer token required for chat/API")
        yield
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
    app.state.auth_gate = gate
    app.state.vault_root = vault

    def _metrics_snapshot() -> Dict[str, Any]:
        pipe = orchestrator.pipeline
        with pipe._metrics_lock:
            snap = dict(pipe.metrics)
            snap["red_by_layer"] = dict(snap.get("red_by_layer", {}))
            total = snap.get("total_requests", 0)
            redactions = snap.get("pii_redactions", 0) + snap.get("secret_redactions", 0)
            snap["pii_filter_healthy"] = bool(total == 0 or redactions > 0)
            snap["agent_enabled"] = agent is not None
            snap["auth_enabled"] = gate.enabled
        return snap

    def _unauthorized():
        return JSONResponse(
            status_code=401,
            content={"detail": "unauthorized", "hint": "POST /v1/login"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _auth_not_configured():
        return JSONResponse(
            status_code=503,
            content={
                "detail": "auth_not_configured",
                "hint": "Set KREPOST_OPERATOR_PASSWORD",
            },
        )

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        path = request.url.path
        method = request.method

        # Body size
        cl = request.headers.get("content-length")
        limit = MAX_INGEST_BYTES if path.startswith("/v1/ingest") else MAX_BODY_BYTES
        if cl is not None:
            try:
                if int(cl) > limit:
                    return JSONResponse(
                        status_code=413, content={"detail": "payload_too_large"}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": "bad_content_length"}
                )

        # Auth
        if gate.needs_auth(path, method):
            if not gate.configured:
                return _auth_not_configured()
            token = gate.extract_bearer(request.headers.get("authorization"))
            if not gate.valid_token(token):
                return _unauthorized()

        return await call_next(request)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.error(f"unhandled API error: {type(exc).__name__}: {exc}")
        return JSONResponse(
            status_code=500, content={"status": "error", "detail": "internal_error"}
        )

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": API_VERSION,
            "agent": agent is not None,
            "tools": (
                [t["name"] for t in agent.registry.specs()] if agent is not None else []
            ),
            "chat": "/chat",
            "auth_required": gate.enabled,
            "private_chat": "tools/KrepostChat",
        }

    @app.post("/v1/login", response_model=LoginResponse)
    async def login(req: LoginRequest):
        if not gate.configured:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "auth_not_configured",
                    "hint": "Set KREPOST_OPERATOR_PASSWORD on Studio",
                },
            )
        if not gate.verify_password(req.password, req.totp):
            return JSONResponse(status_code=401, content={"detail": "bad_credentials"})
        sess = gate.issue_token()
        return LoginResponse(token=sess.token, expires_at=sess.expires_at)

    @app.post("/v1/logout")
    async def logout(request: Request):
        token = gate.extract_bearer(request.headers.get("authorization"))
        if token:
            gate.revoke(token)
        return {"status": "ok"}

    @app.get("/")
    @app.get("/chat")
    async def chat_ui():
        """Браузерный чат (тот же origin). При auth — нужен Bearer (программа KrepostChat удобнее)."""
        if not _CHAT_HTML.is_file():
            return PlainTextResponse("chat UI missing", status_code=404)
        return FileResponse(
            _CHAT_HTML,
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

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
        result = await orchestrator.handle(
            req.text, req.session_id, use_memory=req.use_memory
        )
        return _to_response(result)

    if agent is not None:

        @app.post("/v1/agent", response_model=AgentResponse)
        async def agent_query(req: QueryRequest):
            result = await agent.run(req.text, req.session_id)
            return _agent_to_response(result)

    async def _do_ingest(filename: str, content: str, private: bool) -> JSONResponse:
        if not content.strip():
            return JSONResponse(status_code=400, content={"detail": "empty_content"})
        try:
            path, doc_id = write_personal_note(
                vault, filename, content, private=private
            )
        except Exception as e:
            logger.error(f"ingest write failed: {e}")
            return JSONResponse(status_code=500, content={"detail": "write_failed"})

        added = 0
        blocked = False
        reason = ""
        store = getattr(orchestrator, "memory_store", None)
        if store is not None:
            try:
                result = await store.add(
                    doc_id, content, metadata=ingest_metadata(private=private)
                )
                added = int(getattr(result, "added", 0) or 0)
                blocked = bool(getattr(result, "blocked", False))
                if getattr(result, "reason", None):
                    reason = str(result.reason)
            except Exception as e:
                logger.warning(f"memory ingest failed (file saved): {e}")
                reason = f"file_saved_memory_error:{type(e).__name__}"

        return JSONResponse(
            {
                "status": "ok" if not blocked else "blocked",
                "doc_id": doc_id,
                "path": str(path),
                "chunks": added,
                "blocked": blocked,
                "reason": reason,
                "private": private,
            }
        )

    @app.post("/v1/ingest")
    async def ingest_json(req: IngestJsonRequest):
        return await _do_ingest(req.filename, req.content, req.private)

    # Multipart optional (python-multipart). GUI uses JSON /v1/ingest.
    try:
        from fastapi import File, Form, UploadFile  # noqa: F811

        @app.post("/v1/ingest/upload")
        async def ingest_upload(
            file: UploadFile = File(...),
            private: bool = Form(True),
        ):
            raw = await file.read()
            if len(raw) > MAX_INGEST_BYTES:
                return JSONResponse(
                    status_code=413, content={"detail": "payload_too_large"}
                )
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                return JSONResponse(
                    status_code=400, content={"detail": "utf8_text_only"}
                )
            name = file.filename or "upload.md"
            return await _do_ingest(name, text, private)

    except Exception as e:  # pragma: no cover
        logger.warning(f"/v1/ingest/upload disabled: {e}")

    return app
