"""Tests for krepost.prompts.assistant"""

import pytest

from krepost.prompts.assistant import (
    build_assistant_system_prompt,
    build_rag_messages,
    NO_DATA_TOKEN,
)


class TestBuildAssistantSystemPrompt:
    def test_markers_wired_in(self):
        p = build_assistant_system_prompt("CONTEXT_abc_START", "CONTEXT_abc_END")
        assert "CONTEXT_abc_START" in p
        assert "CONTEXT_abc_END" in p

    def test_core_sections_present(self):
        p = build_assistant_system_prompt("S", "E")
        assert "ГРАНИЦА КОНТЕКСТА" in p
        assert "КОНТЕКСТ-ФЕЙТФУЛНЕСС" in p
        assert "ПРОТОКОЛ ОТКАЗА" in p
        assert "ЦИТИРОВАНИЕ" in p

    def test_refusal_token_present(self):
        p = build_assistant_system_prompt("S", "E")
        assert NO_DATA_TOKEN in p

    def test_vault_name_used_in_citation_format(self):
        p = build_assistant_system_prompt("S", "E", vault_name="MyVault")
        assert "obsidian://open?vault=MyVault" in p

    def test_default_vault_is_krepost(self):
        p = build_assistant_system_prompt("S", "E")
        assert "vault=Krepost" in p


class TestBuildRagMessages:
    def test_returns_system_and_user(self):
        msgs = build_rag_messages("Вопрос?", [{"text": "данные", "source": "a.md"}])
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_question_in_user_message(self):
        msgs = build_rag_messages("Как работает X?", [{"text": "t", "source": "s.md"}])
        assert "Как работает X?" in msgs[1]["content"]

    def test_context_and_source_rendered(self):
        msgs = build_rag_messages(
            "q", [{"text": "тело документа", "source": "path/to/doc.md"}]
        )
        user = msgs[1]["content"]
        assert "тело документа" in user
        assert "path/to/doc.md" in user

    def test_markers_match_between_system_and_user(self):
        msgs = build_rag_messages("q", [{"text": "t", "source": "s.md"}])
        system, user = msgs[0]["content"], msgs[1]["content"]
        assert "CONTEXT_" in user
        start_marker = user.split("\n", 1)[0]
        assert start_marker in system

    def test_nonce_differs_between_calls(self):
        m1 = build_rag_messages("q", [{"text": "t", "source": "s.md"}])
        m2 = build_rag_messages("q", [{"text": "t", "source": "s.md"}])
        assert m1[1]["content"].split("\n", 1)[0] != m2[1]["content"].split("\n", 1)[0]

    def test_empty_context_handled(self):
        msgs = build_rag_messages("q", [])
        assert "контекст пуст" in msgs[1]["content"]

    def test_multiple_blocks_numbered(self):
        msgs = build_rag_messages(
            "q",
            [
                {"text": "первый", "source": "a.md"},
                {"text": "второй", "source": "b.md"},
            ],
        )
        user = msgs[1]["content"]
        assert "[1]" in user
        assert "[2]" in user

    def test_custom_system_prompt_used(self):
        msgs = build_rag_messages(
            "q", [{"text": "t", "source": "s.md"}], system_prompt="OVERRIDE"
        )
        assert msgs[0]["content"] == "OVERRIDE"

    def test_missing_source_defaults_to_unknown(self):
        msgs = build_rag_messages("q", [{"text": "no source"}])
        assert "unknown" in msgs[1]["content"]
