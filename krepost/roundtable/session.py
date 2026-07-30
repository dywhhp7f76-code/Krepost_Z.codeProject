"""In-memory RoundTable session store."""

from __future__ import annotations

from typing import List, Optional

from krepost.roundtable.broker import DebriefBroker, RedactionError
from krepost.roundtable.mode import ModeGate, ModeSnapshot
from krepost.roundtable.schemas import (
    AttackReceipt,
    DefenseReceipt,
    MaskedUtterance,
    RoundReceipt,
    Speaker,
)


class RoundTable:
    """Air-local Round Table: receipts + masked feed + mode gate."""

    def __init__(self, gate: Optional[ModeGate] = None) -> None:
        self.gate = gate or ModeGate(attack_locked=True)
        self.broker = DebriefBroker()
        self._utterances: List[MaskedUtterance] = []
        self._attacks: List[AttackReceipt] = []
        self._defenses: List[DefenseReceipt] = []
        self._rounds: List[RoundReceipt] = []

    def mode(self) -> ModeSnapshot:
        return self.gate.snapshot()

    def add_attack_receipt(self, receipt: AttackReceipt) -> AttackReceipt:
        self._attacks.append(receipt)
        self.broker.register_ids([receipt.attack_id, receipt.envelope_ref])
        return receipt

    def add_defense_receipt(self, receipt: DefenseReceipt) -> DefenseReceipt:
        self._defenses.append(receipt)
        ids = [receipt.defense_id]
        if receipt.attack_id:
            ids.append(receipt.attack_id)
        self.broker.register_ids(ids)
        return receipt

    def add_round_receipt(self, receipt: RoundReceipt) -> RoundReceipt:
        """System-sealed round; also registers attack/defense halves."""
        self.add_attack_receipt(receipt.attack)
        self.add_defense_receipt(receipt.defense)
        self._rounds.append(receipt)
        self.broker.register_ids([receipt.round_id, receipt.input_fingerprint])
        return receipt

    def latest_round(self) -> Optional[RoundReceipt]:
        return self._rounds[-1] if self._rounds else None

    def post(
        self,
        speaker: Speaker | str,
        body: str,
        cites: Optional[List[str]] = None,
        *,
        allow_replay: bool = False,
    ) -> MaskedUtterance:
        snap = self.mode()
        sp = Speaker(speaker) if not isinstance(speaker, Speaker) else speaker
        if not snap.live_allowed and not allow_replay:
            if sp != Speaker.operator:
                raise RedactionError(
                    "combat_live_forbidden",
                    snap.reason,
                )
            raise RedactionError("combat_live_forbidden", snap.reason)

        utt = self.broker.mask(sp, body, cites)
        self._utterances.append(utt)
        return utt

    def feed(self, limit: int = 200) -> List[MaskedUtterance]:
        return list(self._utterances[-limit:])

    def receipts(self) -> dict:
        return {
            "attacks": [a.model_dump(mode="json") for a in self._attacks],
            "defenses": [d.model_dump(mode="json") for d in self._defenses],
            "rounds": [r.model_dump(mode="json") for r in self._rounds],
            "mode": self.mode().mode.value,
        }
