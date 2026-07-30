"""Round Table Debrief — LOCKED IDs from _handoff/ROUNDTABLE_DEBRIEF_SPEC.md."""

from krepost.roundtable.schemas import (
    AttackClass,
    AttackReceipt,
    DefenseLayer,
    DefenseOutcome,
    DefenseReceipt,
    MaskedUtterance,
    PrivateNote,
    RoundFragment,
    RoundMetrics,
    RoundReceipt,
    SafeLevel,
    Speaker,
    SummarizerInput,
    SummarizerOutput,
    TableMode,
)
from krepost.roundtable.broker import DebriefBroker, RedactionError
from krepost.roundtable.mode import ModeGate, ModeSnapshot
from krepost.roundtable.summarizer import DebriefSummarizer, SummarizerError
from krepost.roundtable.gap import (
    note_receipt_gap,
    receipt_facts_for_vault,
    hypothesis_accuracy,
)
from krepost.roundtable.receipts import (
    build_round_receipt,
    defense_from_context,
    fingerprint_input,
    round_receipt_from_pipeline,
)
from krepost.roundtable.session import RoundTable

__all__ = [
    "AttackClass",
    "AttackReceipt",
    "DefenseLayer",
    "DefenseOutcome",
    "DefenseReceipt",
    "MaskedUtterance",
    "PrivateNote",
    "RoundFragment",
    "RoundMetrics",
    "RoundReceipt",
    "SafeLevel",
    "Speaker",
    "SummarizerInput",
    "SummarizerOutput",
    "TableMode",
    "DebriefBroker",
    "RedactionError",
    "ModeGate",
    "ModeSnapshot",
    "DebriefSummarizer",
    "SummarizerError",
    "note_receipt_gap",
    "receipt_facts_for_vault",
    "hypothesis_accuracy",
    "build_round_receipt",
    "defense_from_context",
    "fingerprint_input",
    "round_receipt_from_pipeline",
    "RoundTable",
]
