"""
Пробник #39 (BUG-07): L2/L3-кэш изолируется по версии политики.

L2 cache-hit возвращает GREEN, пропуская Layer 2 (Guard) и Layer 3. Раньше
запись не хранила версию guard/политики → при смене POLICY_VERSION старые
GREEN-вердикты продолжали проскакивать мимо ОБНОВЛЁННОГО Guard. Фикс: кэш
живёт в подкаталоге, привязанном к POLICY_VERSION — смена версии = другой
подкаталог = старые вердикты недостижимы (естественная инвалидация).
"""
from pathlib import Path

import krepost.security.pipeline as pipeline_mod
from krepost.security.pipeline import POLICY_VERSION, _versioned_cache_dir


class TestVersionedCacheDir:

    def test_dir_contains_policy_version(self):
        d = _versioned_cache_dir(Path("/data/cache"))
        assert POLICY_VERSION in str(d)
        assert d == Path("/data/cache") / f"policy-{POLICY_VERSION}"

    def test_version_change_changes_dir(self, monkeypatch):
        base = Path("/data/cache")
        d_now = _versioned_cache_dir(base)
        monkeypatch.setattr(pipeline_mod, "POLICY_VERSION", "9.9.9")
        d_next = _versioned_cache_dir(base)
        assert d_now != d_next
        assert "9.9.9" in str(d_next)

    def test_different_versions_never_collide(self, monkeypatch):
        base = Path("/c")
        monkeypatch.setattr(pipeline_mod, "POLICY_VERSION", "1.0.0")
        a = _versioned_cache_dir(base)
        monkeypatch.setattr(pipeline_mod, "POLICY_VERSION", "2.0.0")
        b = _versioned_cache_dir(base)
        assert a != b
