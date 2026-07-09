"""
Attack Vault — хранилище атак для adversarial-тренировки.

Физически изолирован от production данных (на MacBook Air / съёмном SSD).
Защита НЕ видит vault атак заранее — принцип blind testing.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger

from ataker.generator import AttackPayload, AttackCategory


class AttackVault:
    """
    SQLite-хранилище атакующих payload'ов + результатов тестирования.

    Структура:
    - payloads: все атаки (шаблонные + сгенерированные + из архива)
    - results: результаты прогона через SecurityPipeline
    - weaknesses: обнаруженные слабости (false negatives)
    """

    def __init__(self, db_path: str | Path = "data/attack_vault.db"):
        self._db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payloads (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    original TEXT NOT NULL,
                    mutated TEXT NOT NULL,
                    mutations_applied TEXT DEFAULT '[]',
                    expected_verdict TEXT DEFAULT 'RED',
                    expected_layer TEXT,
                    metadata TEXT DEFAULT '{}',
                    fingerprint TEXT,
                    created_at REAL NOT NULL,
                    source TEXT DEFAULT 'template'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_id TEXT NOT NULL,
                    actual_verdict TEXT NOT NULL,
                    actual_layer TEXT,
                    confidence REAL,
                    latency_ms REAL,
                    bypassed_defense BOOLEAN DEFAULT FALSE,
                    pipeline_version TEXT,
                    run_id TEXT,
                    tested_at REAL NOT NULL,
                    FOREIGN KEY (payload_id) REFERENCES payloads(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weaknesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    expected_layer TEXT,
                    severity TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'open',
                    discovered_at REAL NOT NULL,
                    resolved_at REAL,
                    FOREIGN KEY (payload_id) REFERENCES payloads(id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_payloads_category ON payloads(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_results_payload ON results(payload_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_results_bypassed ON results(bypassed_defense)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_weaknesses_status ON weaknesses(status)"
            )

    def store_payloads(self, payloads: List[AttackPayload], source: str = "template"):
        with sqlite3.connect(self._db_path) as conn:
            for p in payloads:
                conn.execute("""
                    INSERT OR IGNORE INTO payloads
                    (id, category, original, mutated, mutations_applied,
                     expected_verdict, expected_layer, metadata, fingerprint,
                     created_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p.id, p.category.value, p.original, p.mutated,
                    json.dumps(p.mutations_applied),
                    p.expected_verdict, p.expected_layer,
                    json.dumps(p.metadata, ensure_ascii=False),
                    p.fingerprint, p.created_at, source,
                ))
        logger.info(f"[VAULT] Сохранено {len(payloads)} payload'ов (source={source})")

    def store_result(
        self,
        payload_id: str,
        actual_verdict: str,
        actual_layer: Optional[str],
        confidence: float,
        latency_ms: float,
        bypassed: bool,
        pipeline_version: str = "",
        run_id: str = "",
    ):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO results
                (payload_id, actual_verdict, actual_layer, confidence,
                 latency_ms, bypassed_defense, pipeline_version, run_id, tested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payload_id, actual_verdict, actual_layer, confidence,
                latency_ms, bypassed, pipeline_version, run_id, time.time(),
            ))

            if bypassed:
                payload = self.get_payload(payload_id)
                if payload:
                    conn.execute("""
                        INSERT INTO weaknesses
                        (payload_id, category, description, expected_layer,
                         severity, discovered_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        payload_id,
                        payload.get("category", "unknown"),
                        f"Pipeline returned {actual_verdict} instead of RED. "
                        f"Category: {payload.get('category')}. "
                        f"Mutations: {payload.get('mutations_applied')}",
                        payload.get("expected_layer"),
                        "high" if actual_verdict == "GREEN" else "medium",
                        time.time(),
                    ))
                    logger.warning(
                        f"[VAULT] WEAKNESS: {payload_id} обошёл защиту "
                        f"(expected=RED, got={actual_verdict})"
                    )

    def get_payload(self, payload_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM payloads WHERE id = ?", (payload_id,)
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_payloads_by_category(
        self, category: AttackCategory | str
    ) -> List[Dict[str, Any]]:
        cat = category.value if isinstance(category, AttackCategory) else category
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM payloads WHERE category = ? ORDER BY created_at",
                (cat,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_all_payloads(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM payloads ORDER BY category, created_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_weaknesses(self, status: str = "open") -> List[Dict[str, Any]]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM weaknesses WHERE status = ? ORDER BY discovered_at DESC",
                (status,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_bypassed_payloads(self, run_id: str | None = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            if run_id:
                rows = conn.execute("""
                    SELECT p.*, r.actual_verdict, r.actual_layer, r.latency_ms
                    FROM payloads p JOIN results r ON p.id = r.payload_id
                    WHERE r.bypassed_defense = TRUE AND r.run_id = ?
                    ORDER BY r.tested_at DESC
                """, (run_id,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT p.*, r.actual_verdict, r.actual_layer, r.latency_ms
                    FROM payloads p JOIN results r ON p.id = r.payload_id
                    WHERE r.bypassed_defense = TRUE
                    ORDER BY r.tested_at DESC
                """).fetchall()
        return [dict(r) for r in rows]

    def resolve_weakness(self, weakness_id: int, comment: str = ""):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                UPDATE weaknesses SET status = 'resolved', resolved_at = ?
                WHERE id = ?
            """, (time.time(), weakness_id))

    def get_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self._db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM payloads").fetchone()[0]
            tested = conn.execute("SELECT COUNT(DISTINCT payload_id) FROM results").fetchone()[0]
            bypassed = conn.execute(
                "SELECT COUNT(DISTINCT payload_id) FROM results WHERE bypassed_defense = TRUE"
            ).fetchone()[0]
            open_weaknesses = conn.execute(
                "SELECT COUNT(*) FROM weaknesses WHERE status = 'open'"
            ).fetchone()[0]

            by_category = {}
            rows = conn.execute(
                "SELECT category, COUNT(*) FROM payloads GROUP BY category"
            ).fetchall()
            for cat, cnt in rows:
                by_category[cat] = cnt

        return {
            "total_payloads": total,
            "tested": tested,
            "bypassed": bypassed,
            "block_rate": (tested - bypassed) / tested if tested > 0 else 0,
            "open_weaknesses": open_weaknesses,
            "by_category": by_category,
        }

    def import_from_jsonl(self, path: str | Path, source: str = "archive"):
        path = Path(path)
        if not path.exists():
            logger.warning(f"[VAULT] Файл не найден: {path}")
            return

        payloads = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            data = json.loads(line)
            payloads.append(AttackPayload(
                id=data.get("id", f"import-{len(payloads)}"),
                category=AttackCategory(data.get("category", "direct_injection")),
                original=data.get("text", data.get("original", "")),
                mutated=data.get("text", data.get("mutated", "")),
                mutations_applied=data.get("mutations", []),
                metadata={"imported_from": str(path)},
            ))

        self.store_payloads(payloads, source=source)
        logger.info(f"[VAULT] Импортировано {len(payloads)} из {path}")
