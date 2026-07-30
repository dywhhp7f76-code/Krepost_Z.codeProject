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


class NoteChannel(str, Enum):
    private = "private"


class RoundReceiptSource(str, Enum):
    system = "system"


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


class PrivateNote(BaseModel):
    """Operator-only agent narrative — untrusted; compare to RoundReceipt."""

    round_id: str = Field(..., min_length=4, max_length=64)
    speaker: Speaker
    body: str = Field(..., min_length=1, max_length=4000)
    channel: NoteChannel = NoteChannel.private
    ts: datetime = Field(default_factory=_utcnow)


class RoundFragment(BaseModel):
    """Depersonalized round slice for Round Table (role hidden, event retained)."""

    round_id: str = Field(..., min_length=4, max_length=64)
    attack_class: AttackClass
    outcome: DefenseOutcome
    safe: Optional[SafeLevel] = None
    ts: datetime = Field(default_factory=_utcnow)


class RoundReceipt(BaseModel):
    """Machine anchor for a round — written by orchestrator, not agents."""

    round_id: str = Field(..., min_length=4, max_length=64)
    source: RoundReceiptSource = RoundReceiptSource.system
    attack: AttackReceipt
    defense: DefenseReceipt
    input_fingerprint: str = Field(..., min_length=8, max_length=128)
    judge_instability_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    judge_verdicts: List[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0, ge=0.0)
    blindness_tier: int = Field(default=0, ge=0, le=1)
    ts: datetime = Field(default_factory=_utcnow)

    @field_validator("source")
    @classmethod
    def _must_be_system(cls, v: RoundReceiptSource) -> RoundReceiptSource:
        if v != RoundReceiptSource.system:
            raise ValueError("RoundReceipt.source must be system")
        return v


class RoundMetrics(BaseModel):
    """Growth metrics — one row per round in metrics.jsonl."""

    round_id: str
    note_receipt_gap_ataker: Optional[float] = None
    note_receipt_gap_krepost: Optional[float] = None
    hypothesis_accuracy: float = 0.0
    instability_rate: float = 0.0
    pause_recommended: bool = False
    ts: datetime = Field(default_factory=_utcnow)


class SummarizerInput(BaseModel):
    """All three sources required — receipt is anchor, not optional."""

    round_receipt: RoundReceipt
    private_notes: List[PrivateNote] = Field(default_factory=list)
    public_feed: List[MaskedUtterance] = Field(default_factory=list)


class SummarizerOutput(BaseModel):
    round_id: str
    markdown: str
    metrics: RoundMetrics
    next_step: str = "Твой следующий шаг: [ ]"
