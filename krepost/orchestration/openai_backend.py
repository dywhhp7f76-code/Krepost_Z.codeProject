"""
krepost/orchestration/openai_backend.py

Бэкенд поверх ЛЮБОГО OpenAI-совместимого сервера: LM Studio, vLLM, LocalAI,
облачные OpenAI-совместимые endpoint'ы. Прямое следствие «архитектура важнее
модели» (§5.2) — Крепость не привязана к одному движку.

Даёт две вещи:
- `OpenAIBackend` — ModelBackend (generate) + ToolCallingBackend (step) для
  основной модели;
- `OpenAIGuardClient` — тонкий адаптер, чей `.chat(model, messages, format)`
  совпадает с интерфейсом, который ждёт GuardClassifier, и возвращает форму
  `{"message":{"content": ...}}`, понятную его парсеру. Так LM Studio может быть
  и guard-движком.

HTTP по умолчанию через stdlib `urllib` (без новых зависимостей). `transport`
внедряется — в тестах фейк, в проде реальный POST. Никакой сети в тестах.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from krepost.orchestration.tools import BackendStep, FinalAnswer, ToolCall

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


Transport = Callable[[Dict[str, Any]], Dict[str, Any]]

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"   # LM Studio по умолчанию


# ─────────────────────────────────────────────────────────────────────────
# HTTP + разбор ответа
# ─────────────────────────────────────────────────────────────────────────

def _make_urllib_transport(base_url: str, api_key: str, timeout: int) -> Transport:
    url = base_url.rstrip("/") + "/chat/completions"

    def _post(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))

    return _post


def _message(resp: Dict[str, Any]) -> Dict[str, Any]:
    choices = resp.get("choices") or []
    if not choices:
        return {}
    return choices[0].get("message") or {}


def _content(resp: Dict[str, Any]) -> str:
    return _message(resp).get("content") or ""


def _to_openai_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Внутренний формат tool-loop → OpenAI, с парностью tool_call_id."""
    out: List[Dict[str, Any]] = []
    pending_id: Optional[str] = None
    for m in messages:
        role = m.get("role", "user")
        if role == "assistant" and "tool_call" in m:
            tc = m["tool_call"]
            call_id = f"call_{len(out)}"
            out.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": call_id, "type": "function",
                    "function": {"name": tc["name"],
                                 "arguments": json.dumps(tc.get("args", {}), ensure_ascii=False)},
                }],
            })
            pending_id = call_id
        elif role == "tool":
            out.append({"role": "tool",
                        "tool_call_id": pending_id or f"call_{len(out)}",
                        "content": m.get("content", "")})
            pending_id = None
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


def _to_openai_tools(specs: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
    if not specs:
        return None
    return [{
        "type": "function",
        "function": {
            "name": s["name"],
            "description": s.get("description", ""),
            "parameters": s.get("parameters", {"type": "object", "properties": {}}),
        },
    } for s in specs]


# ─────────────────────────────────────────────────────────────────────────
# Backend
# ─────────────────────────────────────────────────────────────────────────

class OpenAIBackend:
    """ModelBackend + ToolCallingBackend поверх OpenAI-совместимого сервера."""

    def __init__(
        self,
        model: str,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "lm-studio",
        transport: Optional[Transport] = None,
        options: Optional[Dict[str, Any]] = None,
        timeout: int = 120,
    ):
        self.name = model
        self.model = model
        self.base_url = base_url
        self._transport = transport or _make_urllib_transport(base_url, api_key, timeout)
        self.options = options or {}

    async def _chat(self, messages: List[Dict[str, Any]], tools: Any = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"model": self.model, "messages": messages, **self.options}
        if tools:
            payload["tools"] = tools
        if inspect.iscoroutinefunction(self._transport):
            return await self._transport(payload)
        return await asyncio.to_thread(self._transport, payload)

    async def generate(self, prompt: str, ctx: Any) -> str:
        resp = await self._chat([{"role": "user", "content": prompt}])
        return _content(resp)

    async def step(self, messages: List[Dict[str, Any]],
                   tools: List[Dict[str, Any]]) -> BackendStep:
        resp = await self._chat(_to_openai_messages(messages), tools=_to_openai_tools(tools))
        msg = _message(resp)
        tcs = msg.get("tool_calls") or []
        if tcs:
            fn = tcs[0].get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            return ToolCall(fn.get("name", ""), args)
        return FinalAnswer(msg.get("content") or "")


# ─────────────────────────────────────────────────────────────────────────
# Guard-адаптер
# ─────────────────────────────────────────────────────────────────────────

class OpenAIGuardClient:
    """Адаптер под интерфейс GuardClassifier (`chat(model, messages, format)`).
    Возвращает `{"message":{"content": ...}}` — форму, понятную его парсеру."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "lm-studio",
        transport: Optional[Transport] = None,
        timeout: int = 60,
    ):
        self._transport = transport or _make_urllib_transport(base_url, api_key, timeout)

    def chat(self, model: str, messages: List[Dict[str, Any]],
             format: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"model": model, "messages": messages}
        if format == "json":
            # response_format: LM Studio 0.4+ принимает только json_schema/text,
            # старые серверы — json_object. Пробуем text (guard-модели типа
            # Qwen3Guard отдают нативный текстовый формат, JSON не нужен).
            payload["response_format"] = {"type": "text"}
        # Т9: проброс temperature из options (GuardClassifier передаёт
        # options={"temperature":0} для детерминизма guard).
        options = kwargs.get("options")
        if isinstance(options, dict) and "temperature" in options:
            payload["temperature"] = options["temperature"]
        resp = self._transport(payload)
        return {"message": {"content": _content(resp)}}
