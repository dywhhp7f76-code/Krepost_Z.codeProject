# Auth & 5-Level Access Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 5-level access control system (L1-Яды / L2-Химера / L3-Коды / L4-Агенты / L5-KILL) for Ataker-boop, with TOTP-based unlock for L2-L4, a static operator-set kill password for L5, and a separate long-lived ingestion token.

**Architecture:** `PlannerCapabilities` holds the mutable unlock state (which levels are active, kill flag). `AuthManager` verifies TOTP codes per-level with brute-force lockout, and verifies the kill password via argon2id. Both live in `ataker/auth.py`. Secrets are stored as chmod 600 files under `~/.ataker/`.

**Tech Stack:** Python ≥3.10, `pyotp` (TOTP RFC 6238), `argon2-cffi` (password hashing), `pytest` + `pytest-asyncio` (already in dev deps).

## Global Constraints

- Python ≥3.10 (existing project floor, `pyproject.toml`)
- Tests live in `Ataker-boop/tests/`, follow existing `test_ataker.py` patterns (plain `pytest`, `asyncio_mode = "auto"`)
- Every secret file: **chmod 600**, owner `$USER`, **never in git** (already covered by existing `.gitignore` patterns via `*.env` and new `~/.ataker/` outside repo)
- `pyotp` and `argon2-cffi` must be added to `pyproject.toml` under a new `[planner]` optional dependency group
- Existing `ataker/__init__.py` exports must NOT be removed — only appended to
- Do NOT touch `ataker/generator.py`, `mutations.py`, `vault.py`, `red_team_loop.py`, `success_analyzer.py`, `benchmark_catalog.py`, `evals_ucs.py`, `tests/test_ataker.py`
- L5 (kill password) is **static, operator-set, argon2id-hashed** — NOT TOTP. Reason: must work without phone, fail-safe paradox (code can only kill, never unlock).
- Sequential unlock: L3 requires L2 active, L4 requires L3 active. L5 is exempt (can fire anytime).

---

## File Structure

| File | Responsibility |
|------|----------------|
| `Ataker-boop/ataker/auth.py` | `CapabilityLevel` enum, `PlannerCapabilities` state, `AuthManager` (TOTP + kill password + ingest token + lockout). ~180 lines. |
| `Ataker-boop/tests/test_auth.py` | All tests for auth subsystem. ~300 lines. |
| `Ataker-boop/pyproject.toml` | Add `[planner]` optional deps with `pyotp`, `argon2-cffi`. |

**Interfaces produced (consumed by later subsystems):**
- `CapabilityLevel(IntEnum)` — L1_POISONS=1, L2_CHIMERA=2, L3_CODEBREAK=3, L4_AGENTS=4, L5_KILL=5
- `PlannerCapabilities` — `.locked()`, `.has(level)`, `.unlock(level, code, auth)`, `.activate_kill()`, `.reset_kill(code, auth)`, `.fully_locked`
- `AuthManager` — `.verify_totp(level, code)`, `.verify_ingest_token(token)`, `.verify_kill_password(pw)`, `.is_locked_out(level)`, `.set_kill_password(pw)`, `.from_secrets_dir(path)`
- `verify_ingest_token(token, path)` — module-level convenience

---

### Task 1: Add `[planner]` optional dependencies to pyproject.toml

**Files:**
- Modify: `Ataker-boop/pyproject.toml`

**Interfaces:**
- Produces: installable deps `pyotp`, `argon2-cffi`, `pyyaml`, `chromadb`, `sentence-transformers`, `openai` under `[planner]` extra

- [ ] **Step 1: Edit pyproject.toml to add planner extra**

Open `Ataker-boop/pyproject.toml`. After the existing `[project.optional-dependencies]` block (which has `llm`, `full`, `dev`), add a new `planner` entry. The full block should read:

```toml
[project.optional-dependencies]
llm = ["openai"]
full = ["openai", "chromadb"]
dev = ["pytest", "pytest-asyncio"]
planner = [
    "openai",
    "chromadb",
    "sentence-transformers",
    "pyotp>=2.9",
    "argon2-cffi>=23.1",
    "pyyaml>=6.0",
]
```

- [ ] **Step 2: Install the new deps**

Run: `cd Ataker-boop && pip install -e ".[planner,dev]"`
Expected: installs `pyotp`, `argon2-cffi`, `pyyaml` plus existing. No errors.

- [ ] **Step 3: Verify imports work**

Run: `python -c "import pyotp, argon2, yaml; print(pyotp.__version__, argon2.__version__, yaml.__version__)"`
Expected: prints three version numbers, no ImportError.

- [ ] **Step 4: Commit**

```bash
git add Ataker-boop/pyproject.toml
git commit -m "deps(ataker): add [planner] extra with pyotp, argon2-cffi, pyyaml"
```

---

### Task 2: Define `CapabilityLevel` enum

**Files:**
- Create: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Produces: `CapabilityLevel(IntEnum)` with 5 members and `UNLOCKABLE` set (L2-L4 only)

- [ ] **Step 1: Write the failing test**

Create `Ataker-boop/tests/test_auth.py`:

```python
"""Tests for ataker.auth — 5-level access control."""
from __future__ import annotations

import pytest

from ataker.auth import CapabilityLevel


class TestCapabilityLevel:
    def test_has_five_levels(self):
        levels = list(CapabilityLevel)
        assert len(levels) == 5

    def test_level_values_are_sequential(self):
        values = [l.value for l in CapabilityLevel]
        assert values == [1, 2, 3, 4, 5]

    def test_level_names_match_spec(self):
        assert CapabilityLevel.L1_POISONS.value == 1
        assert CapabilityLevel.L2_CHIMERA.value == 2
        assert CapabilityLevel.L3_CODEBREAK.value == 3
        assert CapabilityLevel.L4_AGENTS.value == 4
        assert CapabilityLevel.L5_KILL.value == 5

    def test_unlockable_excludes_l1_and_l5(self):
        """L1 always open, L5 is kill (different mechanism)."""
        assert CapabilityLevel.L1_POISONS not in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L5_KILL not in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L2_CHIMERA in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L3_CODEBREAK in CapabilityLevel.UNLOCKABLE
        assert CapabilityLevel.L4_AGENTS in CapabilityLevel.UNLOCKABLE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestCapabilityLevel -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ataker.auth'`

- [ ] **Step 3: Write minimal implementation**

Create `Ataker-boop/ataker/auth.py`:

```python
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

from enum import IntEnum
from typing import Set


class CapabilityLevel(IntEnum):
    L1_POISONS = 1
    L2_CHIMERA = 2
    L3_CODEBREAK = 3
    L4_AGENTS = 4
    L5_KILL = 5

    #: Уровни которые разблокируются через TOTP (не L1, не L5).
    UNLOCKABLE: Set["CapabilityLevel"] = set()  # populated below


CapabilityLevel.UNLOCKABLE = {
    CapabilityLevel.L2_CHIMERA,
    CapabilityLevel.L3_CODEBREAK,
    CapabilityLevel.L4_AGENTS,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestCapabilityLevel -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): add CapabilityLevel enum (5 levels)"
```

---

### Task 3: `PlannerCapabilities` — locked state and `has()` check

**Files:**
- Modify: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Consumes: `CapabilityLevel` (Task 2)
- Produces: `PlannerCapabilities` with `.locked()`, `.has(level)`, `.fully_locked`, `.unlocked_levels`

- [ ] **Step 1: Write the failing tests**

Append to `Ataker-boop/tests/test_auth.py`:

```python
from ataker.auth import PlannerCapabilities


class TestPlannerCapabilitiesLocked:
    def test_locked_factory_has_only_l1(self):
        caps = PlannerCapabilities.locked()
        assert caps.has(CapabilityLevel.L1_POISONS) is True
        assert caps.has(CapabilityLevel.L2_CHIMERA) is False
        assert caps.has(CapabilityLevel.L3_CODEBREAK) is False
        assert caps.has(CapabilityLevel.L4_AGENTS) is False

    def test_has_requires_all_lower_levels(self):
        """L3 требует L2 — если L2 не открыт, L3 тоже False."""
        caps = PlannerCapabilities.locked()
        caps.unlocked_levels.add(CapabilityLevel.L3_CODEBREAK)
        # L2 не открыт → L3 has() должен вернуть False
        assert caps.has(CapabilityLevel.L3_CODEBREAK) is False

    def test_has_l3_true_when_l2_also_unlocked(self):
        caps = PlannerCapabilities.locked()
        caps.unlocked_levels.add(CapabilityLevel.L2_CHIMERA)
        caps.unlocked_levels.add(CapabilityLevel.L3_CODEBREAK)
        assert caps.has(CapabilityLevel.L3_CODEBREAK) is True

    def test_fully_locked_blocks_even_l1(self):
        """Kill switch блокирует даже L1."""
        caps = PlannerCapabilities.locked()
        caps.fully_locked = True
        assert caps.has(CapabilityLevel.L1_POISONS) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestPlannerCapabilitiesLocked -v`
Expected: FAIL with `ImportError: cannot import name 'PlannerCapabilities'`

- [ ] **Step 3: Write minimal implementation**

Append to `Ataker-boop/ataker/auth.py` (after the `CapabilityLevel.UNLOCKABLE` assignment):

```python
from dataclasses import dataclass, field
from typing import Set


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestPlannerCapabilitiesLocked -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): PlannerCapabilities locked state + has()"
```

---

### Task 4: `AuthManager.verify_totp()` — valid and invalid codes

**Files:**
- Modify: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Consumes: `CapabilityLevel` (Task 2)
- Produces: `AuthManager` with `.verify_totp(level, code)`, `.from_totp_secrets(secrets_dict)` classmethod

- [ ] **Step 1: Write the failing tests**

Append to `Ataker-boop/tests/test_auth.py`:

```python
import pyotp

from ataker.auth import AuthManager


def _make_auth_with_secret(level: CapabilityLevel, secret: str) -> AuthManager:
    """Helper: AuthManager with one level's TOTP secret set."""
    return AuthManager.from_totp_secrets({level: secret})


class TestAuthManagerTOTP:
    def test_valid_totp_passes(self):
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, secret)
        valid_code = pyotp.TOTP(secret).now()

        assert auth.verify_totp(CapabilityLevel.L2_CHIMERA, valid_code) is True

    def test_invalid_totp_fails(self):
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, secret)

        assert auth.verify_totp(CapabilityLevel.L2_CHIMERA, "000000") is False

    def test_accepts_previous_window_code(self):
        """±30s clock drift — valid_window=1."""
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L3_CODEBREAK, secret)
        # код из предыдущего 30-сек окна
        prev_code = pyotp.TOTP(secret).at(__import__("time").time() - 30)

        assert auth.verify_totp(CapabilityLevel.L3_CODEBREAK, prev_code) is True

    def test_unknown_level_secret_fails(self):
        """Уровень без секрета → всегда False."""
        auth = AuthManager.from_totp_secrets({})  # пусто
        assert auth.verify_totp(CapabilityLevel.L2_CHIMERA, "123456") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestAuthManagerTOTP -v`
Expected: FAIL with `ImportError: cannot import name 'AuthManager'`

- [ ] **Step 3: Write minimal implementation**

Append to `Ataker-boop/ataker/auth.py`:

```python
import pyotp
from typing import Dict, Optional


class AuthManager:
    """TOTP-проверка для L2-L4 + kill password для L5 + ingest token.

    Каждый уровень — отдельный secret (утечка одного не ломает другие).
    """

    def __init__(
        self,
        totp_secrets: Optional[Dict[CapabilityLevel, str]] = None,
    ):
        self._totp_secrets: Dict[CapabilityLevel, str] = dict(totp_secrets or {})

    @classmethod
    def from_totp_secrets(cls, secrets: Dict[CapabilityLevel, str]) -> "AuthManager":
        """Создать AuthManager со словарём level→base32-secret."""
        return cls(totp_secrets=secrets)

    def set_totp_secret(self, level: CapabilityLevel, secret: str) -> None:
        if level not in CapabilityLevel.UNLOCKABLE:
            raise ValueError(f"Level {level.name} is not TOTP-unlockable")
        self._totp_secrets[level] = secret

    def verify_totp(self, level: CapabilityLevel, code: str) -> bool:
        """Проверить TOTP-код для уровня. ±30s drift принимается."""
        secret = self._totp_secrets.get(level)
        if not secret:
            return False
        totp = pyotp.TOTP(secret, interval=30, digits=6)
        return totp.verify(code, valid_window=1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestAuthManagerTOTP -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): AuthManager.verify_totp with ±30s drift"
```

---

### Task 5: Brute-force lockout (3 attempts → 5 min)

**Files:**
- Modify: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Produces: `.is_locked_out(level)`, `.lockout_seconds_remaining(level)`, attributes `max_attempts`, `lockout_seconds`

- [ ] **Step 1: Write the failing tests**

Append to `Ataker-boop/tests/test_auth.py`:

```python
class TestAuthManagerLockout:
    def test_three_failures_trigger_lockout(self):
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, secret)
        auth.max_attempts = 3
        auth.lockout_seconds = 300

        for _ in range(3):
            auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")

        assert auth.is_locked_out(CapabilityLevel.L2_CHIMERA) is True

    def test_lockout_rejects_even_valid_code(self):
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, secret)
        auth.max_attempts = 3

        for _ in range(3):
            auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")

        valid_code = pyotp.TOTP(secret).now()
        assert auth.verify_totp(CapabilityLevel.L2_CHIMERA, valid_code) is False

    def test_lockout_is_per_level(self):
        """Lockout L2 не блокирует L3."""
        auth = AuthManager.from_totp_secrets({
            CapabilityLevel.L2_CHIMERA: pyotp.random_base32(),
            CapabilityLevel.L3_CODEBREAK: pyotp.random_base32(),
        })
        auth.max_attempts = 2

        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")
        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")

        assert auth.is_locked_out(CapabilityLevel.L2_CHIMERA) is True
        assert auth.is_locked_out(CapabilityLevel.L3_CODEBREAK) is False

    def test_valid_code_resets_attempt_counter(self):
        """Удачный ввод сбрасывает счётчик неудач."""
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, secret)
        auth.max_attempts = 3

        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")  # 1
        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")  # 2
        auth.verify_totp(CapabilityLevel.L2_CHIMERA, pyotp.TOTP(secret).now())  # reset
        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")  # 1 again

        assert auth.is_locked_out(CapabilityLevel.L2_CHIMERA) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestAuthManagerLockout -v`
Expected: FAIL with `AttributeError: 'AuthManager' object has no attribute 'is_locked_out'`

- [ ] **Step 3: Write minimal implementation**

Modify `AuthManager.__init__` and add lockout methods. Replace the existing `__init__` and `verify_totp`:

```python
import time
from collections import defaultdict


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestAuthManagerLockout -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): brute-force lockout (3 attempts → 5 min, per-level)"
```

---

### Task 6: Kill password (argon2id) — set, verify, Fail-Safe Paradox

**Files:**
- Modify: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Produces: `.set_kill_password(password)`, `.verify_kill_password(password)`, `.has_kill_password()`

- [ ] **Step 1: Write the failing tests**

Append to `Ataker-boop/tests/test_auth.py`:

```python
class TestAuthManagerKillPassword:
    def test_set_and_verify_kill_password(self):
        auth = AuthManager()
        auth.set_kill_password("Hervam_Secret_2026!")

        assert auth.verify_kill_password("Hervam_Secret_2026!") is True

    def test_wrong_kill_password_fails(self):
        auth = AuthManager()
        auth.set_kill_password("correct")

        assert auth.verify_kill_password("wrong") is False

    def test_no_kill_password_set_fails(self):
        auth = AuthManager()
        assert auth.verify_kill_password("anything") is False

    def test_kill_password_is_hashed_not_plain(self):
        """В памяти не должен храниться plain-text пароль."""
        auth = AuthManager()
        auth.set_kill_password("my_secret")

        # _kill_hash хранится, не plain
        assert hasattr(auth, "_kill_hash")
        assert auth._kill_hash is not None
        assert "my_secret" not in auth._kill_hash

    def test_has_kill_password_flag(self):
        auth = AuthManager()
        assert auth.has_kill_password() is False
        auth.set_kill_password("x")
        assert auth.has_kill_password() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestAuthManagerKillPassword -v`
Expected: FAIL with `AttributeError: 'AuthManager' object has no attribute 'set_kill_password'`

- [ ] **Step 3: Write minimal implementation**

Add `argon2` import at top of `ataker/auth.py` and extend `AuthManager`:

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_argon2 = PasswordHasher()  # default params: argon2id, memory=65536 KiB, time=3


class AuthManager:
    # ... existing __init__ ...

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

    # ... existing totp methods ...

    def set_kill_password(self, password: str) -> None:
        """Hash и сохранить kill password (L5). Никогда не хранить plain."""
        self._kill_hash = _argon2.hash(password)

    def verify_kill_password(self, password: str) -> bool:
        """Constant-time проверка kill password. False если не задан."""
        if not self._kill_hash:
            return False
        try:
            _argon2.verify(self._kill_hash, password)
            return True
        except VerifyMismatchError:
            return False

    def has_kill_password(self) -> bool:
        return self._kill_hash is not None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestAuthManagerKillPassword -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): kill password via argon2id (Fail-Safe Paradox)"
```

---

### Task 7: Ingestion token (long-lived, constant-time compare)

**Files:**
- Modify: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Produces: `.set_ingest_token(token)`, `.verify_ingest_token(token)`, `.has_ingest_token()`, module-level `generate_ingest_token()`

- [ ] **Step 1: Write the failing tests**

Append to `Ataker-boop/tests/test_auth.py`:

```python
from ataker.auth import generate_ingest_token


class TestIngestToken:
    def test_generate_returns_32_hex(self):
        token = generate_ingest_token()
        assert len(token) == 32
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_is_random(self):
        a = generate_ingest_token()
        b = generate_ingest_token()
        assert a != b

    def test_set_and_verify_token(self):
        auth = AuthManager()
        auth.set_ingest_token("abc123" * 5 + "ab")  # 32 chars

        assert auth.verify_ingest_token("abc123" * 5 + "ab") is True

    def test_wrong_token_fails(self):
        auth = AuthManager()
        auth.set_ingest_token("a" * 32)

        assert auth.verify_ingest_token("b" * 32) is False

    def test_no_token_set_fails(self):
        auth = AuthManager()
        assert auth.verify_ingest_token("anything") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestIngestToken -v`
Expected: FAIL with `ImportError: cannot import name 'generate_ingest_token'`

- [ ] **Step 3: Write minimal implementation**

Add to top of `ataker/auth.py`:

```python
import secrets as _secrets
```

Extend `AuthManager.__init__` (add `self._ingest_token: Optional[str] = None`) and add methods:

```python
def generate_ingest_token() -> str:
    """Сгенерировать новый 32-char hex ingest token."""
    return _secrets.token_hex(16)


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

    # ... existing methods ...

    def set_ingest_token(self, token: str) -> None:
        self._ingest_token = token

    def verify_ingest_token(self, token: str) -> bool:
        """Constant-time сравнение ingest token."""
        if not self._ingest_token:
            return False
        return _secrets.compare_digest(self._ingest_token, token)

    def has_ingest_token(self) -> bool:
        return self._ingest_token is not None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestIngestToken -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): ingestion token (long-lived, constant-time)"
```

---

### Task 8: `PlannerCapabilities.unlock()` — sequential unlock + kill activation

**Files:**
- Modify: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Consumes: `AuthManager.verify_totp`, `AuthManager.verify_kill_password` (Tasks 4, 6)
- Produces: `PlannerCapabilities.unlock(level, code, auth)`, `.activate_kill()`, `.reset_kill(password, auth)`

- [ ] **Step 1: Write the failing tests**

Append to `Ataker-boop/tests/test_auth.py`:

```python
class TestPlannerCapabilitiesUnlock:
    def _auth_with_l2(self):
        secret = pyotp.random_base32()
        auth = AuthManager.from_totp_secrets({CapabilityLevel.L2_CHIMERA: secret})
        return auth, secret

    def test_unlock_l2_with_valid_totp(self):
        auth, secret = self._auth_with_l2()
        caps = PlannerCapabilities.locked()
        code = pyotp.TOTP(secret).now()

        assert caps.unlock(CapabilityLevel.L2_CHIMERA, code, auth) is True
        assert caps.has(CapabilityLevel.L2_CHIMERA) is True

    def test_unlock_l2_with_invalid_totp_fails(self):
        auth, _ = self._auth_with_l2()
        caps = PlannerCapabilities.locked()

        assert caps.unlock(CapabilityLevel.L2_CHIMERA, "000000", auth) is False
        assert caps.has(CapabilityLevel.L2_CHIMERA) is False

    def test_unlock_l3_requires_l2_first(self):
        """L3 без L2 → reject (sequential unlock)."""
        l3_secret = pyotp.random_base32()
        auth = AuthManager.from_totp_secrets({CapabilityLevel.L3_CODEBREAK: l3_secret})
        caps = PlannerCapabilities.locked()
        code = pyotp.TOTP(l3_secret).now()

        assert caps.unlock(CapabilityLevel.L3_CODEBREAK, code, auth) is False

    def test_unlock_l3_after_l2_succeeds(self):
        l2_secret = pyotp.random_base32()
        l3_secret = pyotp.random_base32()
        auth = AuthManager.from_totp_secrets({
            CapabilityLevel.L2_CHIMERA: l2_secret,
            CapabilityLevel.L3_CODEBREAK: l3_secret,
        })
        caps = PlannerCapabilities.locked()

        caps.unlock(CapabilityLevel.L2_CHIMERA, pyotp.TOTP(l2_secret).now(), auth)
        assert caps.unlock(CapabilityLevel.L3_CODEBREAK, pyotp.TOTP(l3_secret).now(), auth) is True

    def test_unlock_l5_with_kill_password_activates_kill(self):
        auth = AuthManager()
        auth.set_kill_password("Hervam_Kill_2026!")
        caps = PlannerCapabilities.locked()

        result = caps.unlock(CapabilityLevel.L5_KILL, "Hervam_Kill_2026!", auth)
        assert result is True
        assert caps.fully_locked is True
        # L1 теперь тоже заблокирован
        assert caps.has(CapabilityLevel.L1_POISONS) is False

    def test_unlock_l5_wrong_password_no_effect(self):
        auth = AuthManager()
        auth.set_kill_password("correct")
        caps = PlannerCapabilities.locked()

        result = caps.unlock(CapabilityLevel.L5_KILL, "wrong", auth)
        assert result is False
        assert caps.fully_locked is False
        assert caps.has(CapabilityLevel.L1_POISONS) is True

    def test_unlock_blocked_when_fully_locked(self):
        """При активном kill нельзя разблокировать L2-L4."""
        auth = AuthManager()
        auth.set_totp_secret(CapabilityLevel.L2_CHIMERA, pyotp.random_base32())
        caps = PlannerCapabilities.locked()
        caps.fully_locked = True

        secret = auth._totp_secrets[CapabilityLevel.L2_CHIMERA]
        code = pyotp.TOTP(secret).now()
        assert caps.unlock(CapabilityLevel.L2_CHIMERA, code, auth) is False

    def test_reset_kill_requires_password(self):
        auth = AuthManager()
        auth.set_kill_password("secret")
        caps = PlannerCapabilities.locked()
        caps.activate_kill()

        assert caps.reset_kill("wrong", auth) is False
        assert caps.fully_locked is True
        assert caps.reset_kill("secret", auth) is True
        assert caps.fully_locked is False
        # После reset L2-L4 остались заблокированы
        assert caps.has(CapabilityLevel.L2_CHIMERA) is False

    def test_fail_safe_paradox_l5_cannot_unlock_l2(self):
        """L5 код не может разблокировать L2 — только kill."""
        auth = AuthManager()
        auth.set_kill_password("kill_pass")
        caps = PlannerCapabilities.locked()

        # Пытаемся использовать kill password как TOTP для L2
        result = caps.unlock(CapabilityLevel.L2_CHIMERA, "kill_pass", auth)
        assert result is False
        assert caps.has(CapabilityLevel.L2_CHIMERA) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestPlannerCapabilitiesUnlock -v`
Expected: FAIL with `AttributeError: 'PlannerCapabilities' object has no attribute 'unlock'`

- [ ] **Step 3: Write minimal implementation**

Add `unlock`, `activate_kill`, `reset_kill` methods to `PlannerCapabilities`:

```python
@dataclass
class PlannerCapabilities:
    unlocked_levels: Set[CapabilityLevel] = field(
        default_factory=lambda: {CapabilityLevel.L1_POISONS}
    )
    fully_locked: bool = False

    @classmethod
    def locked(cls) -> "PlannerCapabilities":
        return cls()

    def has(self, level: CapabilityLevel) -> bool:
        if self.fully_locked:
            return False
        if level == CapabilityLevel.L5_KILL:
            return True
        return all(l in self.unlocked_levels for l in CapabilityLevel if 1 <= l <= level)

    def unlock(self, level: CapabilityLevel, code: str, auth: "AuthManager") -> bool:
        """Разблокировать уровень или активировать kill (L5)."""
        # L5 — kill switch, отдельный механизм
        if level == CapabilityLevel.L5_KILL:
            if auth.verify_kill_password(code):
                self.activate_kill()
                return True
            return False

        # L2-L4: если уже kill active — ничего не выйдет
        if self.fully_locked:
            return False

        # Только unlockable уровни
        if level not in CapabilityLevel.UNLOCKABLE:
            return False

        # Проверяем TOTP
        if not auth.verify_totp(level, code):
            return False

        # Sequential unlock: L3 требует L2, L4 требует L3
        if level > CapabilityLevel.L2_CHIMERA:
            required = CapabilityLevel(level - 1)
            if required not in self.unlocked_levels:
                return False

        self.unlocked_levels.add(level)
        return True

    def activate_kill(self) -> None:
        """L5: полная блокировка + очистка разблокированных уровней."""
        self.fully_locked = True
        self.unlocked_levels.clear()

    def reset_kill(self, password: str, auth: "AuthManager") -> bool:
        """Сброс kill switch — требует kill password повторно."""
        if not auth.verify_kill_password(password):
            return False
        self.fully_locked = False
        self.unlocked_levels = {CapabilityLevel.L1_POISONS}
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestPlannerCapabilitiesUnlock -v`
Expected: 9 passed.

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `pytest Ataker-boop/tests/ -v`
Expected: all tests pass (existing `test_ataker.py` + new `test_auth.py`).

- [ ] **Step 6: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): sequential unlock + kill activation + reset"
```

---

### Task 9: Secret file I/O — load/save from `~/.ataker/`

**Files:**
- Modify: `Ataker-boop/ataker/auth.py`
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Produces: `AuthManager.from_secrets_dir(path)`, `.save_to_dir(path)`, `init_secrets_dir(path, kill_password)` (creates dir + files, chmod 600)

- [ ] **Step 1: Write the failing tests**

Append to `Ataker-boop/tests/test_auth.py`:

```python
import os
from pathlib import Path

from ataker.auth import init_secrets_dir, AuthManager


class TestSecretFileIO:
    def test_init_creates_dir_with_700_perms(self, tmp_path):
        secrets_dir = tmp_path / "ataker_secrets"
        init_secrets_dir(secrets_dir, kill_password="my_kill")

        assert secrets_dir.is_dir()
        if os.name == "posix":
            mode = secrets_dir.stat().st_mode & 0o777
            assert mode == 0o700

    def test_init_creates_all_secret_files(self, tmp_path):
        secrets_dir = tmp_path / "s"
        init_secrets_dir(secrets_dir, kill_password="my_kill")

        assert (secrets_dir / "totp_l2").is_file()
        assert (secrets_dir / "totp_l3").is_file()
        assert (secrets_dir / "totp_l4").is_file()
        assert (secrets_dir / "kill_password_hash").is_file()
        assert (secrets_dir / "ingest_token").is_file()

    def test_secret_files_are_chmod_600(self, tmp_path):
        if os.name != "posix":
            pytest.skip("chmod only on posix")
        secrets_dir = tmp_path / "s"
        init_secrets_dir(secrets_dir, kill_password="my_kill")

        for fname in ["totp_l2", "totp_l3", "totp_l4", "kill_password_hash", "ingest_token"]:
            mode = (secrets_dir / fname).stat().st_mode & 0o777
            assert mode == 0o600, f"{fname} has mode {oct(mode)}, expected 0o600"

    def test_init_generates_different_secrets_each_call(self, tmp_path):
        d1 = tmp_path / "s1"
        d2 = tmp_path / "s2"
        init_secrets_dir(d1, kill_password="x")
        init_secrets_dir(d2, kill_password="x")

        assert (d1 / "totp_l2").read_text() != (d2 / "totp_l2").read_text()
        assert (d1 / "ingest_token").read_text() != (d2 / "ingest_token").read_text()

    def test_from_secrets_dir_loads_everything(self, tmp_path):
        secrets_dir = tmp_path / "s"
        init_secrets_dir(secrets_dir, kill_password="my_kill")

        auth = AuthManager.from_secrets_dir(secrets_dir)

        assert auth.has_kill_password() is True
        assert auth.verify_kill_password("my_kill") is True
        assert auth.has_ingest_token() is True
        # TOTP secrets loaded
        for level in CapabilityLevel.UNLOCKABLE:
            assert level in auth._totp_secrets

    def test_from_secrets_dir_verifies_totp(self, tmp_path):
        """Полный round-trip: init → load → verify TOTP."""
        import pyotp
        secrets_dir = tmp_path / "s"
        init_secrets_dir(secrets_dir, kill_password="x")

        auth = AuthManager.from_secrets_dir(secrets_dir)
        secret = (secrets_dir / "totp_l2").read_text().strip()
        valid_code = pyotp.TOTP(secret).now()

        assert auth.verify_totp(CapabilityLevel.L2_CHIMERA, valid_code) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestSecretFileIO -v`
Expected: FAIL with `ImportError: cannot import name 'init_secrets_dir'`

- [ ] **Step 3: Write minimal implementation**

Add to `ataker/auth.py`:

```python
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]

_TOTP_FILES = {
    CapabilityLevel.L2_CHIMERA: "totp_l2",
    CapabilityLevel.L3_CODEBREAK: "totp_l3",
    CapabilityLevel.L4_AGENTS: "totp_l4",
}


def _chmod_600(path: Path) -> None:
    """Set chmod 600 on POSIX (no-op elsewhere)."""
    if os.name == "posix":
        os.chmod(path, 0o600)


def init_secrets_dir(secrets_dir: PathLike, kill_password: str) -> None:
    """Создать директорию с секретами (chmod 700) и все файлы (chmod 600).

    Идемпотентно: перезаписывает существующие файлы.
    """
    secrets_dir = Path(secrets_dir)
    secrets_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        os.chmod(secrets_dir, 0o700)

    # TOTP secrets (base32)
    for level, fname in _TOTP_FILES.items():
        secret = pyotp.random_base32()
        p = secrets_dir / fname
        p.write_text(secret)
        _chmod_600(p)

    # Kill password (argon2id hash)
    kill_p = secrets_dir / "kill_password_hash"
    kill_p.write_text(_argon2.hash(kill_password))
    _chmod_600(kill_p)

    # Ingest token (32 hex)
    ingest_p = secrets_dir / "ingest_token"
    ingest_p.write_text(generate_ingest_token())
    _chmod_600(ingest_p)


class AuthManager:
    # ... existing methods ...

    @classmethod
    def from_secrets_dir(cls, secrets_dir: PathLike) -> "AuthManager":
        """Загрузить все секреты из директории (созданной init_secrets_dir)."""
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestSecretFileIO -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): secret file I/O with init_secrets_dir + from_secrets_dir"
```

---

### Task 10: `ataker init` CLI command

**Files:**
- Modify: `Ataker-boop/ataker/auth.py` (add `main()` entry point)
- Test: `Ataker-boop/tests/test_auth.py`

**Interfaces:**
- Produces: `main()` function callable via `python -m ataker.auth` that runs `init_secrets_dir` interactively

- [ ] **Step 1: Write the failing test**

Append to `Ataker-boop/tests/test_auth.py`:

```python
from ataker.auth import main
import subprocess
import sys


class TestInitCLI:
    def test_main_init_with_kill_password_arg(self, tmp_path, monkeypatch):
        """`python -m ataker.auth init --dir X --kill-password Y`."""
        secrets_dir = tmp_path / "ataker"
        # monkeypatch sys.argv
        monkeypatch.setattr(
            sys, "argv",
            ["ataker.auth", "init", "--dir", str(secrets_dir), "--kill-password", "test_kill"]
        )

        main()

        assert (secrets_dir / "totp_l2").is_file()
        assert (secrets_dir / "kill_password_hash").is_file()
        assert (secrets_dir / "ingest_token").is_file()

    def test_main_init_prints_totp_uris(self, tmp_path, monkeypatch, capsys):
        """init выводит otpauth:// URI для QR-кодов."""
        secrets_dir = tmp_path / "a"
        monkeypatch.setattr(
            sys, "argv",
            ["ataker.auth", "init", "--dir", str(secrets_dir), "--kill-password", "x"]
        )

        main()
        captured = capsys.readouterr()

        # Должны быть 3 otpauth URI (L2, L3, L4)
        assert captured.out.count("otpauth://") == 3
        assert "L2_CHIMERA" in captured.out or "L2" in captured.out

    def test_main_init_prompts_kill_password_if_missing(self, tmp_path, monkeypatch, capsys):
        """Если --kill-password не передан — просит ввести через input()."""
        secrets_dir = tmp_path / "a"
        monkeypatch.setattr(
            sys, "argv",
            ["ataker.auth", "init", "--dir", str(secrets_dir)]
        )
        monkeypatch.setattr("builtins.input", lambda _: "typed_password")

        main()

        auth = AuthManager.from_secrets_dir(secrets_dir)
        assert auth.verify_kill_password("typed_password") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestInitCLI -v`
Expected: FAIL with `ImportError: cannot import name 'main'`

- [ ] **Step 3: Write minimal implementation**

Append to `ataker/auth.py`:

```python
def _totp_uri(secret: str, level: CapabilityLevel) -> str:
    """otpauth:// URI для QR-кода Google Authenticator."""
    label = f"Ataker-boop:{level.name}"
    issuer = "Ataker-boop"
    return pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)


def main() -> None:
    """CLI: python -m ataker.auth init --dir ~/.ataker [--kill-password X]"""
    import argparse

    parser = argparse.ArgumentParser(prog="ataker.auth")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Создать секреты")
    p_init.add_argument("--dir", default=os.path.expanduser("~/.ataker"),
                        help="Путь к директории секретов (default: ~/.ataker)")
    p_init.add_argument("--kill-password", default=None,
                        help="Kill password (если не указан — спросит)")

    args = parser.parse_args()

    if args.cmd == "init":
        kill_pw = args.kill_password
        if kill_pw is None:
            kill_pw = input("Введите KILL PASSWORD (L5): ").strip()
            if not kill_pw:
                print("Ошибка: kill password не может быть пустым", file=sys.stderr)
                sys.exit(1)

        init_secrets_dir(args.dir, kill_pw)

        print(f"✓ Секреты созданы в {args.dir}")
        print()
        print("=== TOTP QR-коды для Google Authenticator ===")
        for level, fname in _TOTP_FILES.items():
            secret = (Path(args.dir) / fname).read_text().strip()
            uri = _totp_uri(secret, level)
            print(f"\n[{level.name}]")
            print(f"  {uri}")
        print()
        ingest = (Path(args.dir) / "ingest_token").read_text().strip()
        print(f"=== Ingest token (для ingestion pipeline) ===")
        print(f"  {ingest}")
        print()
        print("⚠️  СОХРАНИ KILL PASSWORD В НАДЕЖНОЕ МЕСТО — это твой рубильник.")


if __name__ == "__main__":
    main()
```

Add `import sys` to the top imports if not already there.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestInitCLI -v`
Expected: 3 passed.

- [ ] **Step 5: Run full auth test suite**

Run: `pytest Ataker-boop/tests/test_auth.py -v`
Expected: all auth tests pass (Tasks 2-10).

- [ ] **Step 6: Run entire test suite for regressions**

Run: `pytest Ataker-boop/tests/ -v`
Expected: all tests pass (existing + new).

- [ ] **Step 7: Commit**

```bash
git add Ataker-boop/ataker/auth.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker/auth): 'ataker init' CLI with TOTP URIs + kill password prompt"
```

---

### Task 11: Export new symbols from `ataker/__init__.py`

**Files:**
- Modify: `Ataker-boop/ataker/__init__.py`

**Interfaces:**
- Produces: public API exports `CapabilityLevel`, `PlannerCapabilities`, `AuthManager`, `init_secrets_dir`, `generate_ingest_token`, `verify_ingest_token`

- [ ] **Step 1: Write the failing test**

Append to `Ataker-boop/tests/test_auth.py`:

```python
class TestPublicAPI:
    def test_auth_symbols_importable_from_ataker(self):
        """Все публичные символы auth экспортируются из ataker package."""
        import ataker

        assert hasattr(ataker, "CapabilityLevel")
        assert hasattr(ataker, "PlannerCapabilities")
        assert hasattr(ataker, "AuthManager")
        assert hasattr(ataker, "init_secrets_dir")
        assert hasattr(ataker, "generate_ingest_token")

    def test_existing_exports_still_work(self):
        """Существующие экспорты не сломаны."""
        import ataker

        # несколько ключевых существующих
        assert hasattr(ataker, "AttackGenerator")
        assert hasattr(ataker, "MutationEngine")
        assert hasattr(ataker, "RedTeamLoop")
        assert hasattr(ataker, "AttackVault")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest Ataker-boop/tests/test_auth.py::TestPublicAPI -v`
Expected: FAIL on `assert hasattr(ataker, "CapabilityLevel")`

- [ ] **Step 3: Write minimal implementation**

Open `Ataker-boop/ataker/__init__.py`. Append (do NOT remove existing lines):

```python
# Auth subsystem (5-level access control)
from .auth import (
    CapabilityLevel,
    PlannerCapabilities,
    AuthManager,
    init_secrets_dir,
    generate_ingest_token,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest Ataker-boop/tests/test_auth.py::TestPublicAPI -v`
Expected: 2 passed.

- [ ] **Step 5: Run full suite**

Run: `pytest Ataker-boop/tests/ -v`
Expected: all pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add Ataker-boop/ataker/__init__.py Ataker-boop/tests/test_auth.py
git commit -m "feat(ataker): export auth symbols from __init__"
```

---

## Self-Review Notes

**Spec coverage (from `Ataker-boop/design/2026-07-22-planner-executor-attacker-design.md` §В.12):**
- ✅ 5 levels (L1-L5) — Task 2
- ✅ TOTP for L2-L4 with ±30s drift — Task 4
- ✅ Brute-force lockout 3→5min per-level — Task 5
- ✅ Kill password (argon2id, Fail-Safe Paradox) — Task 6
- ✅ Ingestion token — Task 7
- ✅ Sequential unlock (L3 needs L2, L4 needs L3) — Task 8
- ✅ L5 exempt from sequential, can fire anytime — Task 8
- ✅ L5 can only kill, never unlock — Task 8 (`test_fail_safe_paradox_l5_cannot_unlock_l2`)
- ✅ reset_kill requires password — Task 8
- ✅ Secret file I/O (chmod 600/700) — Task 9
- ✅ `ataker init` CLI with TOTP URIs — Task 10
- ✅ Public API exports — Task 11

**Gaps intentionally deferred to later plans:**
- `AdversarialLoop` integration (checks `caps.fully_locked` before each iteration) — Plan 5
- `Ingestion pipeline` using `verify_ingest_token` — Plan 3
- Planner checking `caps.has(L2_CHIMERA)` before emitting hybrid recipes — Plan 4

**Type consistency check:**
- `CapabilityLevel` used consistently across all tasks
- `PlannerCapabilities.has/unlock/activate_kill/reset_kill` signatures match between Task 8 tests and implementation
- `AuthManager.from_totp_secrets` / `from_secrets_dir` / `verify_totp` / `verify_kill_password` / `verify_ingest_token` — consistent naming throughout
