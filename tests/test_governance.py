"""Тесты для модуля гейтинга улучшений (krepost.governance)."""
import os
import tempfile
import pytest

from krepost.governance.gate import ImprovementGate, Proposal, ProposalStatus


@pytest.fixture
def gate(tmp_path):
    db_path = str(tmp_path / "test_proposals.db")
    return ImprovementGate(db_path=db_path)


@pytest.fixture
def sample_proposal():
    return Proposal(
        id="test-01",
        title="Тестовое предложение",
        description="Описание тестового предложения",
        category="security",
        files_affected=["krepost/security/pipeline.py"],
        dependencies=["loguru"],
        risks=["Риск 1"],
    )


class TestProposal:
    def test_create_proposal(self, sample_proposal):
        assert sample_proposal.id == "test-01"
        assert sample_proposal.status == ProposalStatus.PENDING

    def test_to_dict(self, sample_proposal):
        d = sample_proposal.to_dict()
        assert d["id"] == "test-01"
        assert d["status"] == "pending"
        assert isinstance(d["files_affected"], list)

    def test_from_dict(self, sample_proposal):
        d = sample_proposal.to_dict()
        restored = Proposal.from_dict(d)
        assert restored.id == sample_proposal.id
        assert restored.status == sample_proposal.status
        assert restored.title == sample_proposal.title


class TestImprovementGate:
    def test_submit(self, gate, sample_proposal):
        result = gate.submit(sample_proposal)
        assert result.status == ProposalStatus.PENDING

    def test_submit_and_retrieve(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        retrieved = gate.get_proposal("test-01")
        assert retrieved is not None
        assert retrieved.title == "Тестовое предложение"
        assert retrieved.category == "security"

    def test_approve(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        assert gate.approve("test-01", "Одобрено оператором")
        assert gate.is_approved("test-01")

    def test_reject(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        assert gate.reject("test-01", "Отклонено — слишком рано")
        assert not gate.is_approved("test-01")
        p = gate.get_proposal("test-01")
        assert p.status == ProposalStatus.REJECTED

    def test_request_revision(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        assert gate.request_revision("test-01", "Доработать риски")
        assert not gate.is_approved("test-01")
        p = gate.get_proposal("test-01")
        assert p.status == ProposalStatus.REVISION

    def test_fail_closed_unknown_id(self, gate):
        assert not gate.is_approved("nonexistent")

    def test_fail_closed_pending(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        assert not gate.is_approved("test-01")

    def test_mark_integrated_requires_relai(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        gate.approve("test-01")
        # без регресс-набора — BLOCKED (RELAI)
        assert not gate.mark_integrated("test-01")
        assert gate.get_proposal("test-01").status == ProposalStatus.APPROVED
        # с зелёным suite — ok
        assert gate.mark_integrated(
            "test-01", regression_suite_passed=True, suite_name="probniki"
        )
        assert gate.get_proposal("test-01").status == ProposalStatus.INTEGRATED

    def test_mark_integrated_operator_override(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        gate.approve("test-01")
        assert gate.mark_integrated("test-01", operator_override=True)
        assert gate.get_proposal("test-01").status == ProposalStatus.INTEGRATED

    def test_list_pending(self, gate):
        for i in range(3):
            p = Proposal(id=f"p-{i}", title=f"Предложение {i}",
                         description="...", category="security")
            gate.submit(p)
        gate.approve("p-1")
        pending = gate.list_pending()
        assert len(pending) == 2
        ids = [p.id for p in pending]
        assert "p-0" in ids
        assert "p-2" in ids
        assert "p-1" not in ids

    def test_list_all(self, gate):
        for i in range(3):
            p = Proposal(id=f"p-{i}", title=f"Предложение {i}",
                         description="...", category="testing")
            gate.submit(p)
        all_proposals = gate.list_all()
        assert len(all_proposals) == 3

    def test_audit_log(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        gate.approve("test-01", "Первое одобрение")
        gate.request_revision("test-01", "Нужна доработка")
        gate.approve("test-01", "Второе одобрение")

        log = gate.get_audit_log("test-01")
        assert len(log) == 4  # submit + approve + revision + approve
        assert log[0]["action"] == "submit"
        assert log[1]["new_status"] == "approved"
        assert log[2]["new_status"] == "revision"
        assert log[3]["new_status"] == "approved"

    def test_reject_nonexistent(self, gate):
        assert not gate.reject("fake-id")

    def test_notify_callback(self, gate):
        notifications = []
        gate._notify = lambda p: notifications.append(p.id)

        p = Proposal(id="notify-test", title="Test", description="...",
                     category="security")
        gate.submit(p)
        assert len(notifications) == 1
        assert notifications[0] == "notify-test"

    def test_reviewer_comment_stored(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        gate.approve("test-01", "Отличное предложение!")
        p = gate.get_proposal("test-01")
        assert p.reviewer_comment == "Отличное предложение!"
        assert p.reviewed_at is not None

    def test_files_affected_preserved(self, gate, sample_proposal):
        gate.submit(sample_proposal)
        p = gate.get_proposal("test-01")
        assert p.files_affected == ["krepost/security/pipeline.py"]
        assert p.dependencies == ["loguru"]
        assert p.risks == ["Риск 1"]
