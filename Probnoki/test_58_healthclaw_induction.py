"""Пробник #58: HealthClaw induction dispositions."""
from krepost.memory.healthclaw import HealthClawInductor, InductionStore


def test_discard_noise_and_security():
    ind = HealthClawInductor()
    assert ind.induce(query="hi", response="yo").disposition == "discard"
    assert (
        ind.induce(
            query="long enough question about solar batteries in vault",
            response="something useful about energy storage systems",
            security_verdict="RED",
        ).disposition
        == "discard"
    )


def test_profile_and_procedure():
    ind = HealthClawInductor()
    p = ind.induce(
        query="Запомни: я предпочитаю краткие ответы всегда",
        response="Ок, буду отвечать коротко.",
    )
    assert p.disposition == "profile"
    proc = ind.induce(
        query="How to restart Krepost launchd step by step?",
        response="1. kickstart\n2. check health\n3. smoke query\n" + ("x" * 50),
    )
    assert proc.disposition == "procedure"


def test_keep_episodic_default():
    ind = HealthClawInductor()
    v = ind.induce(
        query="Что такое KREPOST-RAG-7742 в архитектуре Крепости?",
        response="Это smoke-маркер для проверки retrieval в vault.",
    )
    assert v.disposition == "keep_episodic"


def test_store_writes_profile(tmp_path):
    store = InductionStore(tmp_path)
    ind = HealthClawInductor()
    v = ind.induce(
        query="Меня зовут тест и я предпочитаю русский",
        response="Принято.",
    )
    store.persist(v, query="q", response="r", session_id="s1", episode_id="e1")
    assert store.profile_path.is_file()
    assert "profile" in store.profile_path.read_text(encoding="utf-8")
