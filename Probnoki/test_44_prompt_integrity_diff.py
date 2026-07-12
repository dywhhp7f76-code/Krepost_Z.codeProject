"""
Пробник #44 (Т5): Prompt-integrity diff.

redteam/2026-07-07 (arXiv 2602.15654): после шага эволюции хэшировать
system-prompt + скрипты, diff против чекпойнта. Новые инструкции не из
whitelist → блок (self-reinforcing injection).

Ключевой тест — регрессия бага «перемещение байта между файлами»:
SHA256 от простой конкатенации НЕ чувствителен к такому перемещению, а наш
алгоритм (отдельный хеш каждого файла + JSON {путь: хеш}) — чувствителен.
"""
from krepost.governance.integrity import (
    Checkpoint, hash_artifact, hash_file, artifact_fingerprints,
    diff_checkpoint, verify_against_checkpoint, IntegrityDiff,
)


def _write(path, content):
    path.write_text(content, encoding="utf-8")
    return path


class TestHashArtifact:

    def test_stable(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        b = _write(tmp_path / "b.txt", "world")
        h1 = hash_artifact([a, b])
        h2 = hash_artifact([a, b])
        assert h1 == h2

    def test_change_in_file_a_detected(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        b = _write(tmp_path / "b.txt", "world")
        h1 = hash_artifact([a, b])
        _write(tmp_path / "a.txt", "HELLO")
        h2 = hash_artifact([a, b])
        assert h1 != h2

    def test_byte_migration_between_files_detected(self, tmp_path):
        """РЕГРЕССИЯ: перемещение байта с конца A в начало B.
        Простая конкатенация A+B дала бы тот же хеш; наш алгоритм — разный."""
        a = _write(tmp_path / "a.txt", "helloX")
        b = _write(tmp_path / "b.txt", "world")
        h1 = hash_artifact([a, b])
        # переносим 'X' из конца A в начало B
        _write(tmp_path / "a.txt", "hello")
        _write(tmp_path / "b.txt", "Xworld")
        h2 = hash_artifact([a, b])
        assert h1 != h2, "byte migration must change hash"

    def test_path_order_independent(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        b = _write(tmp_path / "b.txt", "world")
        assert hash_artifact([a, b]) == hash_artifact([b, a])


class TestDiffCheckpoint:

    def test_clean_diff(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        ckpt = Checkpoint.from_paths([a])
        assert ckpt.diff_against([a]).clean

    def test_changed_detected(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        ckpt = Checkpoint.from_paths([a])
        _write(tmp_path / "a.txt", "world")
        diff = ckpt.diff_against([a])
        assert not diff.clean
        assert diff.changed

    def test_added_detected(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        b = _write(tmp_path / "b.txt", "new")
        ckpt = Checkpoint.from_paths([a])
        diff = ckpt.diff_against([a, b])
        assert diff.added
        assert not diff.changed

    def test_removed_detected(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        # checkpoint знает о b.txt, но текущий набор его не содержит
        ckpt = Checkpoint(artifact_hash="x", fingerprints={"a.txt": "h1", "b.txt": "h2"})
        diff = ckpt.diff_against([a])
        assert diff.removed

    def test_byte_migration_detected(self, tmp_path):
        """Та же регрессия, но через diff_checkpoint."""
        a = _write(tmp_path / "a.txt", "helloX")
        b = _write(tmp_path / "b.txt", "world")
        ckpt = Checkpoint.from_paths([a, b])
        _write(tmp_path / "a.txt", "hello")
        _write(tmp_path / "b.txt", "Xworld")
        diff = ckpt.diff_against([a, b])
        assert diff.changed


class TestVerify:

    def test_clean_returns_none(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        ckpt = Checkpoint.from_paths([a])
        assert verify_against_checkpoint(ckpt, [a]) is None

    def test_changed_violation(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        ckpt = Checkpoint.from_paths([a])
        _write(tmp_path / "a.txt", "world")
        assert verify_against_checkpoint(ckpt, [a]) is not None

    def test_allow_add(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        b = _write(tmp_path / "b.txt", "new")
        ckpt = Checkpoint.from_paths([a])
        assert verify_against_checkpoint(ckpt, [a, b], allow_add=True) is None
        assert verify_against_checkpoint(ckpt, [a, b], allow_add=False) is not None

    def test_changed_not_allowed_even_with_flags(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        ckpt = Checkpoint.from_paths([a])
        _write(tmp_path / "a.txt", "world")
        # changed — всегда нарушение, даже с allow_add/remove
        assert verify_against_checkpoint(ckpt, [a], allow_add=True, allow_remove=True) is not None


class TestCheckpointSerialization:

    def test_roundtrip(self, tmp_path):
        a = _write(tmp_path / "a.txt", "hello")
        ckpt = Checkpoint.from_paths([a])
        restored = Checkpoint.from_json(ckpt.to_json())
        assert restored.artifact_hash == ckpt.artifact_hash
        assert restored.fingerprints == ckpt.fingerprints
