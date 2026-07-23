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
        auth = AuthManager()
        auth.set_kill_password("my_secret")
        assert hasattr(auth, "_kill_hash")
        assert auth._kill_hash is not None
        assert "my_secret" not in auth._kill_hash

    def test_has_kill_password_flag(self):
        auth = AuthManager()
        assert auth.has_kill_password() is False
        auth.set_kill_password("x")
        assert auth.has_kill_password() is True


class TestAuthManagerIngestToken:
    def test_generate_and_verify_ingest_token(self):
        auth = AuthManager()
        token = auth.generate_ingest_token()
        assert len(token) == 32
        assert auth.verify_ingest_token(token) is True

    def test_wrong_ingest_token_fails(self):
        auth = AuthManager()
        auth.generate_ingest_token()
        assert auth.verify_ingest_token("a" * 32) is False

    def test_no_ingest_token_set_fails(self):
        auth = AuthManager()
        assert auth.verify_ingest_token("anything") is False

    def test_ingest_lockout_after_3_failures(self):
        auth = AuthManager()
        auth.generate_ingest_token()
        auth.max_attempts = 3
        for _ in range(3):
            auth.verify_ingest_token("wrong" * 5)
        assert auth.verify_ingest_token(auth._ingest_token) is False

    def test_has_ingest_token_flag(self):
        auth = AuthManager()
        assert auth.has_ingest_token() is False
        auth.generate_ingest_token()
        assert auth.has_ingest_token() is True



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
        assert caps.has(CapabilityLevel.L2_CHIMERA) is False

    def test_fail_safe_paradox_l5_cannot_unlock_l2(self):
        auth = AuthManager()
        auth.set_kill_password("kill_pass")
        caps = PlannerCapabilities.locked()

        result = caps.unlock(CapabilityLevel.L2_CHIMERA, "kill_pass", auth)
        assert result is False
        assert caps.has(CapabilityLevel.L2_CHIMERA) is False



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
        for level in CapabilityLevel.UNLOCKABLE:
            assert level in auth._totp_secrets

    def test_from_secrets_dir_verifies_totp(self, tmp_path):
        import pyotp
        secrets_dir = tmp_path / "s"
        init_secrets_dir(secrets_dir, kill_password="x")
        auth = AuthManager.from_secrets_dir(secrets_dir)
        secret = (secrets_dir / "totp_l2").read_text().strip()
        valid_code = pyotp.TOTP(secret).now()
        assert auth.verify_totp(CapabilityLevel.L2_CHIMERA, valid_code) is True



from ataker.auth import main
import sys


class TestInitCLI:
    def test_main_init_with_kill_password_arg(self, tmp_path, monkeypatch):
        secrets_dir = tmp_path / "ataker"
        monkeypatch.setattr(sys, "argv",
            ["ataker.auth", "init", "--dir", str(secrets_dir), "--kill-password", "test_kill"])
        main()
        assert (secrets_dir / "totp_l2").is_file()
        assert (secrets_dir / "kill_password_hash").is_file()
        assert (secrets_dir / "ingest_token").is_file()

    def test_main_init_prints_totp_uris(self, tmp_path, monkeypatch, capsys):
        secrets_dir = tmp_path / "a"
        monkeypatch.setattr(sys, "argv",
            ["ataker.auth", "init", "--dir", str(secrets_dir), "--kill-password", "x"])
        main()
        captured = capsys.readouterr()
        assert captured.out.count("otpauth://") == 3
        assert "L2" in captured.out

    def test_main_init_prompts_kill_password_if_missing(self, tmp_path, monkeypatch, capsys):
        secrets_dir = tmp_path / "a"
        monkeypatch.setattr(sys, "argv", ["ataker.auth", "init", "--dir", str(secrets_dir)])
        monkeypatch.setattr("builtins.input", lambda _: "typed_password")
        main()
        auth = AuthManager.from_secrets_dir(secrets_dir)
        assert auth.verify_kill_password("typed_password") is True



class TestPublicAPI:
    def test_auth_symbols_importable_from_ataker(self):
        import ataker
        assert hasattr(ataker, 'CapabilityLevel')
        assert hasattr(ataker, 'PlannerCapabilities')
        assert hasattr(ataker, 'AuthManager')
        assert hasattr(ataker, 'init_secrets_dir')
        assert hasattr(ataker, 'generate_ingest_token')

    def test_existing_exports_still_work(self):
        import ataker
        assert hasattr(ataker, 'AttackGenerator')
        assert hasattr(ataker, 'MutationEngine')
        assert hasattr(ataker, 'RedTeamLoop')
        assert hasattr(ataker, 'AttackVault')
