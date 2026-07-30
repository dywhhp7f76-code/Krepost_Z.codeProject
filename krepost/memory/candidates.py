"""L1 candidates bridge: Dataview/JSON cache → paths for L2 semantic.

Schema (candidates.json):
{
  "version": 1,
  "generated_at": "...",
  "source": "dataviewjs|python_l1",
  "filter": {"folders": [...], "tags": [...], "date_from": null, "date_to": null},
  "items": [{"path": "05_Knowledge_Base/foo.md", "tags": ["energy"], "mtime": "..."}]
}
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

CANDIDATES_VERSION = 1
DEFAULT_CACHE_REL = "00-System/cache/candidates.json"


@dataclass
class CandidateItem:
    path: str
    tags: List[str] = field(default_factory=list)
    mtime: str = ""
    domain: str = ""


@dataclass
class CandidatesDoc:
    version: int
    generated_at: str
    source: str
    filter: Dict[str, Any]
    items: List[CandidateItem]

    def paths(self) -> List[str]:
        return [i.path for i in self.items]


def save_candidates(doc: CandidatesDoc, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": doc.version,
        "generated_at": doc.generated_at,
        "source": doc.source,
        "filter": doc.filter,
        "items": [asdict(i) for i in doc.items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_candidates(path: Path) -> CandidatesDoc:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = [
        CandidateItem(
            path=str(it.get("path") or ""),
            tags=[str(t) for t in (it.get("tags") or [])],
            mtime=str(it.get("mtime") or ""),
            domain=str(it.get("domain") or ""),
        )
        for it in raw.get("items") or []
        if it.get("path")
    ]
    return CandidatesDoc(
        version=int(raw.get("version") or CANDIDATES_VERSION),
        generated_at=str(raw.get("generated_at") or ""),
        source=str(raw.get("source") or ""),
        filter=dict(raw.get("filter") or {}),
        items=items,
    )


_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
_TAG_LINE = re.compile(r"^tags:\s*(.+)$", re.I | re.M)
_DATE_LINE = re.compile(r"^(?:date|created|updated):\s*['\"]?(\d{4}-\d{2}-\d{2})", re.I | re.M)


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Минимальный YAML-ish парсер frontmatter (без PyYAML)."""
    m = _FM_RE.match(text or "")
    if not m:
        return {}
    block = m.group(1)
    out: Dict[str, Any] = {}
    tags: List[str] = []
    tm = _TAG_LINE.search(block)
    if tm:
        raw = tm.group(1).strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1]
            tags = [t.strip().strip("'\"#") for t in inner.split(",") if t.strip()]
        else:
            tags = [raw.strip().strip("'\"#")]
    # list form under tags:
    if "tags:" in block.lower() and not tags:
        after = block.lower().split("tags:", 1)[1]
        for line in after.splitlines()[1:]:
            s = line.strip()
            if not s.startswith("-"):
                break
            tags.append(s[1:].strip().strip("'\"#"))
    if tags:
        out["tags"] = tags
    dm = _DATE_LINE.search(block)
    if dm:
        out["date"] = dm.group(1)
    return out


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def filter_vault_notes(
    vault: Path,
    *,
    folders: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    suffixes: Iterable[str] = (".md", ".markdown", ".txt"),
) -> List[CandidateItem]:
    """L1 без Dataview: path prefix + frontmatter tags/date."""
    from krepost.memory.domains import domain_from_relpath

    folders_n = [f.strip("/").replace("\\", "/") for f in (folders or []) if f.strip()]
    tags_n = {t.lstrip("#").lower() for t in (tags or []) if t.strip()}
    d0 = _parse_date(date_from)
    d1 = _parse_date(date_to)
    suf = {s.lower() for s in suffixes}
    out: List[CandidateItem] = []

    for path in sorted(vault.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in suf:
            continue
        rel = path.relative_to(vault).as_posix()
        if rel.startswith("00-System/cache/"):
            continue
        if folders_n and not any(
            rel == f or rel.startswith(f + "/") for f in folders_n
        ):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        note_tags = [str(t).lstrip("#").lower() for t in (fm.get("tags") or [])]
        if tags_n and not tags_n.intersection(note_tags):
            continue
        nd = _parse_date(str(fm.get("date") or ""))
        if d0 and (nd is None or nd < d0):
            continue
        if d1 and (nd is None or nd > d1):
            continue
        st = path.stat()
        out.append(
            CandidateItem(
                path=rel,
                tags=note_tags,
                mtime=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                domain=domain_from_relpath(rel),
            )
        )
    return out


def export_candidates(
    vault: Path,
    out_path: Path,
    *,
    folders: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    source: str = "python_l1",
) -> CandidatesDoc:
    items = filter_vault_notes(
        vault,
        folders=folders,
        tags=tags,
        date_from=date_from,
        date_to=date_to,
    )
    doc = CandidatesDoc(
        version=CANDIDATES_VERSION,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        source=source,
        filter={
            "folders": list(folders or []),
            "tags": list(tags or []),
            "date_from": date_from,
            "date_to": date_to,
        },
        items=items,
    )
    save_candidates(doc, out_path)
    return doc
