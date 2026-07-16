"""
krepost/orchestration/tools.py

Агентный tool-loop с врезкой guard'ов — закрывает промежуточный слой
безопасности (ARCHITECTURE_VISION §4, «verify tool outputs»).

Цикл:
    вход (Layer 1-3) → [ модель ⇄ инструмент ]* → выход (Layer 4)

На каждом обороте:
- модель либо даёт финальный ответ, либо запрашивает инструмент;
- URL-инструменты гейтятся UrlGuard ДО fetch (SSRF);
- результат ЛЮБОГО инструмента сканируется ToolOutputGuard ДО возврата в
  модель: blocked → в модель уходит безопасная заглушка (не инъекция),
  sanitized → уходит очищенный текст.

Так данные от инструмента/MCP не могут стать командами для модели.
Простой одноходовый путь остаётся в Orchestrator.handle(); это — агентный
режим для бэкендов, умеющих запрашивать инструменты.
"""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import (Any, Awaitable, Callable, Dict, List, Literal, Optional,
                    Protocol, Sequence, Union, runtime_checkable)

from krepost.security.pipeline import SecurityContext, SecurityPipeline, Verdict
from krepost.security.tool_guard import ToolOutputGuard
from krepost.security.url_guard import UrlGuard

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


# ─────────────────────────────────────────────────────────────────────────
# Шаги бэкенда: либо финальный ответ, либо запрос инструмента
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class ToolCall:
    name: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FinalAnswer:
    text: str


BackendStep = Union[ToolCall, FinalAnswer]


@runtime_checkable
class ToolCallingBackend(Protocol):
    """Бэкенд, умеющий вести многоходовый диалог с инструментами.
    `step` получает историю сообщений и спецификации инструментов и решает:
    вызвать инструмент (ToolCall) или ответить (FinalAnswer)."""

    name: str

    async def step(self, messages: List[Dict[str, Any]],
                   tools: List[Dict[str, Any]]) -> BackendStep: ...


# ─────────────────────────────────────────────────────────────────────────
# Инструменты
# ─────────────────────────────────────────────────────────────────────────

ToolFn = Callable[[Dict[str, Any]], Union[str, Awaitable[str]]]


@dataclass
class Tool:
    name: str
    fn: ToolFn
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=lambda: {
        "type": "object", "properties": {},
    })

    async def run(self, args: Dict[str, Any]) -> str:
        if inspect.iscoroutinefunction(self.fn) or inspect.iscoroutinefunction(
            getattr(self.fn, "__call__", None)
        ):
            result = await self.fn(args)
        else:
            result = await asyncio.to_thread(self.fn, args)
        return result if isinstance(result, str) else str(result)

    def spec(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self, tools: Sequence[Tool] = ()):
        self._tools: Dict[str, Tool] = {t.name: t for t in tools}

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def specs(self) -> List[Dict[str, Any]]:
        return [t.spec() for t in self._tools.values()]


def make_fetch_tool(
    name: str,
    fetch_fn: Callable[[str], Union[str, Awaitable[str]]],
    url_guard: Optional[UrlGuard] = None,
    *,
    description: str = "Fetch a URL and return its text",
) -> Tool:
    """Инструмент-фетчер, у которого URL валидируется UrlGuard ДО запроса.
    Ждёт args={'url': ...}. При отклонённом URL fetch НЕ выполняется."""
    guard = url_guard or UrlGuard()

    async def _fn(args: Dict[str, Any]) -> str:
        url = str(args.get("url", ""))
        # BUG-03: check() синхронный и при resolve_dns=True зовёт блокирующий
        # socket.getaddrinfo — уводим с event loop, без новой зависимости.
        verdict = await asyncio.to_thread(guard.check, url)
        if not verdict.allowed:
            logger.warning(f"fetch tool {name!r} blocked url: {verdict.reason}")
            return f"[fetch blocked: {verdict.reason}]"
        if inspect.iscoroutinefunction(fetch_fn):
            return await fetch_fn(verdict.url)
        return await asyncio.to_thread(fetch_fn, verdict.url)

    return Tool(name, _fn, description)


# ─────────────────────────────────────────────────────────────────────────
# Результат агентного прогона
# ─────────────────────────────────────────────────────────────────────────

AgentStatus = Literal["ok", "blocked_input", "blocked_output", "max_iters"]

BLOCKED_TOOL_PLACEHOLDER = "[tool output blocked: potential injection]"
UNKNOWN_TOOL_PLACEHOLDER = "[unknown tool]"


@dataclass
class ToolTraceEntry:
    tool: str
    status: str          # safe | sanitized | blocked | unknown
    reason: Optional[str] = None


@dataclass
class AgentResult:
    session_id: str
    status: AgentStatus
    verdict: Verdict
    output: str
    input_audit_hash: Optional[str] = None
    violation_layer: Optional[str] = None
    tool_trace: List[ToolTraceEntry] = field(default_factory=list)
    iterations: int = 0

    @property
    def ok(self) -> bool:
        return self.status == "ok"


# ─────────────────────────────────────────────────────────────────────────
# Агентный цикл
# ─────────────────────────────────────────────────────────────────────────

class ToolAgent:
    """Оборачивает pipeline + tool-calling бэкенд + реестр инструментов +
    ToolOutputGuard в безопасный агентный цикл."""

    def __init__(
        self,
        pipeline: SecurityPipeline,
        backend: ToolCallingBackend,
        registry: ToolRegistry,
        tool_output_guard: Optional[ToolOutputGuard] = None,
        max_iters: int = 6,
        blocked_message: str = "Доступ заблокирован.",
    ):
        self.pipeline = pipeline
        self.backend = backend
        self.registry = registry
        self.tool_guard = tool_output_guard or ToolOutputGuard()
        self.max_iters = max_iters
        self.blocked_message = blocked_message

    async def run(self, text: str, session_id: str) -> AgentResult:
        # ── Вход: Layer 1-3. Скомпрометирован → цикл НЕ запускается ──────
        in_ctx = await self.pipeline.process(text, session_id)
        if in_ctx.is_compromised:
            return AgentResult(
                session_id=session_id,
                status="blocked_input",
                verdict=in_ctx.verdict,
                output=self.blocked_message,
                input_audit_hash=in_ctx.audit_hash,
                violation_layer=in_ctx.violation_layer,
            )

        messages: List[Dict[str, Any]] = [{"role": "user", "content": text}]
        trace: List[ToolTraceEntry] = []
        specs = self.registry.specs()
        final_text: Optional[str] = None
        iterations = 0

        for i in range(self.max_iters):
            iterations = i + 1
            step = await self.backend.step(messages, specs)

            if isinstance(step, FinalAnswer):
                final_text = step.text
                break

            # ── ToolCall ────────────────────────────────────────────────
            messages.append({"role": "assistant", "tool_call": {"name": step.name, "args": step.args}})
            tool = self.registry.get(step.name)
            if tool is None:
                trace.append(ToolTraceEntry(step.name, "unknown"))
                messages.append({"role": "tool", "name": step.name, "content": UNKNOWN_TOOL_PLACEHOLDER})
                continue

            raw = await tool.run(step.args)

            # ── Guard: сканируем результат ДО возврата в модель ─────────
            verdict = self.tool_guard.check(raw, tool_name=step.name)
            trace.append(ToolTraceEntry(step.name, verdict.status, verdict.reason))
            if verdict.status == "blocked":
                content = BLOCKED_TOOL_PLACEHOLDER
            else:
                content = verdict.output  # safe или sanitized
            messages.append({"role": "tool", "name": step.name, "content": content})

        if final_text is None:
            # Цикл исчерпан без финального ответа — мягкая деградация.
            return AgentResult(
                session_id=session_id,
                status="max_iters",
                verdict=in_ctx.verdict,
                output="[достигнут лимит обращений к инструментам]",
                input_audit_hash=in_ctx.audit_hash,
                tool_trace=trace,
                iterations=iterations,
            )

        # ── Выход: Layer 4 ──────────────────────────────────────────────
        out_ctx = SecurityContext(session_id=session_id, user_input=text)
        out_ctx.ai_output = final_text
        out_ctx = await self.pipeline.process_output(out_ctx)
        blocked_out = out_ctx.is_compromised

        return AgentResult(
            session_id=session_id,
            status="blocked_output" if blocked_out else "ok",
            verdict=out_ctx.verdict if blocked_out else in_ctx.verdict,
            output=out_ctx.ai_output,
            input_audit_hash=in_ctx.audit_hash,
            violation_layer=out_ctx.violation_layer if blocked_out else None,
            tool_trace=trace,
            iterations=iterations,
        )
