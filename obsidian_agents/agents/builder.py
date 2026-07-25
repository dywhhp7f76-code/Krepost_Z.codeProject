"""Сборка агента из текстового запроса. Работает без LLM; Studio — опция."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from agents.common import load_config
from agents.registry import make_id, save_agent

# ключи → тип агента
_CLIP_HINTS = (
    "сайт",
    "ссылк",
    "ссыло",
    "url",
    "клип",
    "clip",
    "страниц",
    "статью",
    "статей",
    "веб",
    "скачива",
    "с url",
    "по url",
)
_CHECK_HINTS = ("чек", "checklist", "список дел", "todo", "галоч", "чеклист")
_TOPIC_HINTS = ("заметк", "тему", "темы", "исследова", "конспект", "досье", "разбор")


def _guess_type(text: str) -> str:
    t = text.lower()
    if any(h in t for h in _CLIP_HINTS):
        return "clip"
    if any(h in t for h in _CHECK_HINTS):
        return "checklist"
    if any(h in t for h in _TOPIC_HINTS):
        return "topic"
    # по умолчанию — заметка по теме (самый полезный)
    return "topic"


def _guess_name(text: str) -> str:
    # «назови X» / «имя: X»
    m = re.search(
        r"(?:назови\s+(?:его\s+|её\s+|агента\s+)?|имя\s*[:\-]\s*)([«\"]?)(.+?)\1(?:\s|$|,|\.|$)",
        text,
        re.I,
    )
    if m:
        name = m.group(2).strip(" «»\"'")
        if 2 <= len(name) <= 60:
            return name[:60]

    # «агент для/про …» — берём хвост целиком (короткий)
    m2 = re.search(
        r"агент[аы]?\s+(?:который\s+|для\s+|про\s+|по\s+)?(.+)",
        text,
        re.I,
    )
    if m2:
        chunk = m2.group(1).strip().rstrip(".")
        # убрать ведущие служебные
        chunk = re.sub(
            r"^(?:для\s+|про\s+|по теме\s+|по\s+)", "", chunk, flags=re.I
        ).strip()
        if 2 <= len(chunk) <= 60:
            return chunk[:60]
        words = chunk.split()
        return " ".join(words[:6])[:60] or "Мой агент"

    m3 = re.search(r"(?:про|для|по теме)\s+(.+?)(?:\.|,|$)", text, re.I)
    if m3:
        chunk = m3.group(1).strip()
        return " ".join(chunk.split()[:6])[:60] or "Мой агент"

    # чеклист / утренний …
    if "чеклист" in text.lower() or "checklist" in text.lower():
        tail = re.sub(r"(?i).*?(чеклист|checklist)\s*", "", text).strip(" :\-")
        if tail:
            return ("Чеклист " + " ".join(tail.split()[:5]))[:60]
        return "Чеклист"

    words = [w for w in re.split(r"\s+", text.strip()) if w][:5]
    return (" ".join(words)[:50] if words else "Мой агент") or "Мой агент"


def _extract_tags(text: str) -> List[str]:
    tags = re.findall(r"#([a-zA-Zа-яА-ЯёЁ0-9_\-]+)", text)
    # эвристики
    low = text.lower()
    if "крипт" in low or "bitcoin" in low or "btc" in low:
        tags.append("crypto")
    if "крепост" in low:
        tags.append("krepost")
    if "obsidian" in low or "vault" in low:
        tags.append("obsidian")
    # уникальные
    seen = set()
    out: List[str] = []
    for t in tags:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:8]


def _extract_checklist(text: str) -> List[str]:
    items: List[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*[-*•]\s+(.+)", line)
        if m:
            items.append(m.group(1).strip())
    if items:
        return items[:20]
    # «пункты: a, b, c»
    m = re.search(r"(?:пункт[ыа]?|шаги|дела)\s*[:\-]\s*(.+)", text, re.I)
    if m:
        parts = re.split(r"[,;]| и ", m.group(1))
        return [p.strip() for p in parts if p.strip()][:20]
    return ["Сделать первый шаг", "Проверить результат", "Перенести из Inbox"]


def rule_build(request: str) -> Dict[str, Any]:
    """Сборка без ИИ — шаблон + эвристики."""
    text = (request or "").strip()
    if len(text) < 3:
        raise ValueError("слишком короткий запрос")

    kind = _guess_type(text)
    name = _guess_name(text)
    tags = _extract_tags(text)
    instructions = (
        f"Агент создан по запросу оператора.\n\nЗапрос:\n{text}\n\n"
        f"Делай заметки в Inbox. Тип: {kind}."
    )

    spec: Dict[str, Any] = {
        "name": name,
        "type": kind,
        "instructions": instructions,
        "tags": tags or ["custom"],
        "use_llm": kind == "topic",
        "source_request": text,
        "built_by": "rules",
    }
    if kind == "checklist":
        spec["checklist"] = _extract_checklist(text)
        spec["title_prefix"] = name
    if kind == "clip":
        spec["use_llm"] = False
        tags.append("clip") if "clip" not in tags else None
        spec["tags"] = list(dict.fromkeys(tags or ["clip"]))
    return spec


def _try_studio(request: str, cfg: dict) -> Optional[Dict[str, Any]]:
    """Опционально: спросить Крепость на Studio сформулировать JSON."""
    base = (cfg.get("krepost_url") or "").rstrip("/")
    if not base:
        return None
    prompt = (
        "Собери JSON-спеку агента для Obsidian Inbox. Только JSON, без markdown.\n"
        "Поля: name (str), type (clip|topic|checklist|note), instructions (str), "
        "tags (string[]), use_llm (bool), checklist (string[], только для checklist).\n"
        f"Запрос оператора:\n{request}"
    )
    payload = {"text": prompt, "session_id": "obsidian-agent-builder"}
    req = Request(
        base + "/v1/query",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
        answer = (data.get("answer") or data.get("text") or "").strip()
        # вытащить JSON
        m = re.search(r"\{[\s\S]*\}", answer)
        if not m:
            return None
        parsed = json.loads(m.group(0))
        if not isinstance(parsed, dict) or not parsed.get("name"):
            return None
        kind = str(parsed.get("type") or "topic").lower()
        if kind not in ("clip", "topic", "checklist", "note", "inbox"):
            kind = "topic"
        return {
            "name": str(parsed["name"])[:60],
            "type": kind,
            "instructions": str(parsed.get("instructions") or request)[:4000],
            "tags": [str(t) for t in (parsed.get("tags") or ["custom"])][:8],
            "use_llm": bool(parsed.get("use_llm", kind == "topic")),
            "checklist": [str(x) for x in (parsed.get("checklist") or [])][:20],
            "source_request": request,
            "built_by": "studio",
        }
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError, OSError):
        return None


def build_from_request(
    request: str, *, prefer_studio: bool = True, save: bool = True
) -> Tuple[Dict[str, Any], str]:
    """
    Возвращает (spec, reply_text).
    Без ИИ на Air всегда работает; Studio улучшает, если доступна.
    """
    cfg = load_config()
    spec: Optional[Dict[str, Any]] = None
    if prefer_studio and cfg.get("krepost_url"):
        spec = _try_studio(request, cfg)
    if spec is None:
        spec = rule_build(request)

    if save:
        saved = save_agent(spec)
    else:
        saved = {**spec, "id": make_id(spec["name"])}

    type_ru = {
        "clip": "клиппер ссылок → Inbox",
        "topic": "заметка по теме → Inbox",
        "checklist": "чеклист → Inbox",
        "note": "свободная заметка → Inbox",
        "inbox": "свободная заметка → Inbox",
    }.get(saved["type"], saved["type"])

    reply = (
        f"Готово: агент «{saved['name']}» (id: `{saved['id']}`).\n"
        f"Тип: {type_ru}\n"
        f"Сборка: {saved.get('built_by', '?')}\n"
        f"Теги: {', '.join(saved.get('tags') or [])}\n\n"
        f"Запусти его вкладкой «Мои агенты» или напиши: /run {saved['id']} …"
    )
    return saved, reply


def chat_turn(message: str, *, prefer_studio: bool = True) -> Dict[str, Any]:
    """Один ход чата: создать / список / запуск / помощь."""
    from agents.registry import delete_agent, get_agent, list_agents, run_agent

    msg = (message or "").strip()
    low = msg.lower()

    if not msg or low in ("help", "помощь", "?"):
        return {
            "ok": True,
            "role": "assistant",
            "text": (
                "Напиши, какого агента хочешь — например:\n"
                "• «Агент для ссылок про крипту»\n"
                "• «Чеклист утренний: почта, календарь, Inbox»\n"
                "• «Заметки по теме Крепость»\n\n"
                "Команды: /list · /run id текст · /del id\n"
                "ИИ на Air не нужен. Если Studio жива — разбор чуть умнее."
            ),
        }

    if low in ("/list", "list", "список", "мои агенты"):
        agents = list_agents()
        if not agents:
            return {
                "ok": True,
                "role": "assistant",
                "text": "Пока пусто. Опиши агента обычным текстом — создам.",
            }
        lines = ["Твои агенты:"]
        for a in agents:
            lines.append(f"• `{a.get('id')}` — {a.get('name')} [{a.get('type')}]")
        return {"ok": True, "role": "assistant", "text": "\n".join(lines), "agents": agents}

    m_run = re.match(r"^/run\s+(\S+)\s*(.*)$", msg, re.I | re.S)
    if m_run:
        result = run_agent(m_run.group(1), text=m_run.group(2).strip())
        if not result.get("ok"):
            return {
                "ok": False,
                "role": "assistant",
                "text": result.get("error") or "ошибка запуска",
            }
        return {
            "ok": True,
            "role": "assistant",
            "text": (
                f"Запустил «{result.get('agent') or m_run.group(1)}».\n"
                f"{result.get('title', '')}\n{result.get('path', '')}"
            ),
            "result": result,
        }

    m_del = re.match(r"^/del(?:ete)?\s+(\S+)\s*$", msg, re.I)
    if m_del:
        ok = delete_agent(m_del.group(1))
        return {
            "ok": ok,
            "role": "assistant",
            "text": "Удалил." if ok else "Не нашёл такого id.",
        }

    # если похоже на запуск существующего по имени
    if low.startswith("запусти ") or low.startswith("run "):
        rest = msg.split(None, 1)[1] if " " in msg else ""
        aid = rest.split()[0] if rest else ""
        if get_agent(aid):
            result = run_agent(aid, text=rest[len(aid) :].strip())
            return {
                "ok": bool(result.get("ok")),
                "role": "assistant",
                "text": result.get("path") or result.get("error") or str(result),
                "result": result,
            }

    try:
        saved, reply = build_from_request(msg, prefer_studio=prefer_studio, save=True)
        return {
            "ok": True,
            "role": "assistant",
            "text": reply,
            "agent": saved,
        }
    except Exception as e:
        return {
            "ok": False,
            "role": "assistant",
            "text": f"Не смог собрать: {type(e).__name__}: {e}",
        }
