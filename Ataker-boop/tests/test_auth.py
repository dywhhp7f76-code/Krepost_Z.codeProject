"""Tests for ataker.auth — 5-level access control."""
from __future__ import annotations

import time

import pytest

import pyotp

from ataker.auth import AuthManager, CapabilityLevel, PlannerCapabilities


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
        """±30s drift accepted (valid_window=1)."""
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, secret)
        totp = pyotp.TOTP(secret, interval=30, digits=6)
        previous_code = totp.at(int(time.time()) - 30)
        assert auth.verify_totp(CapabilityLevel.L2_CHIMERA, previous_code) is True

    def test_unknown_level_secret_fails(self):
        """No secret configured for a level → always False."""
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, pyotp.random_base32())
        assert auth.verify_totp(CapabilityLevel.L3_CODEBREAK, "123456") is False


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
        """Lockout L2 does not block L3."""
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
        """Successful code resets the failure counter."""
        secret = pyotp.random_base32()
        auth = _make_auth_with_secret(CapabilityLevel.L2_CHIMERA, secret)
        auth.max_attempts = 3

        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")  # 1
        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")  # 2
        auth.verify_totp(CapabilityLevel.L2_CHIMERA, pyotp.TOTP(secret).now())  # reset
        auth.verify_totp(CapabilityLevel.L2_CHIMERA, "wrong")  # 1 again

        assert auth.is_locked_out(CapabilityLevel.L2_CHIMERA) is False
