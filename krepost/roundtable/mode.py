"""CombatMode / DebriefMode gate for Round Table."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from krepost.roundtable.schemas import TableMode


@dataclass(frozen=True)
class ModeSnapshot:
    mode: TableMode
    poison_present: bool
    attack_locked: bool
    live_allowed: bool
    reason: str


class ModeGate:
    """
    DebriefMode if poison absent OR attack locked (spec: one is enough).
    CombatMode otherwise → Round Table live posts fail-closed.
    """

    def __init__(
        self,
        *,
        poison_marker: Optional[Union[str, Path]] = None,
        attack_locked: bool = False,
    ) -> None:
        self.poison_marker = Path(poison_marker) if poison_marker else None
        self.attack_locked = bool(attack_locked)

    def set_attack_locked(self, locked: bool) -> None:
        self.attack_locked = bool(locked)

    def set_poison_marker(self, path: Optional[Union[str, Path]]) -> None:
        self.poison_marker = Path(path) if path else None

    def poison_present(self) -> bool:
        if self.poison_marker is None:
            return False
        return self.poison_marker.exists()

    def snapshot(self) -> ModeSnapshot:
        poison = self.poison_present()
        locked = self.attack_locked
        if (not poison) or locked:
            reason = []
            if not poison:
                reason.append("poison_absent")
            if locked:
                reason.append("attack_locked")
            return ModeSnapshot(
                mode=TableMode.DebriefMode,
                poison_present=poison,
                attack_locked=locked,
                live_allowed=True,
                reason="+".join(reason) or "debrief",
            )
        return ModeSnapshot(
            mode=TableMode.CombatMode,
            poison_present=poison,
            attack_locked=locked,
            live_allowed=False,
            reason="poison_present_and_attack_unlocked",
        )
