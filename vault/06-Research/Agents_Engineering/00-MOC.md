# Agents Engineering — MOC

> Инженерная база: агенты, безопасность агентов, robustness, оптимизация workflow.  
> Сначала git → потом Obsidian sync с Studio vault.

## Читать / фильтровать

→ [[SOURCES]]

## Разделы

| Папка / заметка | Содержание |
|-----------------|------------|
| [[arxiv/LLM_Agent_Security]] | arXiv: LLM Agent Security |
| [[arxiv/Robustness_LLM]] | arXiv: Robustness of LLMs |
| [[arxiv/Agentic_Workflow_Optimization]] | arXiv: Agentic Workflow Optimization |
| [[deeplearning_ai/courses]] | DeepLearning.AI short courses |
| [[frameworks/langchain_memory_tools]] | LangChain / LangGraph Memory + Tools + production security |
| [[frameworks/llamaindex_memory_tools]] | LlamaIndex Memory blocks + Tools |
| [[frameworks/FOR_BOTH]] | Для обоих: attack vs defense reading path |

## Связь с Крепостью

- Harness: `krepost/orchestration/harness_tools.py`, `/v1/agent`
- Memory: Phase 3/4 MemoryRouter / HierarchicalDomainRAG
- Defense KB: `docs/security/knowledge-bases/`
- Ataker KB: `Ataker-boop/knowledge/`

## Как пополнять

1. Оператор фильтрует `SOURCES` (✅/⏸/❌).
2. Агент заносит карточки статей/доков.
3. `python ingest_vault.py` на Studio после синка.
