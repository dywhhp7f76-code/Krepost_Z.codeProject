---
tags: [arxiv, workflow, agents, optimization]
status: filter
---

# arXiv — Agentic Workflow Optimization

**Поиск:** https://arxiv.org/search/?query=%22Agentic+Workflow+Optimization%22&searchtype=all&order=-announced_date_first  
**Шире:** https://arxiv.org/search/?query=agentic+workflow+optimization&searchtype=all&order=-announced_date_first

## Пул

### Survey: Static Templates → Dynamic Runtime Graphs
- abs: https://arxiv.org/abs/2603.22386
- pdf: https://arxiv.org/pdf/2603.22386
- Awesome: https://github.com/IBM/awesome-agentic-workflow-optimization
- Зачем: словарь static vs dynamic workflow; cost/robustness metrics

### AFlow — Automating Agentic Workflow Generation
- abs: https://arxiv.org/abs/2410.10762
- pdf: https://arxiv.org/pdf/2410.10762
- GitHub: https://github.com/FoundationAgents/AFlow
- Зачем: MCTS over code workflows; дешевле сильных моделей

### Weak-for-Strong (W4S)
- abs: https://arxiv.org/abs/2504.04785
- pdf: https://arxiv.org/pdf/2504.04785
- Зачем: слабый meta-agent оптимизирует workflow сильных executors (≈ Planner-Executor)

### AdaptFlow
- abs: https://arxiv.org/abs/2508.08053
- pdf: https://arxiv.org/pdf/2508.08053
- Зачем: meta-learning инициализации workflow

## Заметки Крепости
- Наш Ataker StubPlanner / adversarial_loop — static scaffold; LLM Planner = шаг к dynamic.
- Cost-aware batch (H3 harness plan) ↔ survey metrics.
