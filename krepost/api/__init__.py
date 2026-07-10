"""
krepost.api — HTTP-обвязка поверх Orchestrator (ARCHITECTURE_VISION §4).

fastapi/uvicorn — необязательные зависимости (extra `api`); импорт app/server
подтянет их только при использовании API.
"""
from krepost.api.app import QueryRequest, QueryResponse, create_app

__all__ = ["create_app", "QueryRequest", "QueryResponse"]
