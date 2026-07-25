"""Общие хелперы: конфиг, безопасная запись в Inbox."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"

_UNSAFE = re.compile(r'[<>:"|?*\\]')


def load_config() -> Dict[str, Any]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inbox = Path(cfg["vault_inbox"]).expanduser()
    inbox.mkdir(parents=True, exist_ok=True)
    cfg["_inbox"] = inbox
    return cfg


def slugify(title: str, max_len: int = 60) -> str:
    t = (title or "note").strip()
    t = _UNSAFE.sub("", t)
    t = re.sub(r"\s+", " ", t).strip() or "note"
    return t[:max_len].rstrip(". ")


def write_note(
    inbox: Path,
    *,
    title: str,
    body: str,
    tags: list[str] | None = None,
    source: str = "",
    agent: str = "",
) -> Path:
    """Пишет ТОЛЬКО в Inbox. Ты потом сам решишь, куда перенести в vault."""
    inbox.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    fname = f"{stamp}__{slugify(title)}.md"
    path = inbox / fname
    tag_line = " ".join(f"#{t}" for t in (tags or []) if t)
    front = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        f"agent: {agent}",
        f"status: inbox",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if source:
        front.append(f"**Источник:** {source}")
        front.append("")
    if tag_line:
        front.append(tag_line)
        front.append("")
    front.append("> Черновик агента. Проверь и перенеси из `09-Inbox/from_agents` куда нужно.")
    front.append("")
    front.append(body.strip())
    front.append("")
    path.write_text("\n".join(front), encoding="utf-8")
    return path
