"""Реестр пользовательских агентов (JSON в agents/user/)."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.clipper import clip_url
from agents.common import load_config, slugify, write_note
from agents.topic_note import make_topic_note

USER_DIR = Path(__file__).resolve().parent / "user"
_ID_RE = re.compile(r"[^a-z0-9а-яё_\-]+", re.I)


def _ensure_dir() -> Path:
    USER_DIR.mkdir(parents=True, exist_ok=True)
    return USER_DIR


def make_id(name: str) -> str:
    s = slugify(name, max_len=40).lower().replace(" ", "-")
    s = _ID_RE.sub("-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-") or "agent"
    return s[:48]


def list_agents() -> List[Dict[str, Any]]:
    d = _ensure_dir()
    out: List[Dict[str, Any]] = []
    for p in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["_file"] = p.name
            out.append(data)
        except Exception:
            continue
    return out


def get_agent(agent_id: str) -> Optional[Dict[str, Any]]:
    path = _ensure_dir() / f"{agent_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_agent(spec: Dict[str, Any]) -> Dict[str, Any]:
    d = _ensure_dir()
    aid = spec.get("id") or make_id(spec.get("name") or "agent")
    aid = make_id(aid)
    # уникальность
    base = aid
    n = 2
    while (d / f"{aid}.json").is_file() and spec.get("overwrite") is not True:
        aid = f"{base}-{n}"
        n += 1
    spec = dict(spec)
    spec.pop("overwrite", None)
    spec["id"] = aid
    spec.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    spec["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = d / f"{aid}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return spec


def delete_agent(agent_id: str) -> bool:
    path = _ensure_dir() / f"{agent_id}.json"
    if not path.is_file():
        return False
    path.unlink()
    return True


def run_agent(agent_id: str, text: str = "", url: str = "") -> Dict[str, Any]:
    """Запуск сохранённого агента. Без генерации кода — только обёртки."""
    spec = get_agent(agent_id)
    if not spec:
        return {"ok": False, "error": f"агент не найден: {agent_id}"}

    kind = (spec.get("type") or "topic").lower()
    instr = (spec.get("instructions") or "").strip()
    tags = list(spec.get("tags") or [])
    name = spec.get("name") or agent_id

    if kind == "clip":
        if not url.strip():
            # вытащить URL из текста
            m = re.search(r"https?://\S+", text or "")
            url = m.group(0) if m else ""
        if not url.strip():
            return {"ok": False, "error": "нужна ссылка (URL)"}
        note = instr
        if text.strip() and text.strip() != url.strip():
            note = (note + "\n\n" + text.strip()).strip()
        result = clip_url(url.strip(), note=note)
        if result.get("ok") and tags:
            # теги уже в write_note через clipper — доп. пометка в ответе
            result["agent"] = name
            result["tags"] = tags
        return result

    if kind == "topic":
        topic = text.strip() or name
        extra = instr
        use_llm = bool(spec.get("use_llm", True))
        result = make_topic_note(topic, extra=extra, use_llm=use_llm)
        if result.get("ok"):
            result["agent"] = name
        return result

    if kind in ("note", "checklist", "inbox"):
        cfg = load_config()
        title = (spec.get("title_prefix") or name).strip()
        if text.strip():
            title = f"{title}: {text.strip()[:80]}"
        body_parts = [
            f"## Инструкция агента «{name}»",
            "",
            instr or "_нет_",
            "",
            "## Ввод оператора",
            "",
            text.strip() or "_пусто_",
            "",
        ]
        if kind == "checklist":
            body_parts += [
                "## Чеклист",
                "",
            ]
            for item in spec.get("checklist") or ["…"]:
                body_parts.append(f"- [ ] {item}")
            body_parts.append("")
        path = write_note(
            cfg["_inbox"],
            title=title[:120],
            body="\n".join(body_parts),
            tags=tags or ["agent"],
            agent=f"user:{agent_id}",
        )
        preview = path.read_text(encoding="utf-8")[:500]
        return {
            "ok": True,
            "agent": name,
            "title": title,
            "path": str(path),
            "preview": preview,
        }

    return {"ok": False, "error": f"неизвестный type: {kind}"}
