# SOURCES — инженерная база агентов (читай и фильтруй)

> Формат: `✅ взять` / `⏸ потом` / `❌ мимо`.  
> Живые ссылки; в vault кладём только отобранное.
>
> **Календарь:** `docs/planning/CALENDAR.md`  
> **NOW:** §3 LangChain/LlamaIndex (A4; фаза I до 8 Sep)  
> **DEFERRED:** arXiv deep + DL.AI + workflow-opt → `docs/deferred/agents/`

---

## 1. arXiv — поисковые запросы (для агентов) · **DEFERRED** deep

Парковка: `docs/deferred/agents/arxiv-deep-ingest.md` · workflow: `…/workflow-optimization.md`  
Сейчас: можно глянуть заголовки; глубокое чтение ≥ **2026-09-08** после фильтра.

| Запрос | Search URL |
|--------|------------|
| `"LLM Agent Security"` | https://arxiv.org/search/?query=%22LLM+Agent+Security%22&searchtype=all&source=header&order=-announced_date_first |
| `"Robustness of Large Language Models"` | https://arxiv.org/search/?query=%22Robustness+of+Large+Language+Models%22&searchtype=all&source=header&order=-announced_date_first |
| `"Agentic Workflow Optimization"` | https://arxiv.org/search/?query=%22Agentic+Workflow+Optimization%22&searchtype=all&source=header&order=-announced_date_first |
| шире: `agent security LLM` | https://arxiv.org/search/?query=agent+security+LLM&searchtype=all&order=-announced_date_first |
| шире: `LLM robustness survey` | https://arxiv.org/search/?query=LLM+robustness+survey&searchtype=all&order=-announced_date_first |
| шире: `agentic workflow optimization` | https://arxiv.org/search/?query=agentic+workflow+optimization&searchtype=all&order=-announced_date_first |

### Отобранные статьи (стартовый пул — тоже фильтруй)

#### LLM Agent Security
| Paper | abs | pdf |
|-------|-----|-----|
| Agent Security Bench (ASB) | https://arxiv.org/abs/2410.02644 | https://arxiv.org/pdf/2410.02644 |
| Toward Secure LLM Agents (survey 2026) | https://arxiv.org/abs/2606.10749 | https://arxiv.org/pdf/2606.10749 |
| From Prompt Injections to Protocol Exploits | https://arxiv.org/abs/2506.23260 | https://arxiv.org/pdf/2506.23260 |
| Dark Side of LLMs: agent attack vectors | https://arxiv.org/abs/2507.06850 | https://arxiv.org/pdf/2507.06850 |
| RAS-Eval (real-world agent security) | https://arxiv.org/abs/2506.15253 | https://arxiv.org/pdf/2506.15253 |

#### Robustness of LLMs
| Paper | abs | pdf |
|-------|-----|-----|
| Evaluating and Improving Robustness… (survey) | https://arxiv.org/abs/2506.11111 | https://arxiv.org/pdf/2506.11111 |
| Robustness in LLMs: Mitigation & Metrics (survey) | https://arxiv.org/abs/2505.18658 | https://arxiv.org/pdf/2505.18658 |
| Awesome-LLM-Robustness list (сопутствующий) | https://github.com/zhangkunzk/Awesome-LLM-Robustness-papers | |

#### Agentic Workflow Optimization
| Paper | abs | pdf |
|-------|-----|-----|
| Survey: Static Templates → Dynamic Runtime Graphs | https://arxiv.org/abs/2603.22386 | https://arxiv.org/pdf/2603.22386 |
| Awesome list (IBM) | https://github.com/IBM/awesome-agentic-workflow-optimization | |
| AFlow: Automating Agentic Workflow Generation | https://arxiv.org/abs/2410.10762 | https://arxiv.org/pdf/2410.10762 |
| Weak-for-Strong (W4S) | https://arxiv.org/abs/2504.04785 | https://arxiv.org/pdf/2504.04785 |
| AdaptFlow | https://arxiv.org/abs/2508.08053 | https://arxiv.org/pdf/2508.08053 |

---

## 2. DeepLearning.AI — Short Courses (агенты / tools) · **DEFERRED**

Парковка: `docs/deferred/agents/deeplearning-ai-courses.md`

| Курс | URL | Фокус |
|------|-----|-------|
| **Functions, Tools and Agents with LangChain** | https://www.deeplearning.ai/courses/functions-tools-agents-langchain | tools, routing, conversational agent |
| **AI Agents in LangGraph** | https://www.deeplearning.ai/courses/ai-agents-in-langgraph | controllable agents, persistence, HITL |
| LangChain for LLM Application Development | https://www.deeplearning.ai/courses/langchain | memory, chains, agents (intro) |
| Каталог short courses | https://www.deeplearning.ai/courses/ | |

---

## 3. LangChain / LlamaIndex — Memory & Tools (**для обоих**)

> **Загружено в vault** (выжимки + актуальные URL, не полный HTML mirror):  
> - `frameworks/langchain_memory_tools.md`  
> - `frameworks/llamaindex_memory_tools.md`  
> - `frameworks/FOR_BOTH.md` (attack vs defense)  
> Зеркала: `Ataker-boop/knowledge/sources/05-langchain-llamaindex.md`,  
> `docs/security/knowledge-bases/sources/05-langchain-llamaindex.md`

### LangChain / LangGraph / Deep Agents (канон: docs.langchain.com)
| Тема | URL |
|------|-----|
| Docs home | https://docs.langchain.com/ |
| Short-term memory | https://docs.langchain.com/oss/python/langchain/short-term-memory |
| Long-term memory | https://docs.langchain.com/oss/python/langchain/long-term-memory |
| Tools | https://docs.langchain.com/oss/python/langchain/tools |
| Agents | https://docs.langchain.com/oss/python/langchain/agents |
| Guardrails | https://docs.langchain.com/oss/python/langchain/guardrails |
| HITL | https://docs.langchain.com/oss/python/langchain/human-in-the-loop |
| LangGraph persistence | https://docs.langchain.com/oss/python/langgraph/persistence |
| Deep Agents memory | https://docs.langchain.com/oss/python/deepagents/memory |
| **Going to production** ⭐ | https://docs.langchain.com/oss/python/deepagents/going-to-production |
| Permissions | https://docs.langchain.com/oss/python/deepagents/permissions |

**Крепость:** tool sandbox, HITL, checkpointer isolation, read-only shared policies — аналоги `UrlGuard` / fail-closed.  
**Ataker:** shared-memory injection, thread stuffing, tool-arg abuse — сценарии для Planner/harness.

### LlamaIndex (канон: developers.llamaindex.ai)
| Тема | URL |
|------|-----|
| Docs home | https://developers.llamaindex.ai/ |
| **Agent memory** ⭐ | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/ |
| Agent tools | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/tools/ |
| Agents | https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/ |
| Vector stores | https://developers.llamaindex.ai/python/framework/module_guides/storing/vector_stores/ |
| Evaluation | https://developers.llamaindex.ai/python/framework/module_guides/evaluating/ |
| llms.txt / MCP | https://developers.llamaindex.ai/llms.txt · https://developers.llamaindex.ai/mcp |

Старые `docs.llamaindex.ai/en/stable/...` — не опираться.

---

## Твой фильтр

```
arXiv ASB:                    ✅ / ⏸ / ❌
arXiv Secure LLM Agents:      ✅ / ⏸ / ❌
arXiv Protocol Exploits:      ✅ / ⏸ / ❌
arXiv Dark Side agents:       ✅ / ⏸ / ❌
arXiv RAS-Eval:               ✅ / ⏸ / ❌
arXiv Robustness survey 11111:✅ / ⏸ / ❌
arXiv Robustness 18658:       ✅ / ⏸ / ❌
arXiv Workflow survey 22386:  ✅ / ⏸ / ❌
arXiv AFlow:                  ✅ / ⏸ / ❌
arXiv W4S / AdaptFlow:        ✅ / ⏸ / ❌
DL.AI Tools+Agents:           ✅ / ⏸ / ❌
DL.AI LangGraph agents:       ✅ / ⏸ / ❌
LangChain memory/tools docs:  ✅ / ⏸ / ❌
LlamaIndex memory/tools docs: ✅ / ⏸ / ❌
```
