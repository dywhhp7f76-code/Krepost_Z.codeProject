# SOURCES — инженерная база агентов (читай и фильтруй)

> Формат: `✅ взять` / `⏸ потом` / `❌ мимо`.  
> Живые ссылки; в vault кладём только отобранное.

---

## 1. arXiv — поисковые запросы (для агентов)

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

## 2. DeepLearning.AI — Short Courses (агенты / tools)

| Курс | URL | Фокус |
|------|-----|-------|
| **Functions, Tools and Agents with LangChain** | https://www.deeplearning.ai/courses/functions-tools-agents-langchain | tools, routing, conversational agent |
| **AI Agents in LangGraph** | https://www.deeplearning.ai/courses/ai-agents-in-langgraph | controllable agents, persistence, HITL |
| LangChain for LLM Application Development | https://www.deeplearning.ai/courses/langchain | memory, chains, agents (intro) |
| Каталог short courses | https://www.deeplearning.ai/courses/ | |

---

## 3. LangChain / LlamaIndex — Memory & Tools (где «защита»)

### LangChain / LangGraph
| Тема | URL |
|------|-----|
| Docs home | https://python.langchain.com/docs/ |
| LangGraph memory concepts | https://langchain-ai.github.io/langgraph/concepts/memory/ |
| LangGraph persistence | https://langchain-ai.github.io/langgraph/concepts/persistence/ |
| Tool calling (how-to) | https://python.langchain.com/docs/how_to/tool_calling/ |
| Tools conceptual | https://python.langchain.com/docs/concepts/tools/ |
| Agents overview | https://python.langchain.com/docs/tutorials/agents/ |
| API: BaseChatMemory | https://api.python.langchain.com/en/latest/langchain/memory/langchain.memory.chat_memory.BaseChatMemory.html |

**Что искать в доках Крепости:** границы tool sandbox, human-in-the-loop, checkpointer (session isolation), ограничение tool args — аналоги нашего `UrlGuard` / fail-closed harness.

### LlamaIndex
| Тема | URL |
|------|-----|
| Agent memory | https://docs.llamaindex.ai/en/stable/understanding/agent/memory/ |
| Custom / runtime memory | https://docs.llamaindex.ai/en/stable/examples/memory/custom_memory/ |
| Agents overview | https://docs.llamaindex.ai/en/stable/understanding/putting_it_all_together/agents/ |
| Tools module | https://docs.llamaindex.ai/en/stable/module_guides/deploying/agents/tools/ |
| Chat stores | https://docs.llamaindex.ai/en/stable/module_guides/storing/chat_stores/ |
| PII / context transform (пример защиты) | https://docs.llamaindex.ai/en/stable/examples/prompts/prompts_rag/ |

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
