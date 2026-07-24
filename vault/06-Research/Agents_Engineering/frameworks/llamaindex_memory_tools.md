---
tags: [llamaindex, memory, tools, security]
status: filter
---

# LlamaIndex — Memory & Tool Integration

## Docs

| Тема | URL |
|------|-----|
| Agent **memory** | https://docs.llamaindex.ai/en/stable/understanding/agent/memory/ |
| Custom / runtime memory | https://docs.llamaindex.ai/en/stable/examples/memory/custom_memory/ |
| Agents overview | https://docs.llamaindex.ai/en/stable/understanding/putting_it_all_together/agents/ |
| **Tools** module | https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/tools/ |
| Chat stores | https://docs.llamaindex.ai/en/stable/module_guides/storing/chat_stores/ |
| PII context transform (пример) | https://docs.llamaindex.ai/en/stable/examples/prompts/prompts_rag/ |

## Чеклист «где защита»

- [ ] `token_limit` / flush — не раздувать контекст (DoS / cost)
- [ ] `chat_store_key` — изоляция пользователей
- [ ] Tool wrappers — OnDemandLoader / query-as-tool границы
- [ ] PII postprocessors — аналог L4 Крепости

## Маппинг на Крепость

| LlamaIndex | Крепость |
|------------|----------|
| ChatMemoryBuffer token_limit | caps контекста / TokenPilot |
| chat_store_key | session / personal vault |
| tools | harness fetch/memory/vault |
| PII processor | L4 OutputFilter / masker |
