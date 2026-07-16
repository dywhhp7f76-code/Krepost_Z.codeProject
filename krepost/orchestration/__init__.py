"""
krepost.orchestration — слой маршрутизации и оркестрации между
безопасностью и моделями (ARCHITECTURE_VISION §4, §5.3).
"""
from krepost.orchestration.backends import (
    CallableBackend,
    EchoBackend,
    ModelBackend,
)
from krepost.orchestration.orchestrator import (
    Orchestrator,
    OrchestrationResult,
    OrchestrationStatus,
)
from krepost.orchestration.router import Route, Router
from krepost.orchestration.tools import (
    AgentResult,
    FinalAnswer,
    Tool,
    ToolAgent,
    ToolCall,
    ToolCallingBackend,
    ToolRegistry,
    ToolTraceEntry,
    make_fetch_tool,
)

__all__ = [
    "ModelBackend",
    "CallableBackend",
    "EchoBackend",
    "Route",
    "Router",
    "Orchestrator",
    "OrchestrationResult",
    "OrchestrationStatus",
    # tool-loop
    "ToolAgent",
    "ToolCall",
    "FinalAnswer",
    "Tool",
    "ToolRegistry",
    "ToolCallingBackend",
    "make_fetch_tool",
    "AgentResult",
    "ToolTraceEntry",
    # ollama backend + factory
    "OllamaBackend",
    "build_ollama_orchestrator",
    "build_ollama_agent",
    "build_ollama_pipeline",
    "make_ollama_client",
    # openai-compatible backend (LM Studio / vLLM / LocalAI) + factory
    "OpenAIBackend",
    "OpenAIGuardClient",
    "build_openai_orchestrator",
    "build_openai_agent",
    "build_openai_agent_with_harness",
    "build_openai_pipeline",
]

from krepost.orchestration.ollama_backend import OllamaBackend  # noqa: E402
from krepost.orchestration.openai_backend import (  # noqa: E402
    OpenAIBackend,
    OpenAIGuardClient,
)
from krepost.orchestration.factory import (  # noqa: E402
    build_ollama_agent,
    build_ollama_orchestrator,
    build_ollama_pipeline,
    build_openai_agent,
    build_openai_agent_with_harness,
    build_openai_orchestrator,
    build_openai_pipeline,
    make_ollama_client,
)
