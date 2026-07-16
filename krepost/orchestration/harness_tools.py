"""
Боевые инструменты харнесса Крепости.

Все три инструмента fail-closed:
- fetch_url  — UrlGuard до запроса (SSRF), текст страницы обрезается;
- memory_search — только чтение из MemoryStore / Chroma;
- vault_read — только файлы внутри vault/, path-traversal режется.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from krepost.orchestration.tools import Tool, make_fetch_tool
from krepost.security.url_guard import UrlGuard

DEFAULT_VAULT = Path("vault")
MAX_FETCH_CHARS = 8000
MAX_VAULT_CHARS = 12000


def _http_fetch(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "KrepostHarness/1.0"})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL уже через UrlGuard
        raw = resp.read(MAX_FETCH_CHARS * 4)
    text = raw.decode("utf-8", errors="replace")
    # грубо срезаем теги, чтобы модель не жрала HTML-помойку
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_FETCH_CHARS] or "[empty page]"


def make_memory_search_tool(memory_store: Any) -> Tool:
    async def _fn(args: Dict[str, Any]) -> str:
        query = str(args.get("query", "")).strip()
        if not query:
            return "[memory_search: empty query]"
        top_k = int(args.get("top_k", 5) or 5)
        top_k = max(1, min(top_k, 10))
        result = await memory_store.retrieve(query, k=top_k)
        ctx = memory_store.build_context(result)
        if not ctx.strip():
            return "[memory_search: nothing relevant]"
        return ctx[:MAX_VAULT_CHARS]

    return Tool(
        name="memory_search",
        fn=_fn,
        description=(
            "Search Krepost long-term memory (Obsidian vault / Chroma). "
            "Use for facts, notes, architecture. Args: query (string), optional top_k (1-10)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "top_k": {"type": "integer", "description": "How many chunks (1-10)"},
            },
            "required": ["query"],
        },
    )


def make_vault_read_tool(vault_root: Path | str = DEFAULT_VAULT) -> Tool:
    root = Path(vault_root).resolve()

    async def _fn(args: Dict[str, Any]) -> str:
        rel = str(args.get("path", "")).strip().lstrip("/")
        if not rel or ".." in Path(rel).parts:
            return "[vault_read blocked: invalid path]"
        if not rel.endswith(".md"):
            return "[vault_read blocked: only .md allowed]"
        target = (root / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return "[vault_read blocked: path escape]"
        if not target.is_file():
            return f"[vault_read: not found: {rel}]"
        text = target.read_text(encoding="utf-8", errors="replace")
        return text[:MAX_VAULT_CHARS]

    return Tool(
        name="vault_read",
        fn=_fn,
        description=(
            "Read a markdown note from the Obsidian vault (relative path, .md only). "
            "Example path: 07-Krepost_Architecture/01_Core/RAG_SMOKE_TEST.md"
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path inside vault/, must end with .md",
                },
            },
            "required": ["path"],
        },
    )


def make_fetch_url_tool(url_guard: Optional[UrlGuard] = None) -> Tool:
    tool = make_fetch_tool(
        "fetch_url",
        _http_fetch,
        url_guard=url_guard or UrlGuard(),
        description=(
            "Fetch a public http(s) URL and return plain text (SSRF-guarded). "
            "Args: url (string)."
        ),
    )
    tool.parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "http(s) URL to fetch"},
        },
        "required": ["url"],
    }
    return tool


def build_default_harness_tools(
    *,
    memory_store: Any = None,
    vault_root: Path | str = DEFAULT_VAULT,
    url_guard: Optional[UrlGuard] = None,
) -> List[Tool]:
    tools: List[Tool] = [make_fetch_url_tool(url_guard)]
    if memory_store is not None:
        tools.append(make_memory_search_tool(memory_store))
    tools.append(make_vault_read_tool(vault_root))
    return tools
