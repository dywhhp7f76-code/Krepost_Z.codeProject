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
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Union

import pyotp

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_argon2 = PasswordHasher()


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




    def unlock(self, level: CapabilityLevel, code: str, auth: "AuthManager") -> bool:
        if level == CapabilityLevel.L5_KILL:
            if auth.verify_kill_password(code):
                self.activate_kill()
                return True
            return False
        if self.fully_locked:
            return False
        if level not in CapabilityLevel.UNLOCKABLE:
            return False
        if not auth.verify_totp(level, code):
            return False
        if level > CapabilityLevel.L2_CHIMERA:
            required = CapabilityLevel(level - 1)
            if required not in self.unlocked_levels:
                return False
        self.unlocked_levels.add(level)
        return True

    def activate_kill(self) -> None:
        self.fully_locked = True
        self.unlocked_levels.clear()

    def reset_kill(self, password: str, auth: "AuthManager") -> bool:
        if not auth.verify_kill_password(password):
            return False
        self.fully_locked = False
        self.unlocked_levels = {CapabilityLevel.L1_POISONS}
        return True



PathLike = Union[str, Path]

_TOTP_FILES = {
    CapabilityLevel.L2_CHIMERA: "totp_l2",
    CapabilityLevel.L3_CODEBREAK: "totp_l3",
    CapabilityLevel.L4_AGENTS: "totp_l4",
}


def _chmod_600(path: Path) -> None:
    if os.name == "posix":
        os.chmod(path, 0o600)


def generate_ingest_token() -> str:
    """Module-level convenience: generate a 32-char hex ingest token."""
    return secrets.token_hex(16)


def init_secrets_dir(secrets_dir: PathLike, kill_password: str) -> None:
    secrets_dir = Path(secrets_dir)
    secrets_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        os.chmod(secrets_dir, 0o700)

    for level, fname in _TOTP_FILES.items():
        secret = pyotp.random_base32()
        p = secrets_dir / fname
        p.write_text(secret)
        _chmod_600(p)

    kill_p = secrets_dir / "kill_password_hash"
    kill_p.write_text(_argon2.hash(kill_password))
    _chmod_600(kill_p)

    ingest_p = secrets_dir / "ingest_token"
    ingest_p.write_text(generate_ingest_token())
    _chmod_600(ingest_p)

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
        self._kill_hash: Optional[str] = None
        self._ingest_token: Optional[str] = None
        self._ingest_failed: int = 0
        self._ingest_lockout_until: float = 0.0

    @classmethod
    def from_totp_secrets(cls, secrets: Dict[CapabilityLevel, str], **kwargs) -> "AuthManager":
        return cls(totp_secrets=secrets, **kwargs)

    @classmethod
    def from_secrets_dir(cls, secrets_dir: PathLike) -> "AuthManager":
        secrets_dir = Path(secrets_dir)
        totp_secrets: Dict[CapabilityLevel, str] = {}
        for level, fname in _TOTP_FILES.items():
            p = secrets_dir / fname
            if p.is_file():
                totp_secrets[level] = p.read_text().strip()
        auth = cls(totp_secrets=totp_secrets)
        kill_p = secrets_dir / "kill_password_hash"
        if kill_p.is_file():
            auth._kill_hash = kill_p.read_text().strip()
        ingest_p = secrets_dir / "ingest_token"
        if ingest_p.is_file():
            auth._ingest_token = ingest_p.read_text().strip()
        return auth


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

    def set_kill_password(self, password: str) -> None:
        self._kill_hash = _argon2.hash(password)

    def verify_kill_password(self, password: str) -> bool:
        if not self._kill_hash:
            return False
        try:
            _argon2.verify(self._kill_hash, password)
            return True
        except VerifyMismatchError:
            return False

    def has_kill_password(self) -> bool:
        return self._kill_hash is not None

    def generate_ingest_token(self) -> str:
        """Создать и сохранить 32-char hex ingest token."""
        token = secrets.token_hex(16)  # 32 hex chars
        self._ingest_token = token
        return token

    def set_ingest_token(self, token: str) -> None:
        self._ingest_token = token

    def verify_ingest_token(self, token: str) -> bool:
        if time.time() < self._ingest_lockout_until:
            return False
        if not self._ingest_token:
            return False
        if secrets.compare_digest(self._ingest_token, token):
            self._ingest_failed = 0
            return True
        self._ingest_failed += 1
        if self._ingest_failed >= self.max_attempts:
            self._ingest_lockout_until = time.time() + self.lockout_seconds
            self._ingest_failed = 0
        return False

    def has_ingest_token(self) -> bool:
        return self._ingest_token is not None








def _totp_uri(secret: str, level: CapabilityLevel) -> str:
    label = f"Ataker-boop:{level.name}"
    return pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name="Ataker-boop")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="ataker.auth")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--dir", default=os.path.expanduser("~/.ataker"))
    p_init.add_argument("--kill-password", default=None)
    args = parser.parse_args()

    if args.cmd == "init":
        kill_pw = args.kill_password
        if kill_pw is None:
            kill_pw = input("\u0412\u0432\u0435\u0434\u0438\u0442\u0435 KILL PASSWORD (L5): ").strip()
            if not kill_pw:
                print("\u041e\u0448\u0438\u0431\u043a\u0430: kill password \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043f\u0443\u0441\u0442\u044b\u043c", file=sys.stderr)
                sys.exit(1)

        init_secrets_dir(args.dir, kill_pw)
        print(f"\u2713 \u0421\u0435\u043a\u0440\u0435\u0442\u044b \u0441\u043e\u0437\u0434\u0430\u043d\u044b \u0432 {args.dir}")
        print()
        print("=== TOTP QR-\u043a\u043e\u0434\u044b ===")
        for level, fname in _TOTP_FILES.items():
            secret = (Path(args.dir) / fname).read_text().strip()
            uri = _totp_uri(secret, level)
            print()
            print(f"[{level.name}]")
            print(f"  {uri}")
        ingest = (Path(args.dir) / "ingest_token").read_text().strip()
        print()
        print("=== Ingest token ===")
        print(f"  {ingest}")
        print()
        print("\u26a0\ufe0f  \u0421\u041e\u0425\u0420\u0410\u041d\u0418 KILL PASSWORD \u0412 \u041d\u0410\u0414\u0415\u0416\u041d\u041e\u0415 \u041c\u0415\u0421\u0422\u041e.")


if __name__ == "__main__":
    main()
