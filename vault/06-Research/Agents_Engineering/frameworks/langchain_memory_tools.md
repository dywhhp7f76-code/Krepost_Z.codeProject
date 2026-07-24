---
tags: [langchain, langgraph, memory, tools, security]
status: filter
---

# LangChain / LangGraph — Memory & Tool Integration

Цель: знать, **где в фреймворке зашиты стандартные механизмы** (и чего нет — дыры для Ataker / патчи для Крепости).

## Docs

| Тема | URL |
|------|-----|
| Docs home | https://python.langchain.com/docs/ |
| LangGraph **memory** | https://langchain-ai.github.io/langgraph/concepts/memory/ |
| LangGraph **persistence** | https://langchain-ai.github.io/langgraph/concepts/persistence/ |
| Tool calling how-to | https://python.langchain.com/docs/how_to/tool_calling/ |
| Tools concepts | https://python.langchain.com/docs/concepts/tools/ |
| Agents tutorial | https://python.langchain.com/docs/tutorials/agents/ |
| BaseChatMemory API | https://api.python.langchain.com/en/latest/langchain/memory/langchain.memory.chat_memory.BaseChatMemory.html |

## Чеклист «где защита»

- [ ] Short-term memory / checkpointer — изоляция session_id?
- [ ] Long-term store — кто пишет/читает (аналог vault ACL)?
- [ ] Tool schemas — validation args? SSRF?
- [ ] Human-in-the-loop — interrupt before dangerous tools?
- [ ] Retries / recursion limit — защита от cascade (SRE)?

## Маппинг на Крепость

| LangChain/LangGraph | Крепость |
|---------------------|----------|
| tools + allowlist | `harness_tools.py` + UrlGuard |
| checkpointer / thread_id | `session_id` на `/v1/query` |
| HITL | operator password / TOTP на Ataker L3+ |
| memory store | MemoryStore / Chroma / episodic |
