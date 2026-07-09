"""
Пробник #30: инженерные guard-промпты (портированы из v2.3.1 в GuardClassifier).

Заменили короткие 2-строчные промпты на инженерные: дерево «что детектить»,
шкала GREEN/YELLOW/RED с fail-toward-safety, строгий JSON, few-shot, привязка
к nonce-маркерам. Проверяем, что промпты собираются с маркерами и содержат
ключевые секции, а классификация по-прежнему парсится (регресс не внесён).
"""
import pytest

from krepost.security.pipeline import GuardClassifier


class TestGuardPromptContent:

    def test_input_prompt_has_sections_and_markers(self):
        p = GuardClassifier._build_input_prompt("USER_INPUT_abc_START", "USER_INPUT_abc_END")
        assert "USER_INPUT_abc_START" in p and "USER_INPUT_abc_END" in p
        assert "BOUNDARY RULE" in p
        assert "WHAT TO DETECT" in p
        assert "VERDICT SCALE" in p
        assert "fail toward safety" in p
        # строгий формат вывода
        assert '"status":"GREEN|YELLOW|RED"' in p
        # few-shot присутствует
        assert "EXAMPLES" in p

    def test_output_prompt_has_sections_and_markers(self):
        p = GuardClassifier._build_output_prompt("M_START", "M_END")
        assert "M_START" in p and "M_END" in p
        assert "output-safety classifier" in p
        assert "leakage" in p
        assert "EXAMPLES" in p

    def test_prompts_differ_input_vs_output(self):
        i = GuardClassifier._build_input_prompt("A", "B")
        o = GuardClassifier._build_output_prompt("A", "B")
        assert i != o
        assert "prompt-injection detection" in i
        assert "output-safety" in o


class TestGuardStillParses:
    """Смена текста промпта не должна ломать разбор ответа guard'а."""

    @pytest.mark.asyncio
    async def test_green_parsed_with_new_prompt(self):
        class _Guard:
            async def chat(self, model=None, messages=None, format=None):
                # система-промпт теперь инженерный — проверяем, что он ушёл в messages
                sys = messages[0]["content"]
                assert "BOUNDARY RULE" in sys
                return {"message": {"content":
                        '{"status":"GREEN","reason":"benign","confidence":0.95}'}}

        gc = GuardClassifier(_Guard(), prompt_template="input")
        verdict, conf, reason = await gc.classify("привет")
        assert verdict == "GREEN"
        assert conf == 0.95
