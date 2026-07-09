"""
Пробник #34 (BUG-05): Trust Registry — WAL + атомарный upsert без гонки.

Заявление аудита: нет WAL mode; ручной SELECT+INSERT без транзакции →
IntegrityError на конкурентном добавлении одного нового хеша и «database is
locked» под нагрузкой.

Фикс: PRAGMA journal_mode=WAL; SELECT+INSERT → INSERT ... ON CONFLICT DO UPDATE.
⚠️ НЕ INSERT OR REPLACE — он бы сбросил added_at. Проверяем, что added_at
сохраняется при повторном добавлении.
"""
import sqlite3
import threading

import pytest

from krepost.security.trust_registry import TrustRegistry


def _journal_mode(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("PRAGMA journal_mode").fetchone()[0].lower()


def _added_at(db_path, text_hash):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT added_at FROM trusted_sources WHERE text_hash = ?",
            (text_hash,)).fetchone()
        return row[0] if row else None


class TestWalEnabled:

    def test_journal_mode_is_wal(self, tmp_path):
        db = tmp_path / "t.db"
        TrustRegistry(db_path=db)
        assert _journal_mode(db) == "wal", "PRAGMA journal_mode=WAL не включён"


class TestConcurrentAddNoRace:

    def test_many_threads_same_new_hash(self, tmp_path):
        reg = TrustRegistry(db_path=tmp_path / "t.db")
        text_hash = reg._compute_hash("один и тот же доверенный текст")
        errors = []
        barrier = threading.Barrier(24)

        def worker():
            barrier.wait()  # синхронный старт — максимизируем гонку
            try:
                reg._sync_add_trusted(text_hash, "src")
            except Exception as e:  # noqa: BLE001
                errors.append(repr(e))

        threads = [threading.Thread(target=worker) for _ in range(24)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, f"конкурентный add уронил {len(errors)} потоков: {errors[:3]}"


class TestReAddPreservesAddedAt:

    def test_added_at_not_reset_on_readd(self, tmp_path):
        db = tmp_path / "t.db"
        reg = TrustRegistry(db_path=db)
        h = reg._compute_hash("текст")
        reg._sync_add_trusted(h, "first")
        first_added = _added_at(db, h)
        assert first_added is not None
        # повторное добавление того же (уже активного) хеша
        reg._sync_add_trusted(h, "second")
        assert _added_at(db, h) == first_added, \
            "added_at сброшен при повторном add (симптом INSERT OR REPLACE)"

    def test_revoked_then_readd_restores(self, tmp_path):
        db = tmp_path / "t.db"
        reg = TrustRegistry(db_path=db)
        h = reg._compute_hash("текст2")
        reg._sync_add_trusted(h, "src")
        first_added = _added_at(db, h)
        reg._sync_revoke_trusted(h)
        reg._sync_add_trusted(h, "src")  # снова доверяем
        with sqlite3.connect(db) as conn:
            revoked = conn.execute(
                "SELECT revoked FROM trusted_sources WHERE text_hash = ?",
                (h,)).fetchone()[0]
        assert revoked == 0, "повторный add не снял revoked"
        assert _added_at(db, h) == first_added, "added_at сброшен при un-revoke"
