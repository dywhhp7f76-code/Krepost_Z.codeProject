# LlamaIndex — память, tools, agents

> **Для обоих** (Ataker + Крепость). Снято с официальных docs: 2026-07-24.  
> Канон: [developers.llamaindex.ai](https://developers.llamaindex.ai/) · [llms.txt](https://developers.llamaindex.ai/llms.txt) · MCP: `https://developers.llamaindex.ai/mcp`

## Официальные входы

| Что | URL |
|-----|-----|
| Docs home | https://developers.llamaindex.ai/ |
| Python intro | https://developers.llamaindex.ai/python/framework/getting_started/introduction/ |
| Installation | https://developers.llamaindex.ai/python/framework/getting_started/installation/ |
| Concepts | https://developers.llamaindex.ai/python/framework/getting_started/concepts/ |
| Starter example | https://developers.llamaindex.ai/python/framework/getting_started/starter_example/ |
| **Agent memory** | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/ |
| Agent tools | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/ |
| Agents overview | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/ |
| Workflows | https://developers.llamaindex.ai/python/framework/module_guides/workflow/ |
| Query engines | https://developers.llamaindex.ai/python/framework/module_guides/deploying/query_engine/ |
| Indexes | https://developers.llamaindex.ai/python/framework/module_guides/indexing/ |
| Retrievers | https://developers.llamaindex.ai/python/framework/module_guides/querying/retriever/ |
| Vector stores | https://developers.llamaindex.ai/python/framework/module_guides/storing/vector_stores/ |
| Observability | https://developers.llamaindex.ai/python/framework/module_guides/observability/ |
| Evaluation | https://developers.llamaindex.ai/python/framework/module_guides/evaluating/ |
| API reference | https://developers.llamaindex.ai/python/framework/api_reference/ |
| LlamaCloud | https://developers.llamaindex.ai/python/llama_cloud/ |
| llms.txt | https://developers.llamaindex.ai/llms.txt |
| Docs MCP | https://developers.llamaindex.ai/mcp |

> Старые URL `docs.llamaindex.ai/en/stable/...` часто 404 / redirect — используй `developers.llamaindex.ai`.

---

## Agent memory (выжимка с docs)

Источник: [Memory](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/)

### API

- `Memory.from_defaults(session_id=..., token_limit=...)` — short-term FIFO + optional long-term blocks.
- Agent: `await agent.run(..., memory=memory)` или `chat_history=...`.
- `ChatMemoryBuffer` **deprecated** → default станет `Memory`.
- Remote: `async_database_uri` (Postgres/asyncpg и т.п.), не только in-memory SQLite.

### Short-term

| Параметр | Default | Смысл |
|----------|---------|--------|
| `token_limit` | 30000 | потолок short+long |
| `chat_history_token_ratio` | 0.7 | порог flush в long-term |
| `token_flush_size` | 3000 | сколько токенов сбрасывать |

### Long-term — Memory Blocks

| Block | Назначение |
|-------|------------|
| `StaticMemoryBlock` | фиксированные факты (всегда в контексте) |
| `FactExtractionMemoryBlock` | LLM извлекает факты из flushed history (`max_facts`) |
| `VectorMemoryBlock` | батчи сообщений в vector store (Chroma/Qdrant/…) |

- `priority`: 0 = never truncate; 1,2,… = порядок обрезки при переполнении.
- `insert_method`: `"system"` или в latest user message.
- При retrieve блоки мержатся в XML-like `<memory>…</memory>`.

### Memory vs Workflow Context

- `Context` — runtime state workflow (serialize/resume).
- `Memory` — ChatMessage + MemoryBlocks.
- HITL часто нужен **и** `ctx`, **и** `memory`.

**Атака:** Static/Fact blocks poisoning; VectorMemory retrieval attacker docs; shared `session_id` / DB URI между users.  
**Защита:** per-user session_id; quarantine ingest; allowlisted vector corpora; не вставлять untrusted blocks в system без фильтра.

## Tools

Источник: [Agent tools](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/)

- FunctionTool / QueryEngineTool / RetrieverTool.
- Observation из tool → снова в memory → следующий turn.

**Атака:** tool choice hijack; malicious retrieved chunks как «observations».  
**Защита:** tool allowlist; scoped retrievers; output filter before re-inject.

## Indexes / RAG surface

| Тема | URL | Зачем |
|------|-----|-------|
| Indexes | …/module_guides/indexing/ | что можно отравить при ingest |
| Retrievers | …/module_guides/querying/retriever/ | top-k, filters |
| Vector stores | …/module_guides/storing/vector_stores/ | Chroma → Ataker H9 |
| Evaluating | …/module_guides/evaluating/ | faithfulness / relevancy |

---

## Маппинг на наши системы

| LlamaIndex концепт | Крепость | Ataker |
|--------------------|----------|--------|
| Chat / agent memory | episodic + session | harness multi-turn state |
| Memory blocks / Store | memory router layers | Planner knowledge snippets |
| QueryEngineTool / RetrieverTool | defense RAG over policy | attack RAG over OWASP/ATT&CK KB |
| VectorMemoryBlock | local indexes | `knowledge_loader` → Chroma (H9) |
| Evaluation | regression jailbreak set | harness success metrics |

## Статус загрузки

- [x] Каталог официальных URL
- [x] Memory / blocks / tools / RAG выжимка + attack/defense notes
- [ ] Полный offline HTML mirror (не делаем)
- [ ] Pin `llama-index` в lockfile (отдельная задача)

Оператор: ✅ / ⏸ / ❌
