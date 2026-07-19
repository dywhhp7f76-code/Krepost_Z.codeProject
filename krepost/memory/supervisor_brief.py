"""
Supervisor пишет SearchBrief (HierarchicalDomainRAG Phase 4).

Main LLM → JSON SearchBrief. Domains только из shortlist DomainRouter.
Fail-open → heuristic draft_search_brief.
"""
from __future__ import annotations

import json
import re
from typing import Any, List, Optional, Sequence

from krepost.memory.hierarchical_rag import draft_search_brief
from krepost.memory.search_brief import SearchBrief

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")

_BRIEF_SYSTEM = (
    "Ты — Supervisor Крепости. Пишешь SearchBrief для DomainScout[]. "
    "НЕ отвечай пользователю. Верни ТОЛЬКО JSON-объект:\n"
    '{"query_anchors":["..."],"domains":["domain_id",...],"round":0}\n'
    "Правила:\n"
    "- query_anchors: 2..8 коротких якорей (слова/фразы) для поиска по vault;\n"
    "- domains: ТОЛЬКО из списка ALLOWED_DOMAINS (1..K), не выдумывай id;\n"
    "- round: целое >= 0;\n"
    "- без markdown, без пояснений."
)

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        m = _JSON_RE.search(text)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None


def _clamp_domains(
    requested: Sequence[str],
    allowed: Sequence[str],
) -> List[str]:
    allow = {d for d in allowed if d}
    out: List[str] = []
    for d in requested:
        d = str(d).strip()
        if d in allow and d not in out:
            out.append(d)
    if not out:
        out = list(allowed)[:3] if allowed else []
    return out


class SupervisorBriefDrafter:
    """Supervisor (main LLM) → SearchBrief. Нужен backend с .generate()."""

    def __init__(
        self,
        backend: Any,
        *,
        max_anchors: int = 8,
    ):
        self.backend = backend
        self.max_anchors = max_anchors
        self.last_source: str = "none"  # llm | heuristic | refine_llm | refine_heuristic

    async def draft(
        self,
        user_query: str,
        allowed_domains: Sequence[str],
        *,
        round: int = 0,
        previous: Optional[SearchBrief] = None,
        grade_note: str = "",
        missing_anchors: Optional[Sequence[str]] = None,
        ctx: Any = None,
    ) -> SearchBrief:
        allowed = [d for d in allowed_domains if d]
        heuristic = draft_search_brief(
            user_query, list(allowed), max_anchors=self.max_anchors
        )
        if previous is not None:
            # refine: стартуем с прошлого brief
            heuristic = SearchBrief(
                query_anchors=list(previous.query_anchors),
                domains=list(previous.domains) or list(allowed),
                round=round,
                user_query=user_query,
            )
            for m in missing_anchors or []:
                if m and m not in heuristic.query_anchors:
                    heuristic.query_anchors.append(m)

        if self.backend is None:
            self.last_source = "refine_heuristic" if previous else "heuristic"
            return heuristic

        user_block = (
            f"USER_QUERY:\n{user_query}\n\n"
            f"ALLOWED_DOMAINS:\n{json.dumps(allowed, ensure_ascii=False)}\n"
            f"ROUND: {round}\n"
        )
        if previous is not None:
            prev_payload = {
                "query_anchors": previous.query_anchors,
                "domains": previous.domains,
                "round": previous.round,
            }
            user_block += (
                "PREVIOUS_BRIEF:\n"
                f"{json.dumps(prev_payload, ensure_ascii=False)}\n"
                f"GRADE_NOTE: {grade_note}\n"
                "MISSING_ANCHORS: "
                f"{json.dumps(list(missing_anchors or []), ensure_ascii=False)}\n"
                "Уточни SearchBrief (добавь якоря / поправь domains из ALLOWED).\n"
            )
        else:
            user_block += "Составь SearchBrief.\n"

        messages = [
            {"role": "system", "content": _BRIEF_SYSTEM},
            {"role": "user", "content": user_block},
        ]
        try:
            text = await self.backend.generate(
                user_query, ctx, messages=messages
            )
            obj = _extract_json(text or "")
            if not obj:
                raise ValueError("no json in supervisor brief")
            anchors = obj.get("query_anchors") or obj.get("anchors") or []
            if not isinstance(anchors, list):
                anchors = [str(anchors)]
            anchors = [str(a).strip() for a in anchors if str(a).strip()]
            anchors = anchors[: self.max_anchors]
            if not anchors:
                anchors = list(heuristic.query_anchors)
            domains = _clamp_domains(obj.get("domains") or [], allowed)
            if not domains:
                domains = list(heuristic.domains)
            brief = SearchBrief(
                query_anchors=anchors,
                domains=domains,
                round=int(obj.get("round", round) or round),
                user_query=user_query,
            )
            self.last_source = "refine_llm" if previous else "llm"
            return brief
        except Exception as e:
            logger.warning(
                f"Supervisor SearchBrief failed — heuristic: "
                f"{type(e).__name__}: {e}"
            )
            self.last_source = "refine_heuristic" if previous else "heuristic"
            return heuristic
