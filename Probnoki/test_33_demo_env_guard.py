"""
Пробник #33 (BUG-04-impl): demo-оркестратор не должен подниматься в проде.

build_demo_orchestrator() использует _DevAllowGuard (пропускает всё, GREEN).
Раньше он лишь логировал warning — dev-guard мог молча утечь в прод. Теперь
при KREPOST_ENV in {prod, production, staging} сборка обязана падать с
RuntimeError, а не деградировать защиту до «пропускать всё».
"""
import pytest

from krepost.api.server import build_demo_orchestrator


class TestDemoEnvGuard:

    @pytest.mark.parametrize("env", ["prod", "production", "staging",
                                     "PROD", "Production", " staging "])
    def test_refuses_in_prod_like_env(self, env, tmp_path, monkeypatch):
        monkeypatch.setenv("KREPOST_ENV", env)
        with pytest.raises(RuntimeError, match="(?i)KREPOST_ENV"):
            build_demo_orchestrator(trust_db_path=tmp_path / "t.db")

    def test_builds_when_env_unset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("KREPOST_ENV", raising=False)
        orch = build_demo_orchestrator(trust_db_path=tmp_path / "t.db")
        assert orch is not None

    @pytest.mark.parametrize("env", ["dev", "development", "local", "test", ""])
    def test_builds_in_non_prod_env(self, env, tmp_path, monkeypatch):
        monkeypatch.setenv("KREPOST_ENV", env)
        orch = build_demo_orchestrator(trust_db_path=tmp_path / "t.db")
        assert orch is not None
