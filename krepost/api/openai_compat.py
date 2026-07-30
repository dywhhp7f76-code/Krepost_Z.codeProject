"""OpenAI-compatible shim for AnythingLLM / Generic OpenAI clients.

Maps /v1/chat/completions → Orchestrator.handle (or ToolAgent.run).
Does NOT talk to LM Studio directly — always through Крепость.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple


def extract_user_text(messages: List[Dict[str, Any]]) -> str:
    """Last user message; if none — join all non-system contents."""
    users: List[str] = []
    for m in messages or []:
        role = (m.get("role") or "").lower()
        content = m.get("content")
        if isinstance(content, list):
            # multimodal: take text parts
            parts = [
                str(p.get("text") or "")
                for p in content
                if isinstance(p, dict) and p.get("type") in (None, "text")
            ]
            content = "\n".join(x for x in parts if x)
        text = (content or "").strip() if isinstance(content, str) else ""
        if not text:
            continue
        if role == "user":
            users.append(text)
    if users:
        return users[-1]
    # fallback: last non-system
    for m in reversed(messages or []):
        if (m.get("role") or "").lower() == "system":
            continue
        c = m.get("content")
        if isinstance(c, str) and c.strip():
            return c.strip()
    return ""


def resolve_mode(model: Optional[str]) -> Tuple[str, bool]:
    """Return (mode, use_memory). mode: query|agent."""
    m = (model or "krepost").strip().lower()
    if m in ("krepost-agent", "agent", "krepost/agent"):
        return "agent", True
    if m in ("krepost-fast", "fast", "krepost/fast"):
        return "query", False
    # default: full Крепость with vault/RAG
    return "query", True


def chat_completion_payload(
    *,
    content: str,
    model: str,
    finish_reason: str = "stop",
    verdict: str = "GREEN",
    status: str = "ok",
) -> Dict[str, Any]:
    cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    return {
        "id": cid,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model or "krepost",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        # non-standard but useful for operators / AnythingLLM logs
        "krepost": {"status": status, "verdict": verdict},
    }


def stream_chunks(content: str, model: str) -> List[str]:
    """Minimal SSE payloads (one content chunk + stop + DONE)."""
    cid = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    first = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model or "krepost",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None,
            }
        ],
    }
    last = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model or "krepost",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    return [
        f"data: {json.dumps(first, ensure_ascii=False)}\n\n",
        f"data: {json.dumps(last, ensure_ascii=False)}\n\n",
        "data: [DONE]\n\n",
    ]


def list_models(*, agent_enabled: bool) -> Dict[str, Any]:
    data = [
        {
            "id": "krepost",
            "object": "model",
            "owned_by": "krepost",
            "description": "Крепость: security + vault/RAG + main LLM",
        },
        {
            "id": "krepost-fast",
            "object": "model",
            "owned_by": "krepost",
            "description": "Крепость без RAG (быстрый путь)",
        },
    ]
    if agent_enabled:
        data.append(
            {
                "id": "krepost-agent",
                "object": "model",
                "owned_by": "krepost",
                "description": "Крепость ToolAgent (vault_read / memory_search / fetch)",
            }
        )
    return {"object": "list", "data": data}
