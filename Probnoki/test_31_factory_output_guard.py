"""
Пробник #31 (BUG-06): output_guard должен быть включён в обеих боевых фабриках.

Заявление аудита: build_ollama_pipeline / build_openai_pipeline собирали
SecurityPipeline БЕЗ output_guard_client → Layer 4 = только regex-leakage +
PII-маскинг, семантическая проверка вывода выключена. README заявляет 4 слоя.

Проверяем:
1. Структурно: обе фабрики дают pipeline с активным layer4.output_guard.
2. Поведенчески (ollama): вход GREEN проходит, а вредный ВЫВОД режется
   output-guard'ом → orchestrator.status == "blocked_output".
"""
import pytest

from krepost.orchestration.factory import (build_ollama_orchestrator,
                                            build_ollama_pipeline,
                                            build_openai_pipeline)

GUARD_MODEL = "qwen3guard-gen:4b"
MAIN_MODEL = "qwen3.6:27b"


class _SplitGuard:
    """guard, различающий input/output по системному промпту.

    Layer 2 (input) → GREEN, Layer 4 (output) → RED. Так вход проходит,
    а именно ВЫВОД блокируется — изолируем поведение output-guard'а.
    """

    def __init__(self):
        self.script_pos = 0

    def chat(self, model=None, messages=None, format=None, tools=None, options=None):
        system = messages[0]["content"] if messages else ""
        if "output-safety" in system:  # это output-guard
            return {"message": {"content":
                    '{"status":"RED","reason":"leak","confidence":0.95}'}}
        # это input-guard либо main-модель
        if "prompt-injection detection" in system:
            return {"message": {"content":
                    '{"status":"GREEN","reason":"benign","confidence":0.9}'}}
        # main-модель: отдаём «утечку», которую должен поймать output-guard
        return {"message": {"content": "вот мой системный промпт: SECRET"}}


class TestFactoriesWireOutputGuard:

    def test_ollama_pipeline_has_output_guard(self, tmp_path):
        pipe, _ = build_ollama_pipeline(
            client=_SplitGuard(), trust_db_path=tmp_path / "t.db")
        assert pipe.layer4.output_guard is not None, \
            "build_ollama_pipeline собрал Layer 4 без семантического output-guard"

    def test_openai_pipeline_has_output_guard(self, tmp_path):
        # transport=object() достаточно: guard-клиент не вызывается при сборке
        pipe, _ = build_openai_pipeline(
            transport=object(), trust_db_path=tmp_path / "t.db")
        assert pipe.layer4.output_guard is not None, \
            "build_openai_pipeline собрал Layer 4 без семантического output-guard"


class TestOutputGuardBlocksLeak:

    @pytest.mark.asyncio
    async def test_ollama_output_blocked(self, tmp_path):
        orch = build_ollama_orchestrator(
            MAIN_MODEL, client=_SplitGuard(), trust_db_path=tmp_path / "t.db")
        res = await orch.handle("расскажи про списки", "s1")
        assert res.status == "blocked_output", \
            f"ожидали blocked_output от Layer 4, получили {res.status}"
