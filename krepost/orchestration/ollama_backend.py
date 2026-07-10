"""
krepost/orchestration/ollama_backend.py

Боевой бэкенд поверх локального Ollama — замена EchoBackend на реальную LLM.
Реализует и ModelBackend (одноходовый generate), и ToolCallingBackend
(многоходовый step с инструментами).

Тот же ollama-клиент можно отдать пайплайну как guard_client: GuardClassifier
вызывает `guard_client.chat(model=..., messages=..., format="json")` — это ровно
интерфейс ollama.Client/AsyncClient. Так main-модель (Qwen3.x) и guard
(Qwen3Guard) ходят через один клиент, различаясь только именем модели.

Клиент внедряется (тесты — фейк); в проде создаётся лениво из host. Пакет
`ollama` — необязательная зависимость (extra `ollama`), импортируется только
при реальном использовании.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from krepost.orchestration.tools import BackendStep, FinalAnswer, ToolCall

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


def _normalize_message(resp: Any) -> Dict[str, Any]:
    """Приводит ответ ollama (dict ИЛИ объект) к {content, tool_calls}."""
    if isinstance(resp, dict):
        msg = resp.get("message", {})
    else:
        msg = getattr(resp, "message", None) or {}

    if isinstance(msg, dict):
        content = msg.get("content") or ""
        raw_tcs = msg.get("tool_calls") or []
    else:
        content = getattr(msg, "content", "") or ""
        raw_tcs = getattr(msg, "tool_calls", None) or []

    tool_calls: List[Dict[str, Any]] = []
    for tc in raw_tcs:
        fn = tc.get("function") if isinstance(tc, dict) else getattr(tc, "function", None)
        if fn is None:
            continue
        if isinstance(fn, dict):
            name, args = fn.get("name", ""), fn.get("arguments") or {}
        else:
            name, args = getattr(fn, "name", ""), getattr(fn, "arguments", None) or {}
        tool_calls.append({"name": name, "args": dict(args)})

    return {"content": content, "tool_calls": tool_calls}


def _to_ollama_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Внутренний формат tool-loop → формат сообщений ollama."""
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        if role == "assistant" and "tool_call" in m:
            tc = m["tool_call"]
            out.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": tc["name"],
                                             "arguments": tc.get("args", {})}}],
            })
        elif role == "tool":
            out.append({"role": "tool", "content": m.get("content", ""),
                        "name": m.get("name", "")})
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


class OllamaBackend:
    """ModelBackend + ToolCallingBackend поверх Ollama."""

    def __init__(
        self,
        model: str,
        host: str = "http://127.0.0.1:11434",
        client: Any = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        self.name = model
        self.model = model
        self.host = host
        self._client = client
        self.options = options or {}

    def _get_client(self) -> Any:
        if self._client is None:
            import ollama  # ленивый импорт — только при реальном использовании
            self._client = ollama.Client(host=self.host)
        return self._client

    async def _chat(self, messages: List[Dict[str, Any]], tools: Any = None) -> Any:
        client = self._get_client()
        kwargs: Dict[str, Any] = {"model": self.model, "messages": messages}
        if self.options:
            kwargs["options"] = self.options
        if tools:
            kwargs["tools"] = tools
        if asyncio.iscoroutinefunction(client.chat):
            return await client.chat(**kwargs)
        return await asyncio.to_thread(lambda: client.chat(**kwargs))

    # ── ModelBackend ────────────────────────────────────────────────────
    async def generate(self, prompt: str, ctx: Any) -> str:
        resp = await self._chat([{"role": "user", "content": prompt}])
        return _normalize_message(resp)["content"]

    # ── ToolCallingBackend ──────────────────────────────────────────────
    async def step(self, messages: List[Dict[str, Any]],
                   tools: List[Dict[str, Any]]) -> BackendStep:
        resp = await self._chat(_to_ollama_messages(messages), tools=tools or None)
        norm = _normalize_message(resp)
        if norm["tool_calls"]:
            tc = norm["tool_calls"][0]
            return ToolCall(tc["name"], tc["args"])
        return FinalAnswer(norm["content"])
