"""Общий хук записи эпизодов после query/agent — fail-open (ошибка не роняет ответ)."""
from __future__ import annotations

from typing import Any, Optional

from krepost.memory.episodic import EpisodicMemory, SecurityVerdict

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")


def _map_verdict(raw: Any) -> SecurityVerdict:
    s = str(raw or "GREEN").upper()
    if s == "RED":
        return SecurityVerdict.RED
    if s == "YELLOW":
        return SecurityVerdict.YELLOW
    return SecurityVerdict.GREEN


async def record_episode(
    episodic: Optional[EpisodicMemory],
    *,
    query: str,
    response: str,
    session_id: str,
    verdict: Any,
    status: str,
    importance: float = 0.5,
) -> Optional[str]:
    if episodic is None:
        return None
    try:
        return await episodic.add_episode(
            query=query,
            response=(response or "")[:4000],
            conversation_id=session_id,
            metadata={"status": status},
            importance_score=importance,
            security_verdict=_map_verdict(verdict),
        )
    except Exception as e:
        logger.warning(f"episodic add failed: {type(e).__name__}: {e}")
        return None
