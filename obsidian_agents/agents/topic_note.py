"""Агент 2: тема/вопрос → структурированная заметка в Inbox (опц. LM Studio)."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen

from agents.common import load_config, write_note

SYSTEM = (
    "Ты помощник для Obsidian. Пиши заметку на русском markdown. "
    "Структура: краткий вывод, ключевые пункты, вопросы на потом, источники (если знаешь). "
    "Не выдумывай факты — помечай неуверенность. Без воды."
)


def _lm_generate(cfg: dict, topic: str, extra: str) -> Optional[str]:
    base = (cfg.get("lmstudio_url") or "").rstrip("/")
    if not base:
        return None
    model = cfg.get("lmstudio_model") or ""
    user = f"Тема / вопрос:\n{topic}\n"
    if extra.strip():
        user += f"\nДоп. контекст от оператора:\n{extra.strip()}\n"
    user += "\nСобери заметку для Inbox Obsidian."
    payload: Dict[str, Any] = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
    }
    if model:
        payload["model"] = model
    else:
        # LM Studio часто требует model id — возьмём первый из /models
        try:
            with urlopen(base + "/models", timeout=5) as resp:
                data = json.loads(resp.read().decode())
            models = data.get("data") or []
            if models:
                payload["model"] = models[0].get("id") or "local"
            else:
                payload["model"] = "local"
        except Exception:
            payload["model"] = "local"
    req = Request(
        base + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return None


def _template(topic: str, extra: str) -> str:
    return "\n".join(
        [
            "## Суть",
            "",
            f"(черновик без LLM) Тема: **{topic.strip()}**",
            "",
            "## Контекст оператора",
            "",
            extra.strip() or "_нет_",
            "",
            "## Ключевые пункты",
            "",
            "- …",
            "",
            "## Вопросы / что проверить",
            "",
            "- …",
            "",
            "## Куда перенести",
            "",
            "_Реши сам: Energy / Architecture / Knowledge / …_",
            "",
        ]
    )


def make_topic_note(topic: str, *, extra: str = "", use_llm: bool = True) -> Dict[str, Any]:
    topic = (topic or "").strip()
    if not topic:
        return {"ok": False, "error": "пустая тема"}
    cfg = load_config()
    used_llm = False
    body = None
    if use_llm:
        body = _lm_generate(cfg, topic, extra)
        used_llm = body is not None
    if not body:
        body = _template(topic, extra)
    title = topic if len(topic) < 80 else topic[:77] + "…"
    path = write_note(
        cfg["_inbox"],
        title=title,
        body=body,
        tags=["inbox", "topic", "draft"],
        source="",
        agent="topic_note" + ("+llm" if used_llm else "+template"),
    )
    return {
        "ok": True,
        "agent": "topic_note",
        "used_llm": used_llm,
        "title": title,
        "path": str(path),
        "preview": body[:400],
    }
