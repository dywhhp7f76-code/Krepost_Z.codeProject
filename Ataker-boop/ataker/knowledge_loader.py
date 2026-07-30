"""Чтение markdown KB для Planner (пока без Chroma)."""
from __future__ import annotations

from pathlib import Path
from typing import List

DEFAULT_KNOWLEDGE_ROOT = Path(__file__).resolve().parents[1] / "knowledge"


def knowledge_root() -> Path:
    return DEFAULT_KNOWLEDGE_ROOT


def list_source_cards(root: Path | None = None) -> List[Path]:
    base = (root or knowledge_root()) / "sources"
    if not base.is_dir():
        return []
    return sorted(base.glob("*.md"))


def load_snippets(max_chars: int = 1200, root: Path | None = None) -> List[str]:
    """Короткие сниппеты для PlannerInput.knowledge_snippets."""
    snippets: List[str] = []
    base = root or knowledge_root()
    for path in list_source_cards(base):
        text = path.read_text(encoding="utf-8", errors="replace")
        # drop first frontmatter-less header noise: take first ~max_chars/n
        body = text.strip()
        if len(body) > max_chars:
            body = body[: max_chars - 20] + "\n…"
        snippets.append(f"### {path.name}\n{body}")
    return snippets


def catalog_summary(root: Path | None = None) -> str:
    cards = list_source_cards(root)
    lines = [f"knowledge cards: {len(cards)}"]
    for p in cards:
        lines.append(f" - {p.name}")
    return "\n".join(lines)
