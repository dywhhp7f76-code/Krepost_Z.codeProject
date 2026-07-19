"""
Механизм гейтинга улучшений Крепости.

Все изменения в системе проходят через одобрение оператора:
1. Улучшение создаётся как Proposal в папке предложения/
2. Оператор получает уведомление
3. Оператор читает и выносит решение (approve/reject/revise)
4. Только одобренные предложения интегрируются в систему
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable

from loguru import logger


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION = "revision"
    INTEGRATED = "integrated"


@dataclass
class Proposal:
    id: str
    title: str
    description: str
    category: str
    files_affected: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    reviewed_at: Optional[float] = None
    reviewer_comment: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Proposal:
        d = d.copy()
        d["status"] = ProposalStatus(d["status"])
        return cls(**d)


class ImprovementGate:
    """
    Гейт-контроллер: ни одно изменение не попадает в основную систему
    без явного одобрения оператора.

    Хранение: SQLite (proposals.db) рядом с основной базой.
    Принцип: fail-closed — если статус не APPROVED, интеграция заблокирована.
    """

    def __init__(self, db_path: Optional[str] = None,
                 notify_callback: Optional[Callable[[Proposal], None]] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "предложения" / "proposals.db")
        self._db_path = db_path
        self._notify = notify_callback
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    files_affected TEXT DEFAULT '[]',
                    dependencies TEXT DEFAULT '[]',
                    risks TEXT DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at REAL NOT NULL,
                    reviewed_at REAL,
                    reviewer_comment TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT,
                    comment TEXT,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (proposal_id) REFERENCES proposals(id)
                )
            """)

    def submit(self, proposal: Proposal) -> Proposal:
        proposal.status = ProposalStatus.PENDING
        proposal.created_at = time.time()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO proposals (id, title, description, category,
                    files_affected, dependencies, risks, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proposal.id, proposal.title, proposal.description,
                proposal.category,
                json.dumps(proposal.files_affected, ensure_ascii=False),
                json.dumps(proposal.dependencies, ensure_ascii=False),
                json.dumps(proposal.risks, ensure_ascii=False),
                proposal.status.value, proposal.created_at
            ))
            self._log_action(conn, proposal.id, "submit", None, "pending")

        logger.info(f"[GATE] Новое предложение: {proposal.id} — {proposal.title}")

        if self._notify:
            self._notify(proposal)

        return proposal

    def approve(self, proposal_id: str, comment: str = "") -> bool:
        return self._set_status(proposal_id, ProposalStatus.APPROVED, comment)

    def reject(self, proposal_id: str, comment: str = "") -> bool:
        return self._set_status(proposal_id, ProposalStatus.REJECTED, comment)

    def request_revision(self, proposal_id: str, comment: str = "") -> bool:
        return self._set_status(proposal_id, ProposalStatus.REVISION, comment)

    def mark_integrated(
        self,
        proposal_id: str,
        *,
        regression_suite_passed: bool = False,
        suite_name: Optional[str] = None,
        operator_override: bool = False,
    ) -> bool:
        """Интеграция в основную систему — только APPROVED + RELAI green.

        Auto-RSI / auto-apply без зелёного регресс-набора запрещены
        (`allows_auto_rsi`). operator_override — только явный человек.
        """
        from krepost.governance.relai import allows_auto_rsi

        if not self.is_approved(proposal_id):
            logger.warning(
                f"[GATE] {proposal_id}: integrate BLOCKED — не APPROVED"
            )
            return False

        relai = allows_auto_rsi(
            regression_suite_passed=regression_suite_passed,
            suite_name=suite_name,
            operator_override=operator_override,
        )
        if not relai.allowed:
            logger.warning(
                f"[GATE] {proposal_id}: integrate BLOCKED by RELAI — {relai.reason}"
            )
            return False

        return self._set_status(
            proposal_id,
            ProposalStatus.INTEGRATED,
            f"Интегрировано ({relai.reason})",
        )

    def is_approved(self, proposal_id: str) -> bool:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT status FROM proposals WHERE id = ?",
                (proposal_id,)
            ).fetchone()
        if row is None:
            logger.warning(f"[GATE] Предложение {proposal_id} не найдено — BLOCKED")
            return False
        return row[0] == ProposalStatus.APPROVED.value

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM proposals WHERE id = ?",
                (proposal_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_proposal(row)

    def list_pending(self) -> List[Proposal]:
        return self._list_by_status(ProposalStatus.PENDING)

    def list_all(self) -> List[Proposal]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM proposals ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_proposal(r) for r in rows]

    def get_audit_log(self, proposal_id: str) -> List[dict]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT action, old_status, new_status, comment, timestamp "
                "FROM audit_log WHERE proposal_id = ? ORDER BY timestamp",
                (proposal_id,)
            ).fetchall()
        return [
            {"action": r[0], "old_status": r[1], "new_status": r[2],
             "comment": r[3], "timestamp": r[4]}
            for r in rows
        ]

    def _set_status(self, proposal_id: str, status: ProposalStatus,
                    comment: str) -> bool:
        now = time.time()
        with sqlite3.connect(self._db_path) as conn:
            old = conn.execute(
                "SELECT status FROM proposals WHERE id = ?",
                (proposal_id,)
            ).fetchone()
            if old is None:
                logger.error(f"[GATE] Предложение {proposal_id} не найдено")
                return False

            old_status = old[0]
            conn.execute("""
                UPDATE proposals
                SET status = ?, reviewed_at = ?, reviewer_comment = ?
                WHERE id = ?
            """, (status.value, now, comment, proposal_id))

            self._log_action(conn, proposal_id, "status_change",
                             old_status, status.value, comment)

        logger.info(f"[GATE] {proposal_id}: {old_status} → {status.value}"
                    f"{(' — ' + comment) if comment else ''}")
        return True

    def _list_by_status(self, status: ProposalStatus) -> List[Proposal]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM proposals WHERE status = ? ORDER BY created_at",
                (status.value,)
            ).fetchall()
        return [self._row_to_proposal(r) for r in rows]

    @staticmethod
    def _row_to_proposal(row) -> Proposal:
        return Proposal(
            id=row[0], title=row[1], description=row[2], category=row[3],
            files_affected=json.loads(row[4]), dependencies=json.loads(row[5]),
            risks=json.loads(row[6]), status=ProposalStatus(row[7]),
            created_at=row[8], reviewed_at=row[9], reviewer_comment=row[10]
        )

    @staticmethod
    def _log_action(conn, proposal_id: str, action: str,
                    old_status: Optional[str], new_status: str,
                    comment: str = ""):
        conn.execute("""
            INSERT INTO audit_log (proposal_id, action, old_status,
                new_status, comment, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (proposal_id, action, old_status, new_status, comment, time.time()))
