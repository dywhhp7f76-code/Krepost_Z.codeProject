"""Общий хук записи эпизодов после query/agent — fail-open (ошибка не роняет ответ)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from krepost.memory.episodic import EpisodicMemory, SecurityVerdict

try:
    from loguru import logger
except ImportError:  # pragma: no cover
    import logging

    logger = logging.getLogger("Krepost")

_hc_store = None


def _healthclaw_enabled() -> bool:
    return os.environ.get("KREPOST_ENABLE_HEALTHCLAW", "1").lower() not in (
        "0", "false", "no", "off",
    )


def _get_hc_store():
    global _hc_store
    if _hc_store is not None:
        return _hc_store
    if not _healthclaw_enabled():
        return None
    from krepost.memory.healthclaw import InductionStore

    base = Path(os.environ.get("KREPOST_EPISODIC_DIR", "data/memory"))
    _hc_store = InductionStore(base)
    return _hc_store


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
    episode_id: Optional[str] = None
    try:
        episode_id = await episodic.add_episode(
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

    # HealthClaw induction — fail-open
    if _healthclaw_enabled():
        try:
            from krepost.memory.healthclaw import induce_after_episode

            v = await induce_after_episode(
                query=query,
                response=response or "",
                session_id=session_id,
                security_verdict=verdict,
                status=status,
                episode_id=episode_id,
                store=_get_hc_store(),
            )
            if v.disposition == "discard" and episode_id and hasattr(episodic, "delete"):
                # не удаляем автоматически в scaffold — только метка в store
                pass
            logger.debug(
                f"healthclaw disposition={v.disposition} reason={v.reason}"
            )
        except Exception as e:
            logger.warning(f"healthclaw failed: {type(e).__name__}: {e}")

    return episode_id
