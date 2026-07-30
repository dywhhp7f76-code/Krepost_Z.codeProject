# LangChain / LangGraph — память, tools, security

> **Для обоих** (Ataker + Крепость). Снято с официальных docs: 2026-07-24.  
> Канон URL: [docs.langchain.com](https://docs.langchain.com/) (старый `python.langchain.com` редиректит сюда).

## Официальные входы

| Что | URL |
|-----|-----|
| Docs home | https://docs.langchain.com/ |
| LangChain Python overview | https://docs.langchain.com/oss/python/langchain/overview |
| Agents | https://docs.langchain.com/oss/python/langchain/agents |
| Models | https://docs.langchain.com/oss/python/langchain/models |
| Messages | https://docs.langchain.com/oss/python/langchain/messages |
| Tools | https://docs.langchain.com/oss/python/langchain/tools |
| Short-term memory | https://docs.langchain.com/oss/python/langchain/short-term-memory |
| Long-term memory | https://docs.langchain.com/oss/python/langchain/long-term-memory |
| RAG | https://docs.langchain.com/oss/python/langchain/rag |
| Retrieval | https://docs.langchain.com/oss/python/langchain/retrieval |
| Middleware | https://docs.langchain.com/oss/python/langchain/middleware/overview |
| Guardrails | https://docs.langchain.com/oss/python/langchain/guardrails |
| Human-in-the-loop | https://docs.langchain.com/oss/python/langchain/human-in-the-loop |
| Runtime | https://docs.langchain.com/oss/python/langchain/runtime |
| LangGraph overview | https://docs.langchain.com/oss/python/langgraph/overview |
| Persistence | https://docs.langchain.com/oss/python/langgraph/persistence |
| Memory (LangGraph) | https://docs.langchain.com/oss/python/langgraph/add-memory |
| Deep Agents harness | https://docs.langchain.com/oss/python/deepagents/harness |
| Deep Agents memory | https://docs.langchain.com/oss/python/deepagents/memory |
| **Going to production (security)** | https://docs.langchain.com/oss/python/deepagents/going-to-production |
| Permissions | https://docs.langchain.com/oss/python/deepagents/permissions |
| Reference overview | https://docs.langchain.com/oss/python/reference/overview |
| Integrations | https://docs.langchain.com/oss/python/integrations/providers/overview |
| Changelog | https://docs.langchain.com/oss/python/langchain/changelog-py |

---

## Short-term memory (thread)

Источник: [Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)

- Хранится как часть **agent state**; персистится через **checkpointer**.
- Идентификатор диалога: `thread_id` в `config["configurable"]`.
- Без checkpointer — только внутри одного `invoke`.
- Access patterns: `trim_messages`, `DeleteMessage`, summary через middleware / custom before_model.
- Tools видят историю через `InjectedState`.

**Атака:** залить thread длинным контекстом / summary poisoning / injection через tool results в history.  
**Защита:** trim, summary с фильтрацией, лимиты thread size, не доверять tool output как «системе».

## Long-term memory (across threads)

Источник: [Long-term memory](https://docs.langchain.com/oss/python/langchain/long-term-memory) · [Deep Agents memory](https://docs.langchain.com/oss/python/deepagents/memory)

- JSON / files в **Store** / virtual FS; namespace + key (или path).
- Типы: Semantic / Episodic / Procedural (CoALA).
- Deep Agents: memory как файлы; scopes User / Assistant / Org.

**Атака:** отравить Store чужими «фактами»; shared memory = prompt injection.  
**Защита:** изоляция namespace по user/tenant; read-only shared policies; HITL на write.

## Tools

Источник: [Tools](https://docs.langchain.com/oss/python/langchain/tools)

- Tool calling: model выбирает tool + args → runtime исполняет → ToolMessage обратно.
- `@tool`; `args_schema`; runtime injection для state/context/store.

**Атака:** tool argument injection, confused deputy, excess privileges.  
**Защита:** least privilege, allowlists, HITL на dangerous tools, schema validation.

## Production security (ключевая цитата)

Источник: [Going to production](https://docs.langchain.com/oss/python/deepagents/going-to-production)

> Shared memory (assistant, user, or organization scope) is a **vector for prompt injection**.  
> Если один пользователь пишет в память, которую читает другой — можно внедрить инструкции в shared state.

Митигации из доков:

1. Default scope = `user_id` (не шарить без причины).
2. Org policies = **read-only** для агента; пишет только application code.
3. `permissions` — deny write на `/memories/**`, `/policies/**`.
4. Backend policy hooks — audit / content inspection.
5. HITL / interrupt перед записью в shared paths.
6. Sandbox `execute` **не** покрывается path permissions — отдельный auth proxy.

---

## Маппинг на наши системы

| LangChain концепт | Крепость | Ataker |
|-------------------|----------|--------|
| Short-term / checkpointer | episodic / session history | multi-turn FITD state (план H7) |
| Long-term Store | memory router, semantic/episodic | knowledge snippets → Planner |
| Tools | agent tools в `/v1/agent` | arsenal categories как «tools» Planner |
| Guardrails | L1–L5 + future | measure bypass rate |
| HITL | operator review | human-first Planner default |
| Production isolation | tenant/user memory namespaces | не смешивать attack KB с defense memory |

## Статус загрузки

- [x] Каталог официальных URL (этот файл)
- [x] Short/long memory + tools + production security выжимка
- [ ] Полный offline mirror HTML (не делаем — ссылки + выжимка)
- [ ] SDK pin в CI (отдельная задача)

Оператор: ✅ / ⏸ / ❌
