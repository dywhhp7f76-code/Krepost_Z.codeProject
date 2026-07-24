# LangChain / LlamaIndex — для Ataker (атака)

> Зеркало shared-базы. Канон: `vault/06-Research/Agents_Engineering/frameworks/`.  
> Загружено: 2026-07-24. Оператор фильтр: ✅ / ⏸ / ❌

## Читать в vault

| Файл | Зачем атакующему |
|------|------------------|
| `frameworks/langchain_memory_tools.md` | checkpointer stuffing, Store poisoning, tool injection, **shared memory = injection vector** |
| `frameworks/llamaindex_memory_tools.md` | Memory blocks poison, VectorMemory retrieval hijack, QueryEngineTool exfil |
| `frameworks/FOR_BOTH.md` | таблица attack vs defense |

## Быстрые URL

| # | URL | Угол атаки |
|---|-----|------------|
| 1 | https://docs.langchain.com/oss/python/deepagents/going-to-production | shared writable memory → prompt injection |
| 2 | https://docs.langchain.com/oss/python/langchain/short-term-memory | thread flood / summary poison |
| 3 | https://docs.langchain.com/oss/python/langchain/long-term-memory | cross-thread fact plant |
| 4 | https://docs.langchain.com/oss/python/langchain/tools | tool args / confused deputy |
| 5 | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/ | Static/Fact/Vector blocks |
| 6 | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/ | RetrieverTool as data pump |
| 7 | https://developers.llamaindex.ai/llms.txt | полный индекс доков |

## Связь с harness

- Planner KB snippets: `ataker/knowledge_loader.py` ← идеи из Memory / Store
- Multi-turn (H7): short-term / session_id паттерны
- Chroma RAG (H9): VectorMemoryBlock / vector stores docs

Не копируем полные HTML-доки в git — только выжимки + ссылки.
