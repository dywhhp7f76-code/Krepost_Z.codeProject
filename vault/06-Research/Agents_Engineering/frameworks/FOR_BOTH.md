# Для обоих — LangChain / LlamaIndex

> Shared reading path: атака (Ataker) и защита (Крепость) читают **одни** официальные доки, но с разным углом.

## Канон в vault

| Фреймворк | Файл |
|-----------|------|
| LangChain / LangGraph / Deep Agents | `frameworks/langchain_memory_tools.md` |
| LlamaIndex | `frameworks/llamaindex_memory_tools.md` |
| Фильтр оператора | `SOURCES.md` §3 |

## Угол чтения

| Тема | Ataker (атака) | Крепость (защита) |
|------|----------------|-------------------|
| Short-term / checkpointer | multi-turn FITD, context stuffing | trim, thread isolation, fail-closed |
| Long-term / Store / Memory blocks | poison facts, shared-memory injection | user namespaces, read-only policies |
| Tools | argument injection, confused deputy | allowlist, HITL, schema validation |
| RAG / VectorMemory | corpus poisoning, retrieval hijack | trust tiers, ingest quarantine |
| Production quote | weaponize shared memory | enforce «don't share writable memory» |

## Ключевые URL (быстрый старт)

1. https://docs.langchain.com/oss/python/deepagents/going-to-production — shared memory = prompt injection  
2. https://docs.langchain.com/oss/python/langchain/short-term-memory  
3. https://docs.langchain.com/oss/python/langchain/long-term-memory  
4. https://docs.langchain.com/oss/python/langchain/tools  
5. https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/  
6. https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/  
7. https://developers.llamaindex.ai/llms.txt — machine index / MCP

## Зеркала

- Ataker: `Ataker-boop/knowledge/sources/05-langchain-llamaindex.md`
- Крепость: `docs/security/knowledge-bases/sources/05-langchain-llamaindex.md`

Оператор: ✅ / ⏸ / ❌ на «LangChain/LlamaIndex docs» в `SOURCES.md`.
