"""SealedEnvelope + AttackReceipt helpers for Ataker (Air-local)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Keep Ataker independent of krepost import for envelope storage.
# Receipt JSON shape matches krepost.roundtable.schemas.AttackReceipt.


def attack_id_for(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class SealedEnvelope:
    """Local-only sealed attack payload (never cross to Studio / RoundTable body)."""

    envelope_ref: str
    attack_id: str
    payload: str
    attack_class: str = "other"
    meta: Optional[Dict[str, Any]] = None
    ts: str = ""

    def __post_init__(self) -> None:
        if not self.ts:
            self.ts = datetime.now(timezone.utc).isoformat()


class SealedStore:
    """Filesystem store under data/ataker_sandbox/envelopes/ (or custom root)."""

    def __init__(self, root: Union[str, Path]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def seal(
        self,
        payload: str,
        *,
        attack_class: str = "other",
        meta: Optional[Dict[str, Any]] = None,
    ) -> SealedEnvelope:
        aid = attack_id_for(payload)
        ref = f"env_{aid}"
        env = SealedEnvelope(
            envelope_ref=ref,
            attack_id=aid,
            payload=payload,
            attack_class=attack_class,
            meta=meta or {},
        )
        path = self.root / f"{ref}.json"
        path.write_text(
            json.dumps(asdict(env), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return env

    def open(self, envelope_ref: str) -> SealedEnvelope:
        path = self.root / f"{envelope_ref}.json"
        if not path.is_file():
            raise FileNotFoundError(envelope_ref)
        data = json.loads(path.read_text(encoding="utf-8"))
        return SealedEnvelope(**data)

    def to_attack_receipt(
        self,
        env: SealedEnvelope,
        *,
        useful: Optional[float] = None,
        correct: Optional[float] = None,
        safe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Broker-safe receipt dict (no payload)."""
        return {
            "attack_id": env.attack_id,
            "attack_class": env.attack_class,
            "useful": useful,
            "correct": correct,
            "safe": safe,
            "ts": env.ts,
            "envelope_ref": env.envelope_ref,
        }
