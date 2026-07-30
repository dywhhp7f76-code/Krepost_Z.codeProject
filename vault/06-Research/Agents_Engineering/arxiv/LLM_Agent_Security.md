---
tags: [arxiv, agent-security, krepost]
status: filter
---

# arXiv — LLM Agent Security

**Поиск:** https://arxiv.org/search/?query=%22LLM+Agent+Security%22&searchtype=all&order=-announced_date_first

## Пул (оператор фильтрует)

### Agent Security Bench (ASB)
- abs: https://arxiv.org/abs/2410.02644
- pdf: https://arxiv.org/pdf/2410.02644
- GitHub: https://github.com/agiresearch/ASB
- Зачем: бенч атак/защит агентов (prompt inject, memory poison, tools)

### Toward Secure LLM Agents
- abs: https://arxiv.org/abs/2606.10749
- pdf: https://arxiv.org/pdf/2606.10749
- Зачем: threat surfaces / defenses / evaluation (обзор поля)

### From Prompt Injections to Protocol Exploits
- abs: https://arxiv.org/abs/2506.23260
- pdf: https://arxiv.org/pdf/2506.23260
- Зачем: MCP/A2A/protocol exploits — релевантно `/v1/agent` + tools

### Dark Side of LLMs — agent attack vectors
- abs: https://arxiv.org/abs/2507.06850
- pdf: https://arxiv.org/pdf/2507.06850
- Зачем: inter-agent trust, RAG backdoor, system compromise

### RAS-Eval
- abs: https://arxiv.org/abs/2506.15253
- pdf: https://arxiv.org/pdf/2506.15253
- GitHub: https://github.com/lanzer-tree/RAS-Eval
- Зачем: real-world tool execution, CWE mapping

## Заметки Крепости
- Сопоставить с `harness_tools.py` (fetch/memory/vault) и UrlGuard.
- Memory poisoning → vault ingest quarantine.
