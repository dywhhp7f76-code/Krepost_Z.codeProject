"""Ingest helpers for private operator uploads → vault/personal/."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


_SAFE = re.compile(r"[^A-Za-z0-9._\-а-яА-ЯёЁ]+")


def safe_filename(name: str) -> str:
    name = Path(name).name.strip() or "note.md"
    name = _SAFE.sub("_", name)
    if not name.lower().endswith((".md", ".txt")):
        name = name + ".md"
    return name[:180]


def personal_dir(vault_root: Path) -> Path:
    d = vault_root / "personal"
    d.mkdir(parents=True, exist_ok=True)
    readme = d / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Личные / закрытые заметки оператора\n\n"
            "Сюда пишет только авторизованный Krepost Chat.\n"
            "Не синхронизировать на Air / грязную зону.\n",
            encoding="utf-8",
        )
    return d


def write_personal_note(
    vault_root: Path,
    filename: str,
    content: str,
    *,
    private: bool = True,
) -> Tuple[Path, str]:
    """Write file under vault/personal/. Returns (path, doc_id)."""
    dest_dir = personal_dir(vault_root)
    fname = safe_filename(filename)
    path = dest_dir / fname
    if path.exists():
        stem, suf = path.stem, path.suffix
        n = 1
        while path.exists():
            path = dest_dir / f"{stem}_{n}{suf}"
            n += 1
    header = ""
    if private:
        header = (
            "---\n"
            "private: true\n"
            "domain: personal\n"
            "owner: operator\n"
            "---\n\n"
        )
    path.write_text(header + content, encoding="utf-8")
    doc_id = f"personal/{path.name}"
    return path, doc_id


def ingest_metadata(*, private: bool = True) -> Dict[str, Any]:
    return {
        "domain": "personal",
        "private": private,
        "owner": "operator",
        "source": "krepost_chat_upload",
    }
