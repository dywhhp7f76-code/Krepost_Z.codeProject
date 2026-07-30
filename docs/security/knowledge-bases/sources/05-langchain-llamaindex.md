# LangChain / LlamaIndex — для Крепости (защита)

> Зеркало shared-базы. Канон: `vault/06-Research/Agents_Engineering/frameworks/`.  
> Загружено: 2026-07-24. Оператор фильтр: ✅ / ⏸ / ❌

## Читать в vault

| Файл | Зачем защите |
|------|--------------|
| `frameworks/langchain_memory_tools.md` | checkpointer isolation, Store namespaces, guardrails, HITL, **shared memory = injection** |
| `frameworks/llamaindex_memory_tools.md` | Memory blocks trust, scoped retrievers, eval metrics |
| `frameworks/FOR_BOTH.md` | таблица attack vs defense |

## Быстрые URL

| # | URL | Угол защиты |
|---|-----|-------------|
| 1 | https://docs.langchain.com/oss/python/deepagents/going-to-production | user-scoped memory; read-only org policies |
| 2 | https://docs.langchain.com/oss/python/deepagents/permissions | deny write на shared paths |
| 3 | https://docs.langchain.com/oss/python/langchain/short-term-memory | trim / summarization safely |
| 4 | https://docs.langchain.com/oss/python/langchain/long-term-memory | Store isolation |
| 5 | https://docs.langchain.com/oss/python/langchain/guardrails | PII / topic / safety |
| 6 | https://docs.langchain.com/oss/python/langchain/human-in-the-loop | approve dangerous tools |
| 7 | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/ | session_id per user; block priority |
| 8 | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/ | tool allowlist |
| 9 | https://developers.llamaindex.ai/llms.txt | полный индекс |

## Связь с Крепостью

- `/v1/agent` harness + tool sandbox ↔ LangChain tools + HITL
- MemoryRouter / episodic ↔ short-term checkpointer + long-term Store / Memory blocks
- L1–L5 ↔ guardrails + production permissions pattern
- Defense KB ingest ↔ trust-tiered RAG (не мешать с Ataker KB)

Не копируем полные HTML-доки в git — только выжимки + ссылки.
