"""Build RoundReceipt from combat halves — system only, never LLM."""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional, Sequence

from krepost.roundtable.schemas import (
    AttackClass,
    AttackReceipt,
    DefenseLayer,
    DefenseOutcome,
    DefenseReceipt,
    RoundReceipt,
    SafeLevel,
)
from krepost.security.pipeline import SecurityContext


def fingerprint_input(text: str) -> str:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _id16(prefix: str = "") -> str:
    raw = secrets.token_hex(8)
    return f"{prefix}{raw}" if prefix else raw


def layer_from_violation(violation_layer: Optional[str]) -> DefenseLayer:
    if not violation_layer:
        return DefenseLayer.other
    key = violation_layer.split(":")[0].strip().lower()
    mapping = {
        "layer1": DefenseLayer.L1,
        "layer1-regex": DefenseLayer.L1,
        "l1": DefenseLayer.L1,
        "layer2": DefenseLayer.L2,
        "layer2-guard": DefenseLayer.L2,
        "l2": DefenseLayer.L2,
        "layer3": DefenseLayer.L3,
        "layer3-fewshot": DefenseLayer.L3,
        "l3": DefenseLayer.L3,
        "layer4": DefenseLayer.L4,
        "layer4-outputfilter": DefenseLayer.L4,
        "l4": DefenseLayer.L4,
        "tool_guard": DefenseLayer.tool_guard,
        "url_guard": DefenseLayer.url_guard,
        "urlguard": DefenseLayer.url_guard,
        "ingest_guard": DefenseLayer.ingest_guard,
        "rag": DefenseLayer.rag,
    }
    return mapping.get(key.replace(" ", ""), DefenseLayer.other)


def outcome_from_verdict(verdict: str, *, compromised: bool) -> DefenseOutcome:
    v = (verdict or "").upper()
    if compromised or v == "RED":
        return DefenseOutcome.BLOCK
    if v == "YELLOW":
        return DefenseOutcome.SANITIZE
    if v == "GREEN":
        return DefenseOutcome.PASS
    return DefenseOutcome.ERROR


def safe_from_verdict(verdict: str) -> SafeLevel:
    v = (verdict or "").upper()
    if v in ("GREEN", "YELLOW", "RED"):
        return SafeLevel(v)
    return SafeLevel.RED


def attack_class_from_vector(attack_vector: Optional[str]) -> AttackClass:
    text = (attack_vector or "").lower()
    if "ssrf" in text or "url" in text:
        return AttackClass.ssrf
    if "tool" in text:
        return AttackClass.tool_misuse
    if "rag" in text or "poison" in text:
        return AttackClass.rag_poisoning
    if "indirect" in text:
        return AttackClass.indirect_injection
    if "inject" in text or "prompt" in text or "jailbreak" in text:
        return AttackClass.prompt_injection
    return AttackClass.other


def defense_from_context(
    ctx: SecurityContext,
    *,
    attack_id: Optional[str] = None,
    defense_id: Optional[str] = None,
) -> DefenseReceipt:
    return DefenseReceipt(
        defense_id=defense_id or _id16("def"),
        attack_id=attack_id,
        layer=layer_from_violation(ctx.violation_layer),
        outcome=outcome_from_verdict(ctx.verdict, compromised=bool(ctx.is_compromised)),
        threat_class=attack_class_from_vector(ctx.attack_vector),
    )


def attack_stub_for_text(
    text: str,
    *,
    attack_id: Optional[str] = None,
    attack_class: AttackClass = AttackClass.other,
    envelope_ref: Optional[str] = None,
    safe: Optional[SafeLevel] = None,
) -> AttackReceipt:
    aid = (attack_id or _id16("atk")).lower()
    return AttackReceipt(
        attack_id=aid if len(aid) >= 8 else _id16("atk"),
        attack_class=attack_class,
        envelope_ref=envelope_ref or f"env_{aid[:16]}",
        safe=safe,
    )


def build_round_receipt(
    *,
    attack: AttackReceipt,
    defense: DefenseReceipt,
    input_text: str = "",
    input_fingerprint: Optional[str] = None,
    round_id: Optional[str] = None,
    judge_verdicts: Optional[Sequence[str]] = None,
    judge_instability_rate: float = 0.0,
    latency_ms: float = 0.0,
    blindness_tier: int = 0,
) -> RoundReceipt:
    """Orchestrator/pipeline writer — agents must not call this with forged source."""
    fp = input_fingerprint or fingerprint_input(input_text)
    rid = round_id or f"rnd_{attack.attack_id[:12]}"
    # Keep attack_id linkage on defense when missing
    if defense.attack_id is None:
        defense = defense.model_copy(update={"attack_id": attack.attack_id})
    return RoundReceipt(
        round_id=rid,
        attack=attack,
        defense=defense,
        input_fingerprint=fp,
        judge_verdicts=list(judge_verdicts or []),
        judge_instability_rate=float(judge_instability_rate),
        latency_ms=float(latency_ms),
        blindness_tier=int(blindness_tier),
    )


def round_receipt_from_pipeline(
    ctx: SecurityContext,
    *,
    input_text: str,
    attack: Optional[AttackReceipt] = None,
    latency_ms: float = 0.0,
    judge_verdicts: Optional[Sequence[str]] = None,
    judge_instability_rate: float = 0.0,
    blindness_tier: int = 0,
) -> RoundReceipt:
    """Seal a combat half from SecurityContext (+ optional Ataker AttackReceipt)."""
    atk = attack or attack_stub_for_text(
        input_text,
        attack_class=attack_class_from_vector(ctx.attack_vector),
        safe=safe_from_verdict(ctx.verdict),
    )
    defense = defense_from_context(ctx, attack_id=atk.attack_id)
    return build_round_receipt(
        attack=atk,
        defense=defense,
        input_text=input_text,
        latency_ms=latency_ms or float(ctx.metadata.get("total_latency_ms") or 0.0),
        judge_verdicts=judge_verdicts,
        judge_instability_rate=judge_instability_rate,
        blindness_tier=blindness_tier,
    )
