"""
5-level access control for Ataker-boop Planner.

Levels (по возрастанию опасности):
  L1_POISONS   (🟢 ЯДЫ)         — всегда открыт, если нет kill
  L2_CHIMERA   (🟡 ХИМЕРА)      — синтез гибридов, TOTP
  L3_CODEBREAK (🔴 КОДЫ ВЗЛОМА) — code-gen + ingestion, TOTP
  L4_AGENTS    (⚫ АГЕНТЫ)      — автономный swarm, TOTP
  L5_KILL      (🛑 KILL SWITCH) — полная блокировка, статичный пароль

Последовательная разблокировка: L3 требует L2, L4 требует L3.
L5 — исключение: доступен всегда, только блокирует (Fail-Safe Paradox).
"""
from __future__ import annotations

from enum import IntEnum, nonmember
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict, Optional, Set
import time

import pyotp


class CapabilityLevel(IntEnum):
    L1_POISONS = 1
    L2_CHIMERA = 2
    L3_CODEBREAK = 3
    L4_AGENTS = 4
    L5_KILL = 5

    #: Уровни которые разблокируются через TOTP (не L1, не L5).
    #: nonmember() marks this as a plain class attribute, not an enum member
    #: (required on Python 3.12+, otherwise the set value is passed to int()).
    UNLOCKABLE: Set["CapabilityLevel"] = nonmember(set())  # populated below


CapabilityLevel.UNLOCKABLE = {
    CapabilityLevel.L2_CHIMERA,
    CapabilityLevel.L3_CODEBREAK,
    CapabilityLevel.L4_AGENTS,
}


@dataclass
class PlannerCapabilities:
    """Текущий уровень доступа Творца. L1 всегда открыт, остальные по коду."""
    unlocked_levels: Set[CapabilityLevel] = field(
        default_factory=lambda: {CapabilityLevel.L1_POISONS}
    )
    fully_locked: bool = False  # True когда активирован L5 kill switch

    @classmethod
    def locked(cls) -> "PlannerCapabilities":
        """Только L1 открыт."""
        return cls()

    def has(self, level: CapabilityLevel) -> bool:
        """Разблокирован ли уровень и все ниже (если нет kill)."""
        if self.fully_locked:
            return False
        if level == CapabilityLevel.L5_KILL:
            return True  # kill доступен всегда (для остановки)
        return all(l in self.unlocked_levels for l in CapabilityLevel if 1 <= l <= level)


class AuthManager:
    def __init__(
        self,
        totp_secrets: Optional[Dict[CapabilityLevel, str]] = None,
        max_attempts: int = 3,
        lockout_seconds: int = 300,
    ):
        self._totp_secrets: Dict[CapabilityLevel, str] = dict(totp_secrets or {})
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._failed_attempts: Dict[CapabilityLevel, int] = defaultdict(int)
        self._lockout_until: Dict[CapabilityLevel, float] = defaultdict(float)

    @classmethod
    def from_totp_secrets(cls, secrets: Dict[CapabilityLevel, str], **kwargs) -> "AuthManager":
        return cls(totp_secrets=secrets, **kwargs)

    def set_totp_secret(self, level: CapabilityLevel, secret: str) -> None:
        if level not in CapabilityLevel.UNLOCKABLE:
            raise ValueError(f"Level {level.name} is not TOTP-unlockable")
        self._totp_secrets[level] = secret

    def is_locked_out(self, level: CapabilityLevel) -> bool:
        return time.time() < self._lockout_until[level]

    def lockout_seconds_remaining(self, level: CapabilityLevel) -> int:
        remaining = self._lockout_until[level] - time.time()
        return max(0, int(remaining))

    def verify_totp(self, level: CapabilityLevel, code: str) -> bool:
        if self.is_locked_out(level):
            return False
        secret = self._totp_secrets.get(level)
        if not secret:
            return False
        totp = pyotp.TOTP(secret, interval=30, digits=6)
        if totp.verify(code, valid_window=1):
            self._failed_attempts[level] = 0
            return True
        self._failed_attempts[level] += 1
        if self._failed_attempts[level] >= self.max_attempts:
            self._lockout_until[level] = time.time() + self.lockout_seconds
            self._failed_attempts[level] = 0
        return False
