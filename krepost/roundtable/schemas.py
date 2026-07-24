"""Round Table schemas — LOCKED contract (_handoff/ROUNDTABLE_DEBRIEF_SPEC.md)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AttackClass(str, Enum):
    prompt_injection = "prompt_injection"
    indirect_injection = "indirect_injection"
    rag_poisoning = "rag_poisoning"
    tool_misuse = "tool_misuse"
    ssrf = "ssrf"
    other = "other"


class DefenseLayer(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    tool_guard = "tool_guard"
    url_guard = "url_guard"
    ingest_guard = "ingest_guard"
    rag = "rag"
    other = "other"


class DefenseOutcome(str, Enum):
    BLOCK = "BLOCK"
    PASS = "PASS"
    SANITIZE = "SANITIZE"
    QUARANTINE = "QUARANTINE"
    ERROR = "ERROR"


class SafeLevel(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class Speaker(str, Enum):
    ataker = "ataker"
    krepost = "krepost"
    operator = "operator"


class TableMode(str, Enum):
    CombatMode = "CombatMode"
    DebriefMode = "DebriefMode"


class AttackReceipt(BaseModel):
    attack_id: str = Field(..., min_length=8, max_length=64)
    attack_class: AttackClass
    useful: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    correct: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    safe: Optional[SafeLevel] = None
    ts: datetime = Field(default_factory=_utcnow)
    envelope_ref: str = Field(..., min_length=1, max_length=128)

    @field_validator("attack_id")
    @classmethod
    def _hexish(cls, v: str) -> str:
        return v.strip().lower()


class DefenseReceipt(BaseModel):
    defense_id: str = Field(..., min_length=8, max_length=64)
    attack_id: Optional[str] = Field(default=None, max_length=64)
    layer: DefenseLayer
    outcome: DefenseOutcome
    threat_class: Optional[AttackClass] = None
    ts: datetime = Field(default_factory=_utcnow)


class MaskedUtterance(BaseModel):
    speaker: Speaker
    body: str = Field(..., min_length=1, max_length=2000)
    cites: List[str] = Field(default_factory=list)
    ts: datetime = Field(default_factory=_utcnow)
    redaction_flags: List[str] = Field(default_factory=list)
